from __future__ import annotations

from pathlib import Path

from research.core.config import (
    DEFAULT_EXPERIMENT,
    BuildingConfig,
    ExperimentConfig,
    ExperimentToggles,
    GAConfig,
    ObjectiveConfig,
    TrafficConfig,
    dump_results,
)
from research.evaluation.benchmark import run_benchmarks
from research.visualization.plots import create_plots


def _read_int(prompt: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            value = default
        else:
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a valid integer.")
                continue

        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be <= {maximum}.")
            continue
        return value


def _read_float(prompt: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            value = default
        else:
            try:
                value = float(raw)
            except ValueError:
                print("Please enter a valid number.")
                continue

        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be <= {maximum}.")
            continue
        return value


def _read_bool(prompt: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} ({suffix}): ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "1", "true"}:
            return True
        if raw in {"n", "no", "0", "false"}:
            return False
        print("Please answer y or n.")


def _build_user_config() -> ExperimentConfig:
    defaults = DEFAULT_EXPERIMENT
    print("\n=== Research Benchmark Parameters ===")
    seed = _read_int("Random seed", defaults.seed, minimum=0)

    floors = _read_int("Number of floors", defaults.building.num_floors, minimum=5, maximum=200)
    elevators = _read_int("Number of elevators", defaults.building.num_elevators, minimum=1, maximum=32)
    capacity = _read_int("Elevator capacity", defaults.building.capacity, minimum=1, maximum=50)

    duration = _read_int("Simulation duration (seconds)", defaults.traffic.duration_seconds, minimum=60)
    lam = _read_float("Base arrival rate lambda (requests/min)", defaults.traffic.base_lambda_per_min, minimum=0.1)
    spike_prob = _read_float("Traffic spike probability", defaults.traffic.spike_probability, minimum=0.0, maximum=1.0)

    alpha = _read_float("Objective alpha (energy weight)", defaults.objective.alpha, minimum=0.0)
    beta = _read_float("Objective beta (fairness variance weight)", defaults.objective.beta, minimum=0.0)
    gamma = _read_float("Objective gamma (overload penalty)", defaults.objective.gamma, minimum=0.0)

    pop = _read_int("GA population", defaults.ga.population, minimum=4)
    gens = _read_int("GA generations", defaults.ga.generations, minimum=1)
    cx = _read_float("GA crossover rate", defaults.ga.crossover_rate, minimum=0.0, maximum=1.0)
    mut = _read_float("GA mutation rate", defaults.ga.mutation_rate, minimum=0.0, maximum=1.0)
    elit = _read_int("GA elitism", defaults.ga.elitism, minimum=0)

    print("\n=== Feature Toggles ===")
    adaptive = _read_bool("Adaptive fuzzy rules", defaults.toggles.adaptive_fuzzy)
    ga_fuzzy = _read_bool("GA optimize fuzzy parameters", defaults.toggles.use_ga_for_fuzzy)
    ga_routes = _read_bool("GA route optimization enabled flag", defaults.toggles.use_ga_for_routes)
    faults = _read_bool("Enable random faults", defaults.toggles.enable_faults)
    noise = _read_bool("Enable stochastic delay", defaults.toggles.enable_stochastic_delay)
    spikes = _read_bool("Enable traffic spikes", defaults.toggles.enable_spike_events)

    print("\nScenarios example: peak_up,peak_down,inter_floor,mixed")
    raw_scenarios = input("Scenarios (comma-separated) [peak_up,peak_down,inter_floor,mixed]: ").strip()
    if raw_scenarios:
        scenarios = [s.strip() for s in raw_scenarios.split(",") if s.strip()]
    else:
        scenarios = ["peak_up", "peak_down", "inter_floor", "mixed"]

    return ExperimentConfig(
        name="user_defined_experiment",
        seed=seed,
        building=BuildingConfig(num_floors=floors, num_elevators=elevators, capacity=capacity),
        traffic=TrafficConfig(mode="mixed", duration_seconds=duration, base_lambda_per_min=lam, spike_probability=spike_prob),
        objective=ObjectiveConfig(alpha=alpha, beta=beta, gamma=gamma),
        ga=GAConfig(population=pop, generations=gens, crossover_rate=cx, mutation_rate=mut, elitism=elit),
        toggles=ExperimentToggles(
            adaptive_fuzzy=adaptive,
            use_ga_for_fuzzy=ga_fuzzy,
            use_ga_for_routes=ga_routes,
            enable_faults=faults,
            enable_stochastic_delay=noise,
            enable_spike_events=spikes,
        ),
        scenarios=scenarios,
    )


def _run_research_mode() -> None:
    cfg = _build_user_config()
    results = run_benchmarks(cfg)

    root = Path(__file__).resolve().parent
    out_dir = root / "research" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_json = out_dir / "benchmark_results_user.json"
    dump_results(out_json, results)
    plots = create_plots(results, out_dir, cfg.visualization)

    print("\n=== Benchmark Completed ===")
    print(f"Results JSON: {out_json}")
    if plots:
        print("Plots:")
        for p in plots:
            print(f"- {p}")

    print("\n=== Strategy Summary ===")
    for strategy, stats in results.get("summary", {}).items():
        print(
            f"{strategy:16} wait={stats['avg_wait']:.2f}s p95={stats['p95_wait']:.2f}s "
            f"thr={stats['throughput_per_min']:.2f}/min energy={stats['net_energy']:.2f} "
            f"fair={stats['fairness_variance']:.2f} overload={stats['overload_violations']:.2f}"
        )


def _run_legacy_mode() -> None:
    from main import main as legacy_main

    print("\nLaunching legacy interactive system...\n")
    legacy_main()


def main() -> None:
    print("=" * 62)
    print("SMART ELEVATOR USER LAUNCHER")
    print("1) Legacy interactive system")
    print("2) Research benchmark system (parameterized)")
    print("=" * 62)

    choice = input("Choose mode [2]: ").strip()
    if choice in {"", "2"}:
        _run_research_mode()
    elif choice == "1":
        _run_legacy_mode()
    else:
        print("Invalid option. Please run again and select 1 or 2.")


if __name__ == "__main__":
    main()
