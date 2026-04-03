# Smart Elevator System

Production-ready soft-computing elevator control repository with two aligned execution tracks:

1. **Legacy operational track**: interactive multi-elevator controller using fuzzy dispatch + GA route optimization.
2. **Research track**: hybrid adaptive architecture with stochastic simulation, strategy benchmarking, explainability export, and visualization artifacts.

## Core Objective

For a stream of dynamic hall calls, solve:

1. **Dispatch problem**: choose the best elevator for each request (solved by fuzzy logic).
2. **Routing problem**: optimize stop order to reduce global cost (solved by genetic algorithm).

Primary optimization signals:

- **Wait time**: minimize passenger waiting duration
- **Energy**: reduce power consumption and vertical travel
- **Fairness**: minimize variance in user experience (prevent some passengers waiting too long)
- **Overload avoidance**: balance load across elevators

---

## Technical Highlights

### Fuzzy Logic for Intelligent Dispatch

The system uses fuzzy logic to make contextual dispatch decisions by evaluating:**

- **Distance fuzzy sets**: near, medium, far elevator-to-floor distances
- **Load fuzzy sets**: light, medium, heavy elevator occupancy
- **Queue fuzzy sets**: short, medium, long request queues
- **Direction compatibility**: how well elevator motion aligns with request direction
- **Mamdani rule engine**: 15+ linguistic rules firing simultaneously with partial confidence

Output: **interpretable suitability scores** with reasoning (why elevator 2 was better than elevator 3).

### Genetic Algorithm for Global Route Optimization

The system uses an **NSGA-II (Non-dominated Sorting Genetic Algorithm II)** to optimize elevator routes:

- **Population-based search**: evolves 100+ candidate route orderings
- **Multi-objective optimization**: balances distance, energy, and comfort via Pareto front discovery
- **Crossover operators**: Order Crossover (OX1) preserves stop sequences while mixing parents
- **Adaptive mutation**: 4 mutation operators (swap, inversion, insertion, displacement) with generation-dependent weights
- **Convergence detection**: stops iteration early when population stagnates
- **Time-based simulation fitness**: evaluates assignments using discrete-event simulation for realistic cost prediction

Output: **globally optimized routes** that are typically 30-50% better than greedy nearest-stop heuristics.

## Project Layout

- Legacy runtime modules (stable path):
	- `config.py`
	- `main.py`
	- `elevator.py`
	- `request.py`
	- `fuzzy.py`
	- `ga.py`
	- `simulation.py`
	- `traffic.py`
	- `logger.py`
	- `visualizer.py`

- Research-grade modular architecture:
	- `research/core/`
	- `research/fuzzy/`
	- `research/ga/`
	- `research/simulation/`
	- `research/strategies/`
	- `research/evaluation/`
	- `research/visualization/`
	- `research/experiments/`
	- `research/results/`

- Validation:
	- `test/`

- Interactive launcher:
	- `user.py`

## Run Modes

### 1) User Launcher (recommended)

```bash
python user.py
```

This lets you choose:

1. Legacy interactive system
2. Research benchmark mode with user-provided parameters

### 2) Legacy Interactive Runtime

```bash
python main.py
```

### 3) Research Benchmark + Demo

```bash
python -m research.run_research_demo
```

Outputs:

- `research/results/benchmark_results.json`
- GA convergence plot
- strategy comparison plots
- traffic heatmap
- explainability traces embedded in result JSON

## Tests

Run all tests from repository root:

```bash
python test/test_config.py
python test/test_request.py
python test/test_elevator.py
python test/test_fuzzy.py
python test/test_ga.py
python test/test_traffic.py
python test/test_simulation.py
python test/test_logger.py
python test/test_visualizer.py
python test/test_integration.py
python test/test_edge_cases.py
python test/test_research_track.py
```

## Repository Hygiene

- Cache, temp, and generated artifacts are ignored via `.gitignore`.
- Benchmark and visualization outputs are written under `research/results/`.
- Source behavior is config-driven (legacy `config.py` + research experiment JSON/config dataclasses).

## Documentation

- Conceptual and pipeline details: `explain.md`
- Research architecture and methodology: `research/README.md`
- Architecture audit: `research/ARCHITECTURE_AUDIT.md`
- Technical report: `research/RESEARCH_REPORT.md`
