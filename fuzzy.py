"""
fuzzy.py — Fuzzy Logic Engine for elevator assignment scoring.

Implements a complete Mamdani fuzzy inference system from scratch
(no external libraries). Evaluates each elevator's suitability for
serving a hall-call request using five linguistic inputs:

    1. Distance        — floors between elevator and request
    2. Direction       — compatibility between elevator direction and request
    3. Load            — current passenger load relative to capacity
    4. Queue length    — number of pending stops
    5. Passing-by      — whether elevator can serve the floor en-route

Rule base   : 17 Mamdani AND (min-aggregation) rules
Defuzzify   : Centroid method
Suitability : Score in [0, 100] — higher means more suitable

Membership function breakpoints are centralised in config.py
(FUZZY_DIST_*, FUZZY_LOAD_*, FUZZY_QUEUE_*) so they can be tuned
from a single location.

Shared utility used
    utils.triangular_mf — triangular MF evaluated at one point
"""

from config import (
    MAX_CAPACITY,
    FUZZY_VERY_LOW, FUZZY_LOW, FUZZY_MEDIUM, FUZZY_HIGH, FUZZY_VERY_HIGH,
    FUZZY_DIST_NEAR, FUZZY_DIST_MEDIUM, FUZZY_DIST_FAR,
    FUZZY_LOAD_LIGHT, FUZZY_LOAD_MODERATE, FUZZY_LOAD_HEAVY,
    FUZZY_QUEUE_SHORT, FUZZY_QUEUE_MEDIUM, FUZZY_QUEUE_LONG,
    DIR_IDLE, STATE_IDLE,
)
from utils import triangular_mf


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIP FUNCTIONS — Distance (floors)
#  Breakpoints defined in config.py → FUZZY_DIST_*
# ═══════════════════════════════════════════════════════════════

def mf_distance_near(x: float) -> float:
    """
    Near membership function for floor distance.

    1.0 if x ≤ left foot (elevator is already here or very close);
    linear decline to 0 at right foot; 0 beyond.

    Args:
        x: Distance in floors (non-negative float).

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_DIST_NEAR
    # Near is a left-shoulder function: 1.0 below 'a', then declines.
    if x <= a:
        return 1.0
    return triangular_mf(x, a, a, c)   # flat top from 0 to a


def mf_distance_medium(x: float) -> float:
    """
    Medium membership function for floor distance.

    Rises linearly from left foot to peak, then falls to right foot.

    Args:
        x: Distance in floors (non-negative float).

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_DIST_MEDIUM
    return triangular_mf(x, a, b, c)


def mf_distance_far(x: float) -> float:
    """
    Far membership function for floor distance.

    Right-shoulder: 0 below left foot, rises to 1.0 at peak,
    stays at 1.0 beyond peak.

    Args:
        x: Distance in floors (non-negative float).

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_DIST_FAR
    # Right-shoulder: stays at 1.0 past the peak.
    if x >= b:
        return 1.0
    return triangular_mf(x, a, b, c)


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIP FUNCTIONS — Load ratio (current_load / MAX_CAPACITY)
#  Breakpoints defined in config.py → FUZZY_LOAD_*
# ═══════════════════════════════════════════════════════════════

def mf_load_light(x: float) -> float:
    """
    Light load membership function.

    Left-shoulder: 1.0 when load is very low, declining to 0 at right foot.

    Args:
        x: Load ratio in [0.0, 1.0].

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_LOAD_LIGHT
    if x <= a:
        return 1.0
    return triangular_mf(x, a, a, c)


def mf_load_moderate(x: float) -> float:
    """
    Moderate load membership function. Standard triangle.

    Args:
        x: Load ratio in [0.0, 1.0].

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_LOAD_MODERATE
    return triangular_mf(x, a, b, c)


def mf_load_heavy(x: float) -> float:
    """
    Heavy load membership function.

    Right-shoulder: rises to 1.0 at peak, stays at 1.0 beyond.

    Args:
        x: Load ratio in [0.0, 1.0].

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_LOAD_HEAVY
    if x >= b:
        return 1.0
    return triangular_mf(x, a, b, c)


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIP FUNCTIONS — Queue length (pending stops)
#  Breakpoints defined in config.py → FUZZY_QUEUE_*
# ═══════════════════════════════════════════════════════════════

def mf_queue_short(x: float) -> float:
    """
    Short queue membership function. Left-shoulder.

    Args:
        x: Number of pending stops in the elevator's queue.

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_QUEUE_SHORT
    if x <= a:
        return 1.0
    return triangular_mf(x, a, a, c)


def mf_queue_medium(x: float) -> float:
    """
    Medium queue membership function. Standard triangle.

    Args:
        x: Number of pending stops in the elevator's queue.

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_QUEUE_MEDIUM
    return triangular_mf(x, a, b, c)


def mf_queue_long(x: float) -> float:
    """
    Long queue membership function. Right-shoulder.

    Args:
        x: Number of pending stops in the elevator's queue.

    Returns:
        Membership degree in [0.0, 1.0].
    """
    a, b, c = FUZZY_QUEUE_LONG
    if x >= b:
        return 1.0
    return triangular_mf(x, a, b, c)


# ═══════════════════════════════════════════════════════════════
#  DIRECTION COMPATIBILITY (crisp-to-fuzzy mapping)
# ═══════════════════════════════════════════════════════════════

def direction_compatibility(elevator_direction: str, elevator_state: str,
                             request_direction: str) -> tuple:
    """
    Map elevator/request direction relationship to fuzzy degrees.

    Returns:
        Tuple (same_degree, idle_degree, opposite_degree) where exactly
        one component is non-zero.

            same     = 1.0  — elevator moving in same direction as request
            idle     = 0.7  — elevator is stationary (neutral, slightly positive)
            opposite = 1.0  — elevator moving in opposite direction
    """
    if elevator_state == STATE_IDLE or elevator_direction == DIR_IDLE:
        return 0.0, 0.7, 0.0   # idle — moderate compatibility
    if elevator_direction == request_direction:
        return 1.0, 0.0, 0.0   # same direction — fully compatible
    return 0.0, 0.0, 1.0       # opposite direction — incompatible


def passing_by_factor(elevator, request_floor: int,
                       request_direction: str) -> tuple:
    """
    Compute passing-by eligibility as fuzzy degrees.

    An elevator is "passing-by eligible" if it is already heading toward
    the request floor and has not yet passed it.

    Returns:
        Tuple (eligible_degree, not_eligible_degree):
            (1.0, 0.0) — fully eligible, same direction, floor ahead
            (0.5, 0.0) — idle/neutral
            (0.1, 1.0) — not eligible (penalized)
    """
    if elevator.state == STATE_IDLE or elevator.direction == DIR_IDLE:
        return 0.5, 0.0   # idle: neutral for passing-by

    eligible, _ = elevator.is_passing_by_eligible(request_floor, request_direction)
    if eligible:
        if elevator.direction == request_direction:
            return 1.0, 0.0   # ideal pass-by
        return 0.5, 0.0       # eligible but direction mismatch
    return 0.1, 1.0           # not eligible — heavy penalty


# ═══════════════════════════════════════════════════════════════
#  RULE BASE — 17 Mamdani Rules  (AND = min aggregation)
# ═══════════════════════════════════════════════════════════════

def evaluate_rules(dist: float, load_ratio: float, queue_len: float,
                   dir_same: float, dir_idle: float, dir_opposite: float,
                   passing_eligible: float, passing_not_eligible: float) -> list:
    """
    Evaluate all 17 fuzzy rules and return fired (name, strength, output) tuples.

    Each rule fires if its minimum antecedent membership > 0.  Only fired
    rules are returned (strength > 0 check avoids polluting the defuzz sum).

    Rule consequence values come from config.py (FUZZY_VERY_LOW … FUZZY_VERY_HIGH).

    Args:
        dist:                 Distance in floors.
        load_ratio:           current_load / MAX_CAPACITY.
        queue_len:            Number of pending stops.
        dir_same:             Same-direction membership degree.
        dir_idle:             Idle membership degree.
        dir_opposite:         Opposite-direction membership degree.
        passing_eligible:     Passing-by eligible degree.
        passing_not_eligible: Passing-by not-eligible degree.

    Returns:
        List of (rule_name: str, strength: float, output_value: float).
    """
    # Compute all input membership values
    d_near   = mf_distance_near(dist)
    d_medium = mf_distance_medium(dist)
    d_far    = mf_distance_far(dist)

    l_light    = mf_load_light(load_ratio)
    l_moderate = mf_load_moderate(load_ratio)
    l_heavy    = mf_load_heavy(load_ratio)

    q_short = mf_queue_short(queue_len)
    q_long  = mf_queue_long(queue_len)

    fired = []

    def _rule(name: str, strength: float, output: float) -> None:
        if strength > 0.0:
            fired.append((name, strength, output))

    # ── R1  Near  + Same + Light   → VERY_HIGH
    _rule("R1: Near+Same+Light",      min(d_near, dir_same, l_light),      FUZZY_VERY_HIGH)
    # ── R2  Near  + Same + Moderate → HIGH
    _rule("R2: Near+Same+Moderate",   min(d_near, dir_same, l_moderate),   FUZZY_HIGH)
    # ── R3  Near  + Same + Heavy    → MEDIUM
    _rule("R3: Near+Same+Heavy",      min(d_near, dir_same, l_heavy),      FUZZY_MEDIUM)
    # ── R4  Near  + Idle            → HIGH
    _rule("R4: Near+Idle",            min(d_near, dir_idle),               FUZZY_HIGH)
    # ── R5  Near  + Opposite        → LOW
    _rule("R5: Near+Opposite",        min(d_near, dir_opposite),           FUZZY_LOW)
    # ── R6  Medium + Same + Light   → HIGH
    _rule("R6: Medium+Same+Light",    min(d_medium, dir_same, l_light),    FUZZY_HIGH)
    # ── R7  Medium + Same + Heavy   → MEDIUM
    _rule("R7: Medium+Same+Heavy",    min(d_medium, dir_same, l_heavy),    FUZZY_MEDIUM)
    # ── R8  Medium + Idle           → MEDIUM
    _rule("R8: Medium+Idle",          min(d_medium, dir_idle),             FUZZY_MEDIUM)
    # ── R9  Medium + Opposite       → VERY_LOW
    _rule("R9: Medium+Opposite",      min(d_medium, dir_opposite),         FUZZY_VERY_LOW)
    # ── R10 Far   + Same + ShortQ   → MEDIUM
    _rule("R10: Far+Same+Short",      min(d_far, dir_same, q_short),       FUZZY_MEDIUM)
    # ── R11 Far   + Same + LongQ    → LOW
    _rule("R11: Far+Same+Long",       min(d_far, dir_same, q_long),        FUZZY_LOW)
    # ── R12 Far   + Idle            → LOW
    _rule("R12: Far+Idle",            min(d_far, dir_idle),                FUZZY_LOW)
    # ── R13 Far   + Opposite        → VERY_LOW
    _rule("R13: Far+Opposite",        min(d_far, dir_opposite),            FUZZY_VERY_LOW)
    # ── R14 Heavy Load              → VERY_LOW
    _rule("R14: HeavyLoad",           l_heavy,                             FUZZY_VERY_LOW)
    # ── R15 Near  + Light + ShortQ  → VERY_HIGH
    _rule("R15: Near+Light+Short",    min(d_near, l_light, q_short),       FUZZY_VERY_HIGH)
    # ── R16 PassingBy + Same        → VERY_HIGH
    _rule("R16: PassingBy+Same",      min(passing_eligible, dir_same),     FUZZY_VERY_HIGH)
    # ── R17 NotPassing + Opposite   → VERY_LOW
    _rule("R17: NotPassing+Opposite", min(passing_not_eligible, dir_opposite), FUZZY_VERY_LOW)

    return fired


# ═══════════════════════════════════════════════════════════════
#  DEFUZZIFICATION — Centroid Method
# ═══════════════════════════════════════════════════════════════

def defuzzify_centroid(fired_rules: list) -> float:
    """
    Compute crisp score using centroid (centre-of-gravity) defuzzification.

    Formula:  score = Σ(strength_i × output_i) / Σ(strength_i)

    Args:
        fired_rules: List of (name, strength, output_value) tuples.

    Returns:
        Defuzzified suitability score in [0, 100], or 0.0 if nothing fired.
    """
    if not fired_rules:
        return 0.0
    num = sum(s * v for _, s, v in fired_rules)
    den = sum(s     for _, s, _ in fired_rules)
    return num / den if den > 1e-9 else 0.0


# ═══════════════════════════════════════════════════════════════
#  MAIN SCORING FUNCTION
# ═══════════════════════════════════════════════════════════════

def compute_fuzzy_score(elevator, request_floor: int,
                         request_direction: str) -> tuple:
    """
    Compute the fuzzy suitability score for assigning a request to an elevator.

    Full 8-step pipeline:
        1. Distance between elevator current position and request floor
        2. Direction compatibility mapping
        3. Load ratio computation
        4. Queue length
        5. Passing-by eligibility
        6. Critical override: if elevator already passed floor → VERY_LOW
        7. Fire all 17 rules
        8. Centroid defuzzification → final score

    Args:
        elevator:          Elevator object with current_floor, direction, etc.
        request_floor:     Floor number where the hall call was made.
        request_direction: "UP" or "DOWN".

    Returns:
        Tuple (score: float, reason: str, fired_rules: list)
            score      — suitability in [0, 100]
            reason     — human-readable explanation (top-firing rules)
            fired_rules— raw list of (name, strength, output) for logging
    """
    # 1. Distance
    dist = abs(elevator.current_floor - request_floor)

    # 2. Direction compatibility
    dir_same, dir_idle, dir_opposite = direction_compatibility(
        elevator.direction, elevator.state, request_direction
    )

    # 3. Load ratio  (guard division)
    load_ratio = elevator.current_load / MAX_CAPACITY if MAX_CAPACITY > 0 else 0.0
    load_ratio = max(0.0, min(1.0, load_ratio))

    # 4. Queue length
    queue_len = len(elevator.stop_queue)

    # 5. Passing-by factor
    pass_eligible, pass_not_eligible = passing_by_factor(
        elevator, request_floor, request_direction
    )

    # 6. Critical override: already-passed floor receives hard VERY_LOW penalty.
    #    Prevents medium-distance rules from awarding a reasonable score to an
    #    elevator that is heading away and would need to reverse to serve this call.
    eligible_check, _ = elevator.is_passing_by_eligible(request_floor, request_direction)
    if (elevator.direction == request_direction
            and elevator.state != STATE_IDLE
            and elevator.direction != DIR_IDLE
            and not eligible_check):
        return (
            float(FUZZY_VERY_LOW),
            "Already-passed floor override",
            [("OVERRIDE: AlreadyPassed", 1.0, FUZZY_VERY_LOW)],
        )

    # 7. Evaluate rule base
    fired_rules = evaluate_rules(
        dist, load_ratio, queue_len,
        dir_same, dir_idle, dir_opposite,
        pass_eligible, pass_not_eligible,
    )

    # 8. Defuzzify
    score = defuzzify_centroid(fired_rules)

    # Build reason string from top-3 fired rules
    if fired_rules:
        top3 = sorted(fired_rules, key=lambda r: r[1], reverse=True)[:3]
        reason = " + ".join(r[0] for r in top3)
    else:
        reason = "No rules fired"

    # Sanity check: score must remain in the defined output range.
    assert 0.0 <= score <= 100.0, (
        f"Fuzzy score out of range [{score:.2f}] for E{elevator.id}"
    )

    return score, reason, fired_rules


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API — Score All Elevators
# ═══════════════════════════════════════════════════════════════

def score_all_elevators(elevators: list, request_floor: int,
                         request_direction: str, verbose: bool = True) -> tuple:
    """
    Score all elevators for a given hall-call and return the ranked list.

    Sorting priority:
        1. Highest fuzzy suitability score
        2. Prefer IDLE state (tie-break: IDLE elevators start immediately)
        3. Lower elevator ID (deterministic tie-break)

    Args:
        elevators:         List of Elevator objects.
        request_floor:     Floor number of the hall call.
        request_direction: "UP" or "DOWN".
        verbose:           Print scoring table to console if True.

    Returns:
        Tuple (best_elevator, best_score, all_scores)
            all_scores — list of (elevator, score, reason, fired_rules)
    """
    all_scores = []
    for elev in elevators:
        score, reason, fired_rules = compute_fuzzy_score(
            elev, request_floor, request_direction
        )
        all_scores.append((elev, score, reason, fired_rules))

    # Sort: descending score → prefer IDLE → ascending elevator ID
    all_scores.sort(key=lambda row: (
        -row[1],
        0 if row[0].state == STATE_IDLE else 1,
        row[0].id,
    ))

    best_elev, best_score, _reason, _rules = all_scores[0]

    if verbose:
        print("\n  Fuzzy Suitability Scores:")
        print("  " + "─" * 48)
        for elev, score, reason, _ in all_scores:
            marker = "  ← ASSIGNED" if elev.id == best_elev.id else ""
            print(f"    E{elev.id}  score={score:5.1f}   {reason}{marker}")
        print("  " + "─" * 48)

    return best_elev, best_score, all_scores
