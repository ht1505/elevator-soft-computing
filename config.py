"""
config.py — All constants for the Smart Elevator Management System.

This is the single source of truth for both the legacy interactive track
(root-level modules) and is referenced for baseline values in the
research track (research/core/config.py uses equivalent dataclasses).

Cross-reference:
  • research/core/config.py — mirrors these values as dataclass defaults
    (FuzzyConfig, RuntimeConfig, RouteGAConfig, etc.).  Any intentional
    divergence is documented with a note at the relevant constant.
  • utils.py — shared pure utility functions (triangular_mf, poisson_sample,
    percentile, fmt_*) imported by both tracks.

No magic numbers anywhere else in the codebase.
"""

# ─── Elevator Mechanics ───────────────────────────────────────
FLOOR_TRAVEL_TIME = 3       # seconds to travel one floor (constant speed phase)
DOOR_OPEN_TIME    = 2       # seconds door stays fully open
DOOR_CLOSE_TIME   = 1       # seconds to complete door close animation
MAX_CAPACITY      = 8       # maximum passengers per elevator cabin

# ─── Movement Timing ─────────────────────────────────────────
ACCEL_PHASE_TIME   = 2.0    # seconds for acceleration ramp (0 → max speed)
DECEL_PHASE_TIME   = 1.5    # seconds for deceleration ramp (max speed → 0)
DOOR_OPENING_TIME  = 0.8    # seconds for door-open animation
LEVELING_TOLERANCE = 0.03   # floor alignment precision (fractional floor units)

# ─── Simulation ──────────────────────────────────────────────
SIM_TICK_SIZE            = 0.5    # simulation clock tick in seconds
SIM_POISSON_LAMBDA_LIGHT = 0.5    # requests/minute — light traffic
SIM_POISSON_LAMBDA_PEAK  = 4.0    # requests/minute — peak traffic
SIM_POISSON_LAMBDA_INTER = 2.0    # requests/minute — inter-floor traffic
SIM_SCENARIO_DURATION    = 600    # seconds per benchmark scenario run
SIM_MAX_FLOORS           = 50     # startup validation ceiling for floors
SIM_MAX_ELEVATORS        = 10     # startup validation ceiling for elevators
BENCHMARK_SETTLE_SECONDS = 300    # extra simulation tail for in-flight completion

# ─── Direction Constants ─────────────────────────────────────
DIR_UP   = "UP"
DIR_DOWN = "DOWN"
DIR_IDLE = "IDLE"

# ─── Elevator States (13-State Machine) ──────────────────────
# Idle
STATE_IDLE         = "IDLE"

# Movement phases: acceleration → constant speed → deceleration
STATE_ACCEL_UP     = "ACCEL_UP"       # ramping up speed (going up)
STATE_ACCEL_DOWN   = "ACCEL_DOWN"     # ramping up speed (going down)
STATE_MOVING_UP    = "MOVING_UP"      # constant speed (going up)
STATE_MOVING_DOWN  = "MOVING_DOWN"    # constant speed (going down)
STATE_DECEL_UP     = "DECEL_UP"       # ramping down speed (going up)
STATE_DECEL_DOWN   = "DECEL_DOWN"     # ramping down speed (going down)
STATE_LEVELING     = "LEVELING"       # precise floor alignment

# Door operations
STATE_DOOR_PRE_OPEN = "DOOR_PRE_OPEN"  # safety/overload check before opening
STATE_DOOR_OPENING  = "DOOR_OPENING"   # door animating open  (0.0 → 1.0)
STATE_DOOR_OPEN     = "DOOR_OPEN"      # door fully open, dwell time
STATE_DOOR_CLOSING  = "DOOR_CLOSING"   # door animating closed (1.0 → 0.0)

# Fault / emergency states
STATE_OVERLOAD    = "OVERLOAD"      # passenger load exceeds MAX_CAPACITY
STATE_DOOR_STUCK  = "DOOR_STUCK"   # door mechanism failure after max reopens
STATE_E_STOP      = "E_STOP"       # emergency stop engaged
STATE_FIRE_RECALL = "FIRE_RECALL"  # fire mode — all elevators return to lobby

# ─── Traffic Modes (Legacy Track) ────────────────────────────
# Detected by TrafficAnalyzer in traffic.py.
MODE_UP_PEAK     = "UP_PEAK"
MODE_DOWN_PEAK   = "DOWN_PEAK"
MODE_INTER_FLOOR = "INTER_FLOOR"
MODE_BALANCED    = "BALANCED"
MODE_LIGHT       = "LIGHT"

# ─── Traffic Modes (Research Track) ──────────────────────────
# NOTE: The research track uses lowercase underscore naming for scenario
# strings (e.g. "peak_up") while the legacy track uses SCREAMING_SNAKE
# (e.g. "UP_PEAK"). Both are intentionally separate — the research track
# BenchmarkScenario and StochasticElevatorEnvironment use these strings.
RESEARCH_MODE_PEAK_UP     = "peak_up"
RESEARCH_MODE_PEAK_DOWN   = "peak_down"
RESEARCH_MODE_INTER_FLOOR = "inter_floor"
RESEARCH_MODE_MIXED       = "mixed"

# ─── Fuzzy Logic Membership Function Breakpoints ─────────────
# Used by fuzzy.py to construct triangular membership functions via
# utils.triangular_mf(). Each triple is (left_foot, peak, right_foot).
FUZZY_DIST_NEAR   = (0.0, 0.0, 5.0)    # distance: near  (floors)
FUZZY_DIST_MEDIUM = (2.0, 5.0, 9.0)    # distance: medium
FUZZY_DIST_FAR    = (6.0, 12.0, 25.0)  # distance: far

FUZZY_LOAD_LIGHT    = (0.0, 0.0, 0.6)   # load ratio: light  [0,1]
FUZZY_LOAD_MODERATE = (0.2, 0.5, 0.8)   # load ratio: moderate
FUZZY_LOAD_HEAVY    = (0.6, 1.0, 1.0)   # load ratio: heavy

FUZZY_QUEUE_SHORT  = (0.0, 0.0, 5.0)   # queue length: short (stops)
FUZZY_QUEUE_MEDIUM = (2.0, 4.0, 7.0)   # queue length: medium
FUZZY_QUEUE_LONG   = (5.0, 9.0, 20.0)  # queue length: long

# ─── Fuzzy Output Suitability Scale ──────────────────────────
# These five values are the crisp consequent outputs for each linguistic label.
# Cross-reference: research/core/config.py → FuzzyConfig.output_* mirrors these.
FUZZY_VERY_LOW  = 10
FUZZY_LOW       = 30
FUZZY_MEDIUM    = 50
FUZZY_HIGH      = 75
FUZZY_VERY_HIGH = 95

# ─── Traffic Analysis ────────────────────────────────────────
TRAFFIC_WINDOW_SIZE = 10    # number of recent requests in sliding window

# ─── Mass & Safety ───────────────────────────────────────────
MAX_LOAD_KG          = 630  # maximum cabin weight capacity
KG_PER_PERSON        = 75   # average passenger mass in kg
DOOR_STUCK_THRESHOLD = 3    # number of reopen attempts before DOOR_STUCK fault

# ─── Energy Constants ────────────────────────────────────────
# Cross-reference: research/core/config.py → RuntimeConfig uses the same
# baseline values (energy_up_base=1.0, energy_up_load_factor=0.1).
ENERGY_PER_FLOOR    = 1.0   # base energy units per floor traveled upward
ENERGY_LOAD_FACTOR  = 0.1   # additional energy per passenger per floor upward
ENERGY_REGEN_FACTOR = 0.3   # fraction of downward travel energy recovered

# ─── GA Fitness Weights ──────────────────────────────────────
GA_WEIGHT_DISTANCE      = 0.40   # weight: total fleet travel distance
GA_WEIGHT_ENERGY        = 0.35   # weight: net energy consumption
GA_WEIGHT_COMFORT       = 0.25   # weight: passenger comfort (reversals)
GA_REGEN_FACTOR_DESCENT = 0.45   # regeneration credit per floor during descent
GA_ACCEL_PENALTY        = 1.8    # cost added per direction reversal in route
GA_REVERSAL_PENALTY     = GA_ACCEL_PENALTY  # legacy alias

# ─── Genetic Algorithm Parameters ────────────────────────────
GA_POPULATION      = 30     # chromosome population per generation
GA_GENERATIONS     = 75     # total generations to evolve
GA_CROSSOVER_RATE  = 0.85   # probability that two parents exchange genes
GA_MUTATION_RATE   = 0.12   # probability of swap mutation per chromosome
GA_TOURNAMENT_SIZE = 4      # candidate pool size for tournament selection
GA_ELITISM_COUNT   = 2      # top chromosomes carried forward unchanged

# ─── Demand Forecasting ──────────────────────────────────────
FORECAST_ALPHA        = 0.25    # exponential smoothing factor (0 < α < 1)
FORECAST_SLOTS        = 12      # number of time slots in one simulated hour
FORECAST_SLOT_SECONDS = 300     # slot width in seconds (12 × 300 = 3600 s = 1 h)


# ═══════════════════════════════════════════════════════════════
#  SELF-VALIDATION — Run at Import Time
# ═══════════════════════════════════════════════════════════════

def _validate_constants() -> None:
    """
    Assert that all numeric constants are within their valid ranges.

    Called automatically when this module is imported.
    Raises AssertionError with a descriptive message on misconfiguration.
    """
    assert MAX_CAPACITY >= 1, f"MAX_CAPACITY must be >= 1, got {MAX_CAPACITY}"
    assert FLOOR_TRAVEL_TIME > 0, f"FLOOR_TRAVEL_TIME must be > 0, got {FLOOR_TRAVEL_TIME}"
    assert DOOR_OPEN_TIME >= 0, f"DOOR_OPEN_TIME must be >= 0, got {DOOR_OPEN_TIME}"
    assert SIM_TICK_SIZE > 0, f"SIM_TICK_SIZE must be > 0, got {SIM_TICK_SIZE}"
    assert 0.0 < GA_CROSSOVER_RATE <= 1.0, \
        f"GA_CROSSOVER_RATE must be in (0, 1], got {GA_CROSSOVER_RATE}"
    assert 0.0 < GA_MUTATION_RATE <= 1.0, \
        f"GA_MUTATION_RATE must be in (0, 1], got {GA_MUTATION_RATE}"
    assert GA_POPULATION >= 4, f"GA_POPULATION must be >= 4, got {GA_POPULATION}"
    assert GA_GENERATIONS >= 1, f"GA_GENERATIONS must be >= 1, got {GA_GENERATIONS}"
    assert GA_ELITISM_COUNT < GA_POPULATION, \
        f"GA_ELITISM_COUNT ({GA_ELITISM_COUNT}) must be < GA_POPULATION ({GA_POPULATION})"
    assert ENERGY_PER_FLOOR > 0, f"ENERGY_PER_FLOOR must be > 0, got {ENERGY_PER_FLOOR}"
    assert 0.0 <= ENERGY_LOAD_FACTOR <= 1.0, \
        f"ENERGY_LOAD_FACTOR must be in [0, 1], got {ENERGY_LOAD_FACTOR}"
    assert 0.0 <= ENERGY_REGEN_FACTOR <= 1.0, \
        f"ENERGY_REGEN_FACTOR must be in [0, 1], got {ENERGY_REGEN_FACTOR}"
    assert 0.0 < FORECAST_ALPHA < 1.0, \
        f"FORECAST_ALPHA must be in (0, 1), got {FORECAST_ALPHA}"
    assert FUZZY_VERY_LOW < FUZZY_LOW < FUZZY_MEDIUM < FUZZY_HIGH < FUZZY_VERY_HIGH, \
        "Fuzzy output scale must be strictly increasing"
    weights_sum = GA_WEIGHT_DISTANCE + GA_WEIGHT_ENERGY + GA_WEIGHT_COMFORT
    assert abs(weights_sum - 1.0) < 1e-6, \
        f"GA fitness weights must sum to 1.0, got {weights_sum:.6f}"


_validate_constants()
