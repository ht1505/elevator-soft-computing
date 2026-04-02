from __future__ import annotations

"""
research/core/config.py — Research-track experiment configuration dataclasses.

All configuration is expressed as nested Python dataclasses so that
experiments are fully parameterised, serialisable, and reproducible.

Cross-reference:
    config.py (root) — legacy production constants; baseline values
    here should match those in config.py unless intentionally diverged.
    utils.py  — shared utilities (triangular_mf, poisson_sample, etc.)

Defaults are set to match root config.py baseline values.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class ExperimentToggles:
    adaptive_fuzzy: bool = True
    use_ga_for_fuzzy: bool = True
    use_ga_for_routes: bool = True
    enable_faults: bool = True
    enable_stochastic_delay: bool = True
    enable_spike_events: bool = True


@dataclass
class BuildingConfig:
    """Physical layout of the simulated building."""
    num_floors:    int = 20  # total floors (mirrors SIM_MAX_FLOORS upper bound)
    num_elevators: int = 4   # number of elevator cars
    capacity:      int = 10  # max passengers per cabin (cf. MAX_CAPACITY in config.py)

    def __post_init__(self) -> None:
        assert self.num_floors >= 2,    f"num_floors must be >= 2, got {self.num_floors}"
        assert self.num_elevators >= 1, f"num_elevators must be >= 1, got {self.num_elevators}"
        assert self.capacity >= 1,      f"capacity must be >= 1, got {self.capacity}"


@dataclass
class TrafficConfig:
    """Passenger arrival model for one scenario run."""
    mode:                str   = "mixed"  # peak_up | peak_down | inter_floor | mixed
    duration_seconds:    int   = 600      # seconds to simulate
    base_lambda_per_min: float = 3.0      # mean Poisson arrival rate (passengers/min)
    spike_probability:   float = 0.05     # per-tick probability of a demand spike

    def __post_init__(self) -> None:
        valid_modes = {"peak_up", "peak_down", "inter_floor", "mixed"}
        assert self.mode in valid_modes, \
            f"mode must be one of {valid_modes}, got '{self.mode}'"
        assert self.duration_seconds >= 10, \
            f"duration_seconds must be >= 10, got {self.duration_seconds}"
        assert self.base_lambda_per_min > 0, \
            f"base_lambda_per_min must be > 0, got {self.base_lambda_per_min}"
        assert 0.0 <= self.spike_probability <= 1.0, \
            f"spike_probability must be in [0,1], got {self.spike_probability}"


@dataclass
class ObjectiveConfig:
    alpha: float = 0.20
    beta: float = 0.25
    gamma: float = 3.0


@dataclass
class GAConfig:
    """Parameters for the FuzzyParameterGA (fuzzy membership optimisation)."""
    population:     int   = 30    # chromosome population size
    generations:    int   = 50    # number of generations
    crossover_rate: float = 0.85  # probability of crossover
    mutation_rate:  float = 0.15  # probability of mutation per gene
    elitism:        int   = 2     # top chromosomes kept unchanged

    def __post_init__(self) -> None:
        assert self.population >= 4, \
            f"population must be >= 4, got {self.population}"
        assert self.generations >= 1, \
            f"generations must be >= 1, got {self.generations}"
        assert 0.0 < self.crossover_rate <= 1.0, \
            f"crossover_rate must be in (0,1], got {self.crossover_rate}"
        assert 0.0 < self.mutation_rate <= 1.0, \
            f"mutation_rate must be in (0,1], got {self.mutation_rate}"
        assert self.elitism < self.population, \
            f"elitism ({self.elitism}) must be < population ({self.population})"


@dataclass
class FuzzyConfig:
    # Membership triangles
    distance_near: Tuple[float, float, float] = (0.0, 0.0, 4.0)
    distance_medium: Tuple[float, float, float] = (2.0, 6.0, 10.0)
    distance_far: Tuple[float, float, float] = (7.0, 14.0, 25.0)
    load_light: Tuple[float, float, float] = (0.0, 0.0, 0.4)
    load_moderate: Tuple[float, float, float] = (0.2, 0.5, 0.8)
    load_heavy: Tuple[float, float, float] = (0.6, 1.0, 1.0)
    queue_short: Tuple[float, float, float] = (0.0, 0.0, 2.5)
    queue_medium: Tuple[float, float, float] = (1.5, 4.0, 7.0)
    queue_long: Tuple[float, float, float] = (5.0, 10.0, 20.0)

    # Crisp consequent output values (match root config.py FUZZY_* constants).
    # NOTE: output_medium and output_high differ slightly from the legacy 50/75
    # to utilise the full [0,100] range in the research adaptive system.
    output_very_low:          float = 10.0   # cf. FUZZY_VERY_LOW  = 10
    output_low:               float = 30.0   # cf. FUZZY_LOW       = 30
    output_medium:            float = 55.0   # cf. FUZZY_MEDIUM    = 50  (tuned)
    output_high:              float = 80.0   # cf. FUZZY_HIGH      = 75  (tuned)
    output_very_high:         float = 95.0   # cf. FUZZY_VERY_HIGH = 95
    default_score_if_no_rule: float = 25.0
    epsilon:                  float = 1e-9

    def __post_init__(self) -> None:
        vals = [
            self.output_very_low, self.output_low, self.output_medium,
            self.output_high, self.output_very_high,
        ]
        assert vals == sorted(vals), \
            f"FuzzyConfig output values must be strictly increasing: {vals}"


@dataclass
class FuzzyAdaptationConfig:
    peak_up_r10: float = 1.10
    peak_up_r1: float = 1.05
    peak_up_r9: float = 0.95
    peak_down_r10: float = 1.10
    peak_down_r2: float = 1.05
    peak_down_r9: float = 0.95
    inter_floor_r3: float = 1.12
    inter_floor_r5: float = 1.08
    inter_floor_r6: float = 0.95
    weight_min: float = 0.2
    weight_max: float = 1.8


@dataclass
class FuzzyGAParamSpace:
    triangle_gene_count: int = 15
    triangle_min: float = 0.0
    triangle_max: float = 16.0
    rule_weight_min: float = 0.6
    rule_weight_max: float = 1.3
    mutate_sigma_triangle: float = 0.6
    mutate_sigma_rule: float = 0.08
    tournament_k: int = 3


@dataclass
class RouteGAConfig:
    generations: int = 30
    population: int = 18
    mutation_rate: float = 0.2
    elites: int = 2
    selection_pool_divisor: int = 2
    min_route_length_for_optimization: int = 3
    reversal_penalty: float = 1.8


@dataclass
class RuntimeConfig:
    travel_time_per_floor_base: float = 3.0
    travel_time_noise_std: float = 0.45
    travel_time_per_floor_min: float = 2.2
    fault_probability_per_tick: float = 0.0015
    fault_duration_min_seconds: float = 12.0
    fault_duration_max_seconds: float = 45.0
    # Energy model — aligned with root config.py (ENERGY_PER_FLOOR=1.0,
    # ENERGY_LOAD_FACTOR=0.1).  energy_down_* reflects regenerative credit.
    energy_up_base:         float = 1.0   # cf. ENERGY_PER_FLOOR    = 1.0
    energy_up_load_factor:  float = 0.1   # cf. ENERGY_LOAD_FACTOR  = 0.1  (was 0.08)
    energy_down_base:       float = 0.7   # base energy on descent (regeneration credit)
    energy_down_load_factor: float = 0.06 # load modifier on descent
    max_floor_step_per_tick: float = 1.0
    passenger_group_max_base: int = 3
    passenger_group_max_spike: int = 4
    simulation_step_seconds: float = 1.0
    realtime_interval_seconds: int = 30


@dataclass
class DynamicTrafficConfig:
    window_size: int = 30
    min_samples_for_mode_detection: int = 6
    peak_ratio_threshold: float = 0.68
    inter_floor_diversity_threshold: float = 0.5
    inter_floor_span_threshold: int = 5


@dataclass
class BenchmarkConfig:
    ga_tuning_duration_seconds: int = 180


@dataclass
class ExplainabilityConfig:
    max_saved_decisions_per_run: int = 120


@dataclass
class VisualizationConfig:
    dpi: int = 140
    label_rotation: int = 25
    convergence_color: str = "#0b7285"
    wait_bar_color: str = "#2f9e44"
    fairness_bar_color: str = "#e67700"
    heatmap_cmap: str = "YlGnBu"


@dataclass
class ExperimentConfig:
    name: str = "default"
    seed: int = 42
    building: BuildingConfig = field(default_factory=BuildingConfig)
    traffic: TrafficConfig = field(default_factory=TrafficConfig)
    objective: ObjectiveConfig = field(default_factory=ObjectiveConfig)
    ga: GAConfig = field(default_factory=GAConfig)
    toggles: ExperimentToggles = field(default_factory=ExperimentToggles)
    fuzzy: FuzzyConfig = field(default_factory=FuzzyConfig)
    fuzzy_adaptation: FuzzyAdaptationConfig = field(default_factory=FuzzyAdaptationConfig)
    fuzzy_ga_param_space: FuzzyGAParamSpace = field(default_factory=FuzzyGAParamSpace)
    route_ga: RouteGAConfig = field(default_factory=RouteGAConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    dynamic_traffic: DynamicTrafficConfig = field(default_factory=DynamicTrafficConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    explainability: ExplainabilityConfig = field(default_factory=ExplainabilityConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    scenarios: List[str] = field(default_factory=lambda: ["peak_up", "peak_down", "inter_floor", "mixed"])


DEFAULT_EXPERIMENT = ExperimentConfig()


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    building = BuildingConfig(**data.get("building", {}))
    traffic = TrafficConfig(**data.get("traffic", {}))
    objective = ObjectiveConfig(**data.get("objective", {}))
    ga = GAConfig(**data.get("ga", {}))
    toggles = ExperimentToggles(**data.get("toggles", {}))
    fuzzy = FuzzyConfig(**data.get("fuzzy", {}))
    fuzzy_adaptation = FuzzyAdaptationConfig(**data.get("fuzzy_adaptation", {}))
    fuzzy_ga_param_space = FuzzyGAParamSpace(**data.get("fuzzy_ga_param_space", {}))
    route_ga = RouteGAConfig(**data.get("route_ga", {}))
    runtime = RuntimeConfig(**data.get("runtime", {}))
    dynamic_traffic = DynamicTrafficConfig(**data.get("dynamic_traffic", {}))
    benchmark = BenchmarkConfig(**data.get("benchmark", {}))
    explainability = ExplainabilityConfig(**data.get("explainability", {}))
    visualization = VisualizationConfig(**data.get("visualization", {}))

    return ExperimentConfig(
        name=data.get("name", "custom"),
        seed=data.get("seed", 42),
        building=building,
        traffic=traffic,
        objective=objective,
        ga=ga,
        toggles=toggles,
        fuzzy=fuzzy,
        fuzzy_adaptation=fuzzy_adaptation,
        fuzzy_ga_param_space=fuzzy_ga_param_space,
        route_ga=route_ga,
        runtime=runtime,
        dynamic_traffic=dynamic_traffic,
        benchmark=benchmark,
        explainability=explainability,
        visualization=visualization,
        scenarios=data.get("scenarios", ["peak_up", "peak_down", "inter_floor", "mixed"]),
    )


def dump_results(path: str | Path, payload: Dict) -> None:
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
