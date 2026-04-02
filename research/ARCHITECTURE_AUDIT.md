# Architecture Audit (Phase 1)

## Current Weaknesses Detected

1. Tight coupling in runtime orchestration:
- Dispatch, optimization, simulation stepping, logging, and UI output are mixed in one imperative flow.
- Hard to swap algorithms independently for controlled experiments.

2. Static fuzzy model:
- Membership functions and rule effects are fixed constants.
- No systematic way to tune parameters under changing traffic patterns.

3. Limited strategy abstraction:
- Baseline policies are not encapsulated behind common interfaces.
- Benchmarking identical scenarios across methods is cumbersome.

4. Incomplete uncertainty model:
- Faults, stochastic delays, and bursty demand were not first-class simulation controls.

5. Weak experiment reproducibility:
- No dedicated config-driven experiment runner for repeatable studies.

## Redesigned Modular Architecture

The research package introduces clean separation:

- core/
  - model contracts, metrics entities, strategy interfaces, experiment config
- fuzzy/
  - adaptive fuzzy inference model with tunable memberships and rule weights
- ga/
  - evolutionary optimizer for fuzzy parameter learning
- simulation/
  - stochastic environment with constraints, faults, and uncertainty
- strategies/
  - FCFS, LOOK, greedy, fuzzy-only, and hybrid adaptive policy modules
- evaluation/
  - controlled benchmark orchestration and metric aggregation
- visualization/
  - convergence plots, comparative charts, and scenario heatmaps

## Design Principles Applied

1. High cohesion:
- Each package owns one concern and one evolutionary axis.

2. Low coupling:
- Dispatch logic depends on interfaces and data contracts, not concrete simulation internals.

3. Reproducibility:
- Deterministic seeds + JSON config + saved results artifacts.

4. Explainability:
- Every fuzzy-based assignment emits memberships, rule activations, and defuzzified score.
