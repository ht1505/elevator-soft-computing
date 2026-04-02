from __future__ import annotations

from pathlib import Path

from research.core.config import dump_results, load_experiment_config
from research.evaluation.benchmark import run_benchmarks
from research.fuzzy.adaptive_system import AdaptiveFuzzySystem
from research.simulation.environment import StochasticElevatorEnvironment
from research.strategies.hybrid_adaptive import HybridAdaptiveDispatch
from research.visualization.plots import create_plots
from research.visualization.realtime import render_snapshot


def _run_realtime_demo(cfg) -> None:
    print("\nRealtime demo (hybrid strategy, short horizon):")
    fuzzy_model = AdaptiveFuzzySystem(
        fuzzy_config=cfg.fuzzy,
        adaptation_config=cfg.fuzzy_adaptation,
    )
    strategy = HybridAdaptiveDispatch(fuzzy_model, adaptive_mode=cfg.toggles.adaptive_fuzzy)
    env = StochasticElevatorEnvironment(
        num_floors=cfg.building.num_floors,
        num_elevators=cfg.building.num_elevators,
        capacity=cfg.building.capacity,
        seed=cfg.seed + 123,
        runtime_config=cfg.runtime,
        route_ga_config=cfg.route_ga,
        dynamic_traffic_config=cfg.dynamic_traffic,
    )

    def _cb(elevators, floors, t):
        print(render_snapshot(elevators, floors, t))

    demo_duration = min(cfg.traffic.duration_seconds, cfg.runtime.realtime_interval_seconds * 3)
    env.run(
        strategy=strategy,
        duration_seconds=demo_duration,
        mode=cfg.traffic.mode,
        base_lambda_per_min=cfg.traffic.base_lambda_per_min,
        spike_probability=cfg.traffic.spike_probability,
        enable_faults=cfg.toggles.enable_faults,
        stochastic_delay=cfg.toggles.enable_stochastic_delay,
        enable_spike_events=cfg.toggles.enable_spike_events,
        use_route_ga=cfg.toggles.use_ga_for_routes,
        realtime_callback=_cb,
        realtime_interval=cfg.runtime.realtime_interval_seconds,
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    cfg = load_experiment_config(root / "experiments" / "default_experiment.json")
    _run_realtime_demo(cfg)
    results = run_benchmarks(cfg)

    out_json = root / "results" / "benchmark_results.json"
    dump_results(out_json, results)

    generated = create_plots(results, root / "results", cfg.visualization)

    print("Research benchmark completed.")
    print(f"Results file: {out_json}")
    if generated:
        print("Generated plots:")
        for p in generated:
            print(f"  - {p}")

    print("\nSummary:")
    for strategy, stats in results.get("summary", {}).items():
        print(
            f"{strategy:16} wait={stats['avg_wait']:.2f}s p95={stats['p95_wait']:.2f}s "
            f"thr={stats['throughput_per_min']:.2f}/min energy={stats['net_energy']:.2f} "
            f"fair={stats['fairness_variance']:.2f} overload={stats['overload_violations']:.2f}"
        )


if __name__ == "__main__":
    main()
