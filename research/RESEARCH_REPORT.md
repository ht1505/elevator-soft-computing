# Hybrid Adaptive Intelligent Elevator System

## 1. Problem Formulation

We optimize dispatch and routing under uncertainty with multi-objective fitness:

fitness = -(avg_wait + alpha * energy + beta * variance + gamma * overload_penalty)

Where:
- avg_wait: average passenger wait time
- energy: net system energy
- variance: fairness proxy (wait-time variance across users)
- overload_penalty: strict capacity violation count

## 2. Methodology

1. Adaptive Fuzzy Dispatch:
- Parameterized triangular memberships for distance, load, and queue state.
- Rule base with tunable weights.
- Dynamic rule reweighting by traffic mode (peak_up, peak_down, inter_floor).

2. Genetic Optimization:
- Chromosome encodes fuzzy membership parameters + rule weights.
- Evolutionary search uses elitism, crossover, mutation, and tournament selection.
- Fitness computed from stochastic simulation outcomes.

3. Dynamic and Uncertain Environment:
- Poisson-like request arrivals with occasional traffic spikes.
- Stochastic travel-time delays.
- Random temporary elevator failures.
- Multi-passenger group requests and strict capacity enforcement.

4. Baselines:
- FCFS dispatch
- LOOK heuristic
- Greedy nearest-elevator
- Fuzzy-only
- Hybrid adaptive (fuzzy + dynamic adaptation + GA-tuned parameters)

## 3. Experiment Design

- All strategies run on identical scenario set and durations.
- Scenarios: peak_up, peak_down, inter_floor, mixed.
- Metrics: avg wait, p95 wait, throughput, energy, fairness variance.

## 4. Explainability Layer

For each fuzzy decision:
- membership values by variable
- fired rules and strengths
- defuzzified final score

## 5. Artifacts

- Config: research/experiments/default_experiment.json
- Runner: research/run_research_demo.py
- Results: research/results/benchmark_results.json
- Plots: research/results/*.png

## 6. Notes

This upgrade creates a research-grade experimental track without breaking the existing legacy runtime and tests.
