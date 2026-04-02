from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from research.core.config import ExperimentConfig
from research.core.models import BenchmarkRow
from research.evaluation.explainability import serialize_decisions
from research.fuzzy.adaptive_system import AdaptiveFuzzySystem
from research.ga.fuzzy_genetic_optimizer import FuzzyParameterGA, GAHyperParams
from research.simulation.environment import StochasticElevatorEnvironment
from research.strategies.fcfs import FCFSDispatch
from research.strategies.fuzzy_only import FuzzyOnlyDispatch
from research.strategies.greedy import GreedyNearestDispatch
from research.strategies.hybrid_adaptive import HybridAdaptiveDispatch
from research.strategies.look import LOOKDispatch


def _stable_seed_offset(text: str) -> int:
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(text)) % 10000


def _build_strategies(fuzzy_model: AdaptiveFuzzySystem, adaptive_fuzzy: bool) -> Dict[str, object]:
    hybrid_name = "hybrid_adaptive" if adaptive_fuzzy else "hybrid_static"
    return {
        "fcfs": FCFSDispatch(),
        "look": LOOKDispatch(),
        "greedy_nearest": GreedyNearestDispatch(),
        "fuzzy_only": FuzzyOnlyDispatch(fuzzy_model),
        hybrid_name: HybridAdaptiveDispatch(fuzzy_model, adaptive_mode=adaptive_fuzzy),
    }


def run_benchmarks(config: ExperimentConfig) -> Dict:
    fuzzy_model = AdaptiveFuzzySystem(
        fuzzy_config=config.fuzzy,
        adaptation_config=config.fuzzy_adaptation,
    )

    if config.toggles.use_ga_for_fuzzy:
        ga = FuzzyParameterGA(seed=config.seed, param_space=config.fuzzy_ga_param_space)
        hypers = GAHyperParams(
            population=config.ga.population,
            generations=min(20, config.ga.generations),
            crossover_rate=config.ga.crossover_rate,
            mutation_rate=config.ga.mutation_rate,
            elitism=config.ga.elitism,
        )

        def evaluator(chromosome):
            test_model = AdaptiveFuzzySystem(
                fuzzy_config=config.fuzzy,
                adaptation_config=config.fuzzy_adaptation,
            )
            test_model.set_optimized_parameters(chromosome)
            strategy = HybridAdaptiveDispatch(test_model)
            env = StochasticElevatorEnvironment(
                num_floors=config.building.num_floors,
                num_elevators=config.building.num_elevators,
                capacity=config.building.capacity,
                seed=config.seed + 99,
                runtime_config=config.runtime,
                route_ga_config=config.route_ga,
                dynamic_traffic_config=config.dynamic_traffic,
            )
            m = env.run(
                strategy=strategy,
                duration_seconds=config.benchmark.ga_tuning_duration_seconds,
                mode="mixed",
                base_lambda_per_min=config.traffic.base_lambda_per_min,
                spike_probability=config.traffic.spike_probability,
                enable_faults=config.toggles.enable_faults,
                stochastic_delay=config.toggles.enable_stochastic_delay,
                enable_spike_events=config.toggles.enable_spike_events,
                use_route_ga=config.toggles.use_ga_for_routes,
            )
            return ga.score_terms(
                waits=env.wait_times,
                energy=m.net_energy,
                overload_count=m.overload_violations,
            )

        best_vec, best_fit = ga.optimize(
            rule_count=len(fuzzy_model.rules),
            evaluator=evaluator,
            alpha=config.objective.alpha,
            beta=config.objective.beta,
            gamma=config.objective.gamma,
            params=hypers,
        )
        fuzzy_model.set_optimized_parameters(best_vec)
    else:
        ga = None
        best_fit = None

    strategies = _build_strategies(fuzzy_model, config.toggles.adaptive_fuzzy)

    rows: List[BenchmarkRow] = []
    explainability_logs: Dict[str, List[Dict]] = {}
    for scenario in config.scenarios:
        for name, strat in strategies.items():
            env = StochasticElevatorEnvironment(
                num_floors=config.building.num_floors,
                num_elevators=config.building.num_elevators,
                capacity=config.building.capacity,
                seed=config.seed + _stable_seed_offset(f"{scenario}:{name}"),
                runtime_config=config.runtime,
                route_ga_config=config.route_ga,
                dynamic_traffic_config=config.dynamic_traffic,
            )
            metrics = env.run(
                strategy=strat,
                duration_seconds=config.traffic.duration_seconds,
                mode=scenario,
                base_lambda_per_min=config.traffic.base_lambda_per_min,
                spike_probability=config.traffic.spike_probability,
                enable_faults=config.toggles.enable_faults,
                stochastic_delay=config.toggles.enable_stochastic_delay,
                enable_spike_events=config.toggles.enable_spike_events,
                use_route_ga=config.toggles.use_ga_for_routes,
            )
            rows.append(BenchmarkRow(strategy=name, scenario=scenario, metrics=metrics))
            explainability_logs[f"{scenario}:{name}"] = serialize_decisions(
                env.assignment_log,
                limit=config.explainability.max_saved_decisions_per_run,
            )

    table = [
        {
            "strategy": r.strategy,
            "scenario": r.scenario,
            **asdict(r.metrics),
        }
        for r in rows
    ]

    summary = _summarize(rows)
    return {
        "experiment": config.name,
        "ga_best_fitness": best_fit,
        "ga_history": [] if ga is None else ga.history,
        "rows": table,
        "summary": summary,
        "explanations": explainability_logs,
    }


def _summarize(rows: List[BenchmarkRow]) -> Dict[str, Dict[str, float]]:
    by_strategy: Dict[str, List[BenchmarkRow]] = {}
    for row in rows:
        by_strategy.setdefault(row.strategy, []).append(row)

    summary = {}
    for strategy, items in by_strategy.items():
        n = len(items)
        summary[strategy] = {
            "avg_wait": sum(i.metrics.avg_wait for i in items) / n,
            "p95_wait": sum(i.metrics.p95_wait for i in items) / n,
            "throughput_per_min": sum(i.metrics.throughput_per_min for i in items) / n,
            "net_energy": sum(i.metrics.net_energy for i in items) / n,
            "fairness_variance": sum(i.metrics.fairness_variance for i in items) / n,
            "overload_violations": sum(i.metrics.overload_violations for i in items) / n,
        }
    return summary
