# Smart Elevator System

Production-ready soft-computing elevator control repository with two aligned execution tracks:

1. Legacy operational track: interactive multi-elevator controller using fuzzy dispatch + GA route optimization.
2. Research track: hybrid adaptive architecture with stochastic simulation, strategy benchmarking, explainability export, and visualization artifacts.

## Core Objective

For a stream of dynamic hall calls, solve:

1. Dispatch: choose the best elevator for each request.
2. Routing: optimize stop order to reduce global cost.

Primary optimization signals:

- wait time
- energy
- fairness (variance of user wait)
- overload avoidance

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
