"""
adaptive_system.py — Adaptive Fuzzy Inference System for the Research Track.

Implements a 10-rule Mamdani fuzzy system whose membership parameters and
rule weights can be:
    1. Adapted per traffic mode (peak_up, peak_down, inter_floor, mixed)
    2. Optimised by a Genetic Algorithm (FuzzyParameterGA injects a
       flat float vector via set_optimized_parameters).

Cross-reference:
    fuzzy.py (root) — legacy 17-rule variant, same triangular_mf shared via utils.py.
    utils.triangular_mf — the single triangular membership implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from research.core.config import FuzzyAdaptationConfig, FuzzyConfig
from research.core.models import (
    DecisionExplanation,
    ElevatorState,
    PassengerGroupRequest,
    RuleActivation,
)
from utils import triangular_mf   # shared with root-level fuzzy.py


# ═══════════════════════════════════════════════════════════════
#  MEMBERSHIP PARAMETER CONTAINER
# ═══════════════════════════════════════════════════════════════

@dataclass
class MembershipParameters:
    """
    Triangular membership function breakpoints for all linguistic inputs.

    Each attribute is a 3-tuple (a, b, c):
        a — left foot  (membership = 0 at and below a)
        b — peak       (membership = 1.0 at b)
        c — right foot (membership = 0 at and above c)
    """
    near:     Tuple[float, float, float] = (0.0,  0.0,  4.0)
    medium:   Tuple[float, float, float] = (2.0,  6.0, 10.0)
    far:      Tuple[float, float, float] = (7.0, 14.0, 25.0)
    light:    Tuple[float, float, float] = (0.0,  0.0,  0.4)
    moderate: Tuple[float, float, float] = (0.2,  0.5,  0.8)
    heavy:    Tuple[float, float, float] = (0.6,  1.0,  1.0)
    short_q:  Tuple[float, float, float] = (0.0,  0.0,  2.5)
    medium_q: Tuple[float, float, float] = (1.5,  4.0,  7.0)
    long_q:   Tuple[float, float, float] = (5.0, 10.0, 20.0)


# ═══════════════════════════════════════════════════════════════
#  ADAPTIVE RULE DEFINITION
# ═══════════════════════════════════════════════════════════════

@dataclass
class AdaptiveRule:
    """
    A single fuzzy rule with a mutable base weight.

    The base weight is multiplied by a traffic-mode multiplier during
    adapt_rule_weights(), allowing the system to bias towards rules
    that are most relevant for the current traffic pattern.

    Attributes:
        name:        Unique rule identifier (e.g. "R1").
        antecedents: Dict of {variable_name: linguistic_label}.
        consequent:  Output label (e.g. "very_high").
        base_weight: Scaling factor ∈ [weight_min, weight_max].
    """
    name:        str
    antecedents: Dict[str, str]
    consequent:  str
    base_weight: float


# ═══════════════════════════════════════════════════════════════
#  ADAPTIVE FUZZY SYSTEM
# ═══════════════════════════════════════════════════════════════

@dataclass
class AdaptiveFuzzySystem:
    """
    Mamdani fuzzy inference engine with traffic-adaptive rule weights.

    Key capabilities:
        • evaluate()               — full inference → DecisionExplanation
        • adapt_rule_weights()     — apply traffic-mode multipliers
        • set_optimized_parameters()— inject GA-evolved float vector
        • reset_rule_weights()     — restore canonical weights

    The system uses triangular_mf() from utils.py (same implementation
    shared with the legacy root-level fuzzy.py).
    """

    fuzzy_config:      FuzzyConfig            = field(default_factory=FuzzyConfig)
    adaptation_config: FuzzyAdaptationConfig  = field(default_factory=FuzzyAdaptationConfig)
    params:            MembershipParameters   = field(default_factory=MembershipParameters)
    output_values:     Dict[str, float]       = field(default_factory=dict)
    rules:             List[AdaptiveRule]     = field(default_factory=list)

    def __post_init__(self) -> None:
        # Build membership parameters from config
        self.params = MembershipParameters(
            near     = self.fuzzy_config.distance_near,
            medium   = self.fuzzy_config.distance_medium,
            far      = self.fuzzy_config.distance_far,
            light    = self.fuzzy_config.load_light,
            moderate = self.fuzzy_config.load_moderate,
            heavy    = self.fuzzy_config.load_heavy,
            short_q  = self.fuzzy_config.queue_short,
            medium_q = self.fuzzy_config.queue_medium,
            long_q   = self.fuzzy_config.queue_long,
        )
        # Map output labels to crisp values
        self.output_values = {
            "very_low":  self.fuzzy_config.output_very_low,
            "low":       self.fuzzy_config.output_low,
            "medium":    self.fuzzy_config.output_medium,
            "high":      self.fuzzy_config.output_high,
            "very_high": self.fuzzy_config.output_very_high,
        }
        # Build default 10-rule base (skip if already injected)
        if self.rules:
            return
        self.rules = [
            AdaptiveRule("R1",  {"distance": "near",   "direction": "same",         "load": "light"},    "very_high", 1.00),
            AdaptiveRule("R2",  {"distance": "near",   "direction": "same",         "load": "moderate"}, "high",      0.90),
            AdaptiveRule("R3",  {"distance": "medium", "direction": "same",         "queue": "short"},   "high",      0.85),
            AdaptiveRule("R4",  {"distance": "near",   "direction": "idle"},                             "high",      0.90),
            AdaptiveRule("R5",  {"distance": "medium", "direction": "idle"},                             "medium",    0.80),
            AdaptiveRule("R6",  {"distance": "far",    "direction": "idle"},                             "low",       0.70),
            AdaptiveRule("R7",  {"direction": "opposite", "passby": "not_passable"},                     "very_low",  1.00),
            AdaptiveRule("R8",  {"distance": "far",    "direction": "opposite"},                         "very_low",  0.95),
            AdaptiveRule("R9",  {"queue": "long",      "load": "heavy"},                                 "low",       0.90),
            AdaptiveRule("R10", {"passby": "passable", "direction": "same"},                             "very_high", 0.95),
        ]
        # Snapshot of canonical weights for reset
        self._canonical_weights: Dict[str, float] = {
            r.name: r.base_weight for r in self.rules
        }

    # ───────────────────────────────────────────────────────────
    #  GA-DRIVEN PARAMETER INJECTION
    # ───────────────────────────────────────────────────────────

    def set_optimized_parameters(self, flat_vector: List[float]) -> None:
        """
        Inject a GA-evolved parameter vector into the system.

        Vector layout (25 = 15 triangle genes + 10 rule weight genes):
            [0:3]   near (a, b, c)
            [3:6]   medium (a, b, c)
            [6:9]   far (a, b, c)
            [9:12]  short_q (a, b, c)
            [12:15] medium_q (a, b, c)
            [15:]   one weight per rule (clamped to [0.2, 1.5])

        Args:
            flat_vector: Float list of length ≥ 15.
        """
        if len(flat_vector) < 15:
            return  # malformed vector — skip silently

        p = flat_vector

        def _sorted3(i: int) -> Tuple[float, float, float]:
            """Sort three consecutive genes into non-decreasing order."""
            a = max(0.0, p[i])
            b = max(0.0, p[i + 1])
            c = max(0.1, p[i + 2])
            return tuple(sorted((a, b, c)))   # type: ignore[return-value]

        self.params.near     = _sorted3(0)
        self.params.medium   = _sorted3(3)
        self.params.far      = _sorted3(6)
        self.params.short_q  = _sorted3(9)
        self.params.medium_q = _sorted3(12)

        for i, rule in enumerate(self.rules):
            idx = 15 + i
            if idx < len(flat_vector):
                rule.base_weight = max(0.2, min(1.5, float(flat_vector[idx])))

        self._canonical_weights = {r.name: r.base_weight for r in self.rules}

    # ───────────────────────────────────────────────────────────
    #  RULE WEIGHT ADAPTATION PER TRAFFIC MODE
    # ───────────────────────────────────────────────────────────

    def reset_rule_weights(self) -> None:
        """Restore all rule weights to their canonical (pre-adaptation) values."""
        for rule in self.rules:
            rule.base_weight = self._canonical_weights.get(rule.name, rule.base_weight)

    def adapt_rule_weights(self, traffic_mode: str) -> None:
        """
        Scale rule weights to match the detected traffic regime.

        First resets to canonical weights, then applies mode-specific
        multipliers defined in FuzzyAdaptationConfig.

        Args:
            traffic_mode: One of "peak_up", "peak_down", "inter_floor", "mixed".
        """
        self.reset_rule_weights()

        cfg = self.adaptation_config
        mode_multipliers: Dict[str, Dict[str, float]] = {
            "peak_up":    {"R10": cfg.peak_up_r10,  "R1": cfg.peak_up_r1,       "R9": cfg.peak_up_r9},
            "peak_down":  {"R10": cfg.peak_down_r10,"R2": cfg.peak_down_r2,     "R9": cfg.peak_down_r9},
            "inter_floor":{"R3":  cfg.inter_floor_r3,"R5": cfg.inter_floor_r5,  "R6": cfg.inter_floor_r6},
        }

        for rule in self.rules:
            m = mode_multipliers.get(traffic_mode, {}).get(rule.name, 1.0)
            rule.base_weight = max(
                cfg.weight_min,
                min(cfg.weight_max, rule.base_weight * m),
            )

    # ───────────────────────────────────────────────────────────
    #  MEMBERSHIP COMPUTATION
    # ───────────────────────────────────────────────────────────

    def _memberships(self, elevator: ElevatorState,
                     request: PassengerGroupRequest) -> Dict[str, Dict[str, float]]:
        """
        Compute all membership degrees for the given (elevator, request) pair.

        Uses triangular_mf from utils.py (shared with root fuzzy.py).

        Returns:
            Dict of {variable: {label: degree}} for distance, load,
            queue, direction, and passby.
        """
        distance  = abs(elevator.current_floor - request.floor)
        load_ratio = (elevator.current_load / elevator.capacity
                      if elevator.capacity > 0 else 0.0)
        load_ratio = max(0.0, min(1.0, load_ratio))
        queue_len = float(len(elevator.stop_queue))

        # Direction label
        if elevator.direction == request.direction:
            dir_label = "same"
        elif elevator.direction == "IDLE":
            dir_label = "idle"
        else:
            dir_label = "opposite"

        # Passing-by
        passable = (
            "not_passable"
            if dir_label == "opposite" and distance > 1
            else "passable"
        )

        return {
            "distance": {
                "near":   triangular_mf(distance,  *self.params.near),
                "medium": triangular_mf(distance,  *self.params.medium),
                "far":    triangular_mf(distance,  *self.params.far),
            },
            "load": {
                "light":    triangular_mf(load_ratio, *self.params.light),
                "moderate": triangular_mf(load_ratio, *self.params.moderate),
                "heavy":    triangular_mf(load_ratio, *self.params.heavy),
            },
            "queue": {
                "short":  triangular_mf(queue_len, *self.params.short_q),
                "medium": triangular_mf(queue_len, *self.params.medium_q),
                "long":   triangular_mf(queue_len, *self.params.long_q),
            },
            "direction": {
                "same":     1.0 if dir_label == "same"     else 0.0,
                "idle":     1.0 if dir_label == "idle"     else 0.0,
                "opposite": 1.0 if dir_label == "opposite" else 0.0,
            },
            "passby": {
                "passable":     1.0 if passable == "passable"     else 0.0,
                "not_passable": 1.0 if passable == "not_passable" else 0.0,
            },
        }

    # ───────────────────────────────────────────────────────────
    #  INFERENCE — Full Pipeline
    # ───────────────────────────────────────────────────────────

    def evaluate(self, elevator: ElevatorState,
                 request: PassengerGroupRequest,
                 traffic_mode: str) -> DecisionExplanation:
        """
        Run full fuzzy inference for one (elevator, request) pair.

        Steps:
            1. Compute membership degrees for all linguistic variables
            2. For each rule: fire strength = min(antecedent degrees) × base_weight
            3. Centroid defuzzification: score = Σ(weighted_output) / Σ(weight)
            4. Return DecisionExplanation with full activation trace

        Args:
            elevator:     Research-track ElevatorState object.
            request:      PassengerGroupRequest to evaluate.
            traffic_mode: Current traffic regime string (for logging only).

        Returns:
            DecisionExplanation with score, memberships, and rule activations.
        """
        memberships = self._memberships(elevator, request)
        activations: List[RuleActivation] = []

        num = 0.0
        den = 0.0

        for rule in self.rules:
            # Collect antecedent degrees
            strengths = [
                memberships.get(var, {}).get(label, 0.0)
                for var, label in rule.antecedents.items()
            ]
            # AND aggregation (min), scaled by rule weight
            firing  = min(strengths) if strengths else 0.0
            weighted = firing * rule.base_weight
            out_val  = self.output_values[rule.consequent]

            num += weighted * out_val
            den += weighted

            if firing > 0.0:
                activations.append(
                    RuleActivation(
                        rule_name       = rule.name,
                        firing_strength = round(firing, 4),
                        consequent_label = rule.consequent,
                        weighted_output  = round(weighted * out_val, 4),
                    )
                )

        score = (
            self.fuzzy_config.default_score_if_no_rule
            if den <= self.fuzzy_config.epsilon
            else num / den
        )

        return DecisionExplanation(
            elevator_id     = elevator.elevator_id,
            score           = round(score, 4),
            memberships     = memberships,
            rule_activations = activations,
            traffic_mode    = traffic_mode,
        )
