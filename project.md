    # Smart Elevator Management System — Complete Project Reference

    ## Project Overview

    | Property | Value |
    |---|---|
    | **Name** | Smart Elevator Management System |
    | **Type** | Pure Python soft-computing research project |
    | **Language** | Python 3.10+ (no web framework, no external ML libraries) |
    | **Purpose** | Solve multi-elevator dispatch (which elevator?) and routing (in what order?) using Fuzzy Logic + Genetic Algorithms |
    | **Entry Points** | `user.py` → `main.py` (legacy) or `research/` (benchmark) |

    ---

    ## Architecture: Dual-Track Design

    ```
    elevator-soft-computing-main/
    │
    ├── ── Legacy Track (Production-stable, interactive CLI) ──
    │   config.py          All constants — no magic numbers anywhere else
    │   elevator.py        Elevator class — 13-state FSM + LOOK algorithm
    │   fuzzy.py           Fuzzy inference system — 9 MFs, 17 rules, centroid defuzz
    │   ga.py              Global multi-elevator Genetic Algorithm
    │   simulation.py      Discrete-event simulation engine
    │   traffic.py         Traffic pattern analyzer + demand forecaster
    │   request.py         Request lifecycle + queue management
    │   logger.py          Logging + formatted summary tables
    │   visualizer.py      ASCII shaft renderer + live display
    │   main.py            Interactive CLI menu + core pipeline orchestrator
    │   user.py            Top-level launcher (legacy or research mode)
    │
    ├── ── Research Track (Modular, benchmark-driven) ──
    │   research/
    │   ├── core/            Dataclasses, interfaces, domain models
    │   ├── fuzzy/           Adaptive fuzzy system with GA-tune support
    │   ├── ga/              Fuzzy param GA + route order GA
    │   ├── simulation/      Stochastic environment with faults + spikes
    │   ├── strategies/      5 dispatch strategies for benchmarking
    │   ├── evaluation/      Benchmark runner + explainability log
    │   ├── visualization/   matplotlib plots (convergence, wait, heatmap)
    │   ├── experiments/     JSON config files
    │   └── results/         Output artifacts (JSON, PNGs)
    │
    ├── ── Validation ──
    │   test/               12 unittest modules
    │
    └── ── Demonstrations ──
        Demo/               5 standalone progressive demo scripts
    ```

    ---

    ## Entry Points

    | Command | What Happens |
    |---|---|
    | `python user.py` | Top-level menu: choose Legacy or Research mode |
    | `python main.py` | Legacy interactive CLI directly |
    | `python -m research.run_research_demo` | Default benchmark → writes JSON + plots to `research/results/` |
    | `python test/test_<module>.py` | Run individual test module |
    | `python Demo/05_combined_system_demo.py` | Full visual combined demo |

    ---

    ## File-by-File Reference

    ---

    ### `config.py` — All System Constants (109 lines)

    Single source of truth. Every other module imports from here — no inline numbers.

    | Group | Constants |
    |---|---|
    | Elevator Mechanics | `FLOOR_TRAVEL_TIME=3s`, `DOOR_OPEN_TIME=2s`, `DOOR_CLOSE_TIME=1s`, `MAX_CAPACITY=8` |
    | GA Parameters | `GA_POPULATION=30`, `GA_GENERATIONS=75`, `GA_CROSSOVER_RATE=0.85`, `GA_MUTATION_RATE=0.12`, `GA_TOURNAMENT_SIZE=4`, `GA_ELITISM_COUNT=2` |
    | Fuzzy Output Scale | `FUZZY_VERY_LOW=10`, `FUZZY_LOW=30`, `FUZZY_MEDIUM=50`, `FUZZY_HIGH=75`, `FUZZY_VERY_HIGH=95` |
    | GA Fitness Weights | `GA_WEIGHT_DISTANCE=0.4`, `GA_WEIGHT_ENERGY=0.35`, `GA_WEIGHT_COMFORT=0.25` |
    | Energy | `ENERGY_PER_FLOOR=1.0`, `ENERGY_LOAD_FACTOR=0.1`, `ENERGY_REGEN_FACTOR=0.3` |
    | Mass & Safety | `MAX_LOAD_KG=630`, `KG_PER_PERSON=75`, `DOOR_STUCK_THRESHOLD=3` |
    | Simulation | `SIM_TICK_SIZE=0.5s`, `SIM_SCENARIO_DURATION=600s`, `SIM_MAX_FLOORS=50`, `SIM_MAX_ELEVATORS=10` |
    | Demand Forecasting | `FORECAST_ALPHA=0.25`, `FORECAST_SLOTS=12`, `FORECAST_SLOT_SECONDS=300` |

    **Direction constants:** `DIR_UP`, `DIR_DOWN`, `DIR_IDLE`  
    **Traffic modes:** `MODE_UP_PEAK`, `MODE_DOWN_PEAK`, `MODE_INTER_FLOOR`, `MODE_BALANCED`, `MODE_LIGHT`

    **13 Elevator States:**
    ```
    IDLE
    ACCEL_UP / ACCEL_DOWN         — acceleration ramp phase
    MOVING_UP / MOVING_DOWN       — constant speed phase
    DECEL_UP / DECEL_DOWN         — deceleration ramp phase
    LEVELING                      — sub-floor precision alignment
    DOOR_PRE_OPEN                 — 1-tick safety/overload check
    DOOR_OPENING                  — door animating open (0.0 → 1.0)
    DOOR_OPEN                     — dwell time for boarding/alighting
    DOOR_CLOSING                  — door animating closed (1.0 → 0.0)
    OVERLOAD / DOOR_STUCK / E_STOP / FIRE_RECALL   — fault states
    ```

    ---

    ### `elevator.py` — Elevator Class (760 lines)

    #### Class: `Passenger`
    Simple data record.

    | Attribute | Type | Description |
    |---|---|---|
    | `origin_floor` | int | Boarding floor |
    | `destination_floor` | int | Target floor |
    | `board_time` | float | Simulation time when boarded |

    #### Class: `Elevator`
    Full 13-state finite state machine with realistic physics.

    **Key attributes:**

    | Attribute | Type | Description |
    |---|---|---|
    | `id` | int | Unique elevator identifier |
    | `current_floor` | float | Fractional position (e.g. 3.5 = mid-transit) |
    | `state` | str | One of 13 states |
    | `direction` | str | UP / DOWN / IDLE |
    | `stop_queue` | list | LOOK-sorted ordered floor stops |
    | `passengers` | list | `Passenger` objects currently onboard |
    | `current_load` | int | Passenger count |
    | `door_position` | float | 0.0=closed → 1.0=fully open (animated) |
    | `reopen_count` | int | Door re-open attempts this cycle |
    | `total_floors_traveled` | float | Cumulative floor distance |
    | `energy_consumed` | float | Total energy used |
    | `energy_regenerated` | float | Energy recovered on descent |
    | `passengers_served` | int | Total drop-offs completed |

    **Key methods:**

    | Method | Description |
    |---|---|
    | `add_stop(floor)` | Adds floor to queue; re-sorts via LOOK algorithm |
    | `set_route(route)` | Replaces entire queue with GA-optimized order |
    | `_sort_stops()` | LOOK: serve stops ahead-of-current first, then reverse sweep |
    | `is_passing_by_eligible(floor, dir)` | Returns `(eligible, reason)` — can elevator pick up en-route? |
    | `can_board()` | Returns True if `current_load < MAX_CAPACITY` |
    | `board_passenger(passenger)` | Adds passenger; adds their destination to stop queue |
    | `alight_passengers(floor)` | Removes all passengers destined for this floor; increments `passengers_served` |
    | `update_tick(tick_size)` | One simulation tick of the state machine — returns events list |
    | `emergency_stop()` | Clears queue, sets `E_STOP` state |
    | `fire_recall(lobby)` | Sends elevator to lobby floor |
    | `get_eta_to_next_stop()` | ETA in seconds to next queued stop |
    | `get_status_dict()` | Dict snapshot of full elevator status |
    | `_apply_energy_cost(dist, regen)` | Energy model: load-weighted cost + regenerative descent |

    **State machine tick flow:**
    ```
    update_tick() dispatches to:
    ├── E_STOP / FIRE_RECALL / OVERLOAD / DOOR_STUCK  → fault handlers
    ├── ACCEL_UP / ACCEL_DOWN   → linear speed ramp 0→max; → MOVING_* when done
    ├── MOVING_UP / MOVING_DOWN → constant speed; → DECEL_* when 1 floor from target
    ├── DECEL_UP / DECEL_DOWN   → linear speed ramp max→0; → LEVELING when done
    ├── LEVELING                → snap to exact floor within tolerance; → DOOR_PRE_OPEN
    ├── DOOR_PRE_OPEN           → check overload; → DOOR_OPENING or OVERLOAD
    ├── DOOR_OPENING            → animate door_position 0→1; → DOOR_OPEN
    ├── DOOR_OPEN               → dwell countdown; → DOOR_CLOSING
    ├── DOOR_CLOSING            → animate 1→0; 5% obstruction chance → reopen
    │                              reopen_count >= 3 → DOOR_STUCK
    └── IDLE                    → check stop_queue; → ACCEL_UP/DOWN if stops remain
    ```

    ---

    ### `fuzzy.py` — Fuzzy Logic Engine (555 lines)

    Complete Mamdani fuzzy inference system from scratch — zero external libraries.

    #### Membership Functions (9 total)

    **Distance (floors):**
    - `mf_distance_near(x)`: 1.0 if x≤2; linear decline to 0 at x=5
    - `mf_distance_medium(x)`: rises 2→5, falls 5→9; peak at 5
    - `mf_distance_far(x)`: 0 if x≤6; rises to 1.0 at x=10

    **Load ratio (current_load / MAX_CAPACITY):**
    - `mf_load_light(x)`: 1.0 if x≤0.3; falls to 0 at x=0.6
    - `mf_load_moderate(x)`: rises 0.2→0.5; falls 0.5→0.8; peak at 0.5
    - `mf_load_heavy(x)`: 0 if x≤0.6; rises to 1.0 at x=1.0

    **Queue length (stop count):**
    - `mf_queue_short(x)`: 1.0 if x≤2; falls to 0 at x=5
    - `mf_queue_medium(x)`: rises 2→4; falls 4→7; peak at 4
    - `mf_queue_long(x)`: 0 if x≤5; rises to 1.0 at x=8

    #### Direction Compatibility
    `direction_compatibility(elev_dir, elev_state, req_dir)` → `(same, idle, opposite)`:
    - Same direction → `same=1.0`
    - Elevator IDLE → `idle=0.7`
    - Opposite direction → `opposite=1.0`

    #### Passing-By Factor
    `passing_by_factor(elevator, floor, dir)` → `(eligible_degree, not_eligible_degree)`:
    - Fully eligible same direction → `(1.0, 0.0)`
    - IDLE → `(0.5, 0.0)` (neutral)
    - Not eligible → `(0.1, 1.0)` (penalized)

    #### 17-Rule Rule Base (Mamdani AND = min)

    | Rule | Antecedents | Consequent |
    |---|---|---|
    | R1 | Near + Same + Light | VERY_HIGH (95) |
    | R2 | Near + Same + Moderate | HIGH (75) |
    | R3 | Near + Same + Heavy | MEDIUM (50) |
    | R4 | Near + Idle | HIGH (75) |
    | R5 | Near + Opposite | LOW (30) |
    | R6 | Medium + Same + Light | HIGH (75) |
    | R7 | Medium + Same + Heavy | MEDIUM (50) |
    | R8 | Medium + Idle | MEDIUM (50) |
    | R9 | Medium + Opposite | VERY_LOW (10) |
    | R10 | Far + Same + ShortQueue | MEDIUM (50) |
    | R11 | Far + Same + LongQueue | LOW (30) |
    | R12 | Far + Idle | LOW (30) |
    | R13 | Far + Opposite | VERY_LOW (10) |
    | R14 | Heavy Load | VERY_LOW (10) |
    | R15 | Near + Light + ShortQueue | VERY_HIGH (95) |
    | R16 | PassingBy + Same | VERY_HIGH (95) |
    | R17 | NotPassing + Opposite | VERY_LOW (10) |

    #### Defuzzification
    Centroid: `score = Σ(strength × output_value) / Σ(strength)`

    #### Critical Override
    If elevator is moving in same direction as request but has **already passed** the request floor → immediately return `FUZZY_VERY_LOW` without evaluating rules. Prevents inflated scores from distance rules.

    #### Main Functions
    - `compute_fuzzy_score(elevator, floor, dir)` → `(score, reason, fired_rules)`
    - `score_all_elevators(elevators, floor, dir)` → `(best_elevator, best_score, all_scores_list)`  
    Sorting: highest score → prefer IDLE → lower ID tiebreak

    ---

    ### `ga.py` — Genetic Algorithm Engine (480 lines)

    Global multi-elevator route optimizer. One GA run covers all elevators jointly.

    #### Chromosome Encoding
    Flat list of `(elevator_id, floor)` tuples across all elevators:
    ```
    [(0, 5), (0, 8), (1, 2), (1, 9), (2, 3)]  ← E0 stops at 5,8 ; E1 at 2,9 ; E2 at 3
    ```

    #### Fitness Functions

    **`fitness(chromosome, start_floor, dir)`** — Legacy single-route:
    - Penalty = `total_distance + reversals × GA_ACCEL_PENALTY`
    - Returns negative (lower = better)

    **`multi_fitness(assignment, elevators)`** — Joint 3-objective:
    - `-(0.4 × distance + 0.35 × energy + 0.25 × comfort)`
    - Energy model: up = `ENERGY_PER_FLOOR × (1 + ENERGY_LOAD_FACTOR × load)` per floor; down = `-ENERGY_REGEN_FACTOR × GA_REGEN_FACTOR_DESCENT`; reversals add `GA_ACCEL_PENALTY`
    - Comfort = sum of passenger loads at direction reversals

    #### GA Operators

    | Operator | Details |
    |---|---|
    | Initial population | FCFS seed + (pop-1) shuffled variants per elevator |
    | Selection | Tournament (k=4) |
    | Crossover | OX1 on flat tuple chromosome; `global_crossover()` adds repair step |
    | Mutation | `swap_mutation()` — constrained to same-elevator genes only |
    | Repair | `_repair()` restores exact gene multiset post-crossover |
    | Elitism | Top 2 chromosomes carried forward unchanged |

    #### Main Functions
    - `optimize_all_routes(elevators)` → `(best_assignment_dict, improvement_pct)` — runs full GA, applies routes to elevator objects
    - `optimize_route(elevator)` — Legacy wrapper for single elevator
    - `encode_chromosome(elevators)` / `decode_chromosome(chrom, n)` — chromosome encoding/decoding
    - `compute_total_distance(chromosome, start)` — reporting utility

    ---

    ### `simulation.py` — Discrete-Event Simulation Engine (563 lines)

    #### `generate_poisson_requests(lam, duration, num_floors, seed)`
    - Inter-arrival via `expovariate(lam/60)` 
    - Returns list of `(timestamp, floor, direction, destination)`

    #### `BenchmarkScenario`
    Static factory for 3 canonical scenarios:

    | Scenario | Pattern | Seed |
    |---|---|---|
    | `morning_rush()` | 80% UP from low floors; peak lambda | 101 |
    | `evening_rush()` | 80% DOWN from high floors; peak lambda | 202 |
    | `inter_floor()` | Random balanced Poisson | 303 |

    #### `MetricsCollector`
    Tracks KPIs from simulation events:
    - `wait_times`, `ride_times`, `total_energy_consumed`, `total_energy_regenerated`
    - `passengers_served`, `passengers_missed`
    - Reports: avg_wait, p95_wait, avg_ride, throughput/min, net_energy, energy/trip

    #### `SimulationClock`
    - `schedule_event(time, type, data)` — sorted insertion
    - `get_due_events()` — returns all events ≤ current_time
    - `advance()` — increments `current_time` by `tick_size`

    #### `predict_position(elevator, future_time, current_time)`
    Forward-simulates elevator trajectory to predict floor, direction, and state at a future timestamp. Accounts for door times, movement speed, and stop sequence.

    #### `SimulationEngine`
    Full simulation driver:

    | Method | Description |
    |---|---|
    | `step()` | One tick: update all elevators → process due events → board passengers at pickup floors → alight passengers at destinations |
    | `run_until(target)` | Loop steps; optional live ASCII display at configurable intervals |
    | `predict_all_positions(future_time)` | Position predictions for all elevators |

    **Key behavior in `step()`:**
    - On `FLOOR_ARRIVAL` event: alight any passengers destined here; board any waiting assigned passengers; add their destination to elevator stop queue

    ---

    ### `traffic.py` — Traffic Analysis (275 lines)

    #### `TrafficAnalyzer`
    Sliding window analysis of recent requests.

    **Mode detection (updates on every new request):**

    | Mode | Condition |
    |---|---|
    | `LIGHT` | Fewer than 3 requests in window |
    | `UP_PEAK` | >65% requests going UP |
    | `DOWN_PEAK` | >65% requests going DOWN |
    | `INTER_FLOOR` | Mixed directions + ≥60% unique floors |
    | `BALANCED` | Roughly equal UP/DOWN, few unique floors |

    **Idle repositioning recommendations by mode:**
    - UP_PEAK → all elevators to floor 0 (lobby)
    - DOWN_PEAK → distribute near top floor
    - LIGHT / BALANCED / INTER_FLOOR → distribute evenly across building

    #### `DemandForecaster`
    Exponential smoothing (`α=0.25`) over 12 five-minute slots.
    - `record(slot, floor)` — updates smoothed count for slot
    - `predict_next_slot(current_slot)` — returns predicted demand
    - `recommend_preposition(n_elevators, n_floors)` — if high demand predicted, center around historical floor centroid; else defer to TrafficAnalyzer

    ---

    ### `request.py` — Request Lifecycle (295 lines)

    #### Class: `Request`

    **Lifecycle states:** `created → assigned → picked_up → served`

    | Attribute | Description |
    |---|---|
    | `request_id` | Auto-incremented unique ID |
    | `floor` | Origin floor |
    | `direction` | UP / DOWN |
    | `timestamp` | Simulation time of creation |
    | `assigned_elevator` | Set after fuzzy assignment |
    | `destination_floor` | Passenger's target floor |
    | `wait_time` | Computed as `pickup_time - timestamp` |
    | `picked_up` | True when passenger boards elevator |
    | `served` | True when passenger reaches destination |
    | `fuzzy_score` | Winning fuzzy score at assignment |
    | `ga_improvement` | GA distance improvement percentage |

    #### Class: `RequestQueue`

    | Method | Description |
    |---|---|
    | `validate_request(floor, dir)` | Checks floor range + direction logic |
    | `is_duplicate(floor, dir)` | Prevents same floor+direction from double-queuing |
    | `create_request(floor, dir, time, dest)` | Validate → deduplicate → create → add to pending |
    | `assign_request(req, elev_id, score)` | pending → active |
    | `pickup_request(req, time)` | Records pickup; computes wait_time |
    | `complete_request(req, time)` | active → completed; records dropoff_time |
    | `get_pickup_requests_at_floor(elev_id, floor)` | Active requests waiting at specific floor for specific elevator |
    | `get_stats()` | Returns counts + best/worst/avg wait times |

    ---

    ### `logger.py` — Logging System (224 lines)

    #### Class: `Logger`

    | Method | Output |
    |---|---|
    | `log_request(req, score, ga_improve, reason)` | Stores entry with live `_request_ref` for real-time wait-time updates |
    | `log_event(type, message, time)` | System events: MODE_CHANGE, NON_OPTIMAL, CAPACITY_FULL, ERROR |
    | `print_request_table()` | Unicode box-drawing table: Req# │ Time │ Floor │ Dir │ Dest │ To │ Wait │ Pickup │ Fuzzy │ GA% |
    | `print_elevator_summary(elevators)` | Per-elevator: distance, passengers, avg wait, energy consumed/regenerated |
    | `print_system_summary(traffic_analyzer)` | GA totals, best/worst/avg wait times, traffic mode transitions |
    | `print_full_summary(elevators, analyzer)` | Calls all three above in sequence |

    ---

    ### `main.py` — CLI Orchestrator (721 lines)

    #### Startup: `get_startup_input()`
    Validates: 2–10 elevators, 5–50 floors.

    #### Main Menu (6 options)

    | Choice | Feature |
    |---|---|
    | 1 | **Manual Request Entry** — floor + direction + destination; runs full pipeline |
    | 2 | **Timer-Based Simulation** — schedules future request; runs sim to that time; uses `predict_position` |
    | 3 | **Show Current Elevator Status** — ASCII shaft + detailed status boxes |
    | 4 | **Show Summary / Logs** — full request table + elevator stats + system stats |
    | 5 | **Exit** — prints final summary then exits |
    | 6 | **Run Benchmark Scenarios** — Morning Rush, Evening Rush, Inter-Floor; KPI side-by-side table |

    #### `process_request()` — Core 8-Step Pipeline

    ```
    Step 1+2: Passing-by check (+ position prediction for timer requests)
    Step 3:   Fuzzy scoring — score_all_elevators()
    Step 4:   Assign to highest-score elevator; handle all-at-capacity edge case
    Step 5:   Global GA — optimize_all_routes() if total_stops > 1
    Step 6:   Start elevator movement if currently IDLE
    Step 7:   Traffic analyzer + forecaster update; Logger.log_request()
    Step 8:   Visualizer.render_shaft()
    ```

    ---

    ### `visualizer.py` — ASCII Renderer (371 lines)

    #### Class: `Visualizer`

    **`render_shaft(elevators, num_floors)`:**
    Draws a grid — floors top-to-bottom as rows, elevators as columns.

    | Symbol | Meaning |
    |---|---|
    | `[^ E0]` | Moving UP |
    | `[v E0]` | Moving DOWN |
    | `[= E0]` | Door OPEN |
    | `[- E0]` | Door CLOSING / LEVELING |
    | `[! E0]` | Fault state (OVERLOAD, STUCK, E_STOP, FIRE_RECALL) |
    | `[* E0]` | IDLE |
    | `(stop)` | Pending stop at that floor |

    Below grid: per-elevator status line (floor, state, direction, load, queue, ETA).

    **`render_status(elevators)`:** Detailed unicode box per elevator with all stats.

    **`__main__` demo block:** Self-contained 3-simultaneous-calls demo → Fuzzy assign → GA optimize → 18 live ticks → final metrics.

    ---

    ### `user.py` — Unified Launcher (184 lines)

    Top-level entry point offering two modes:

    **Mode 1 (Legacy):** Calls `main.main()` directly.

    **Mode 2 (Research):** Interactively collects all `ExperimentConfig` parameters:
    - Building: floors, elevators, capacity
    - Traffic: duration, lambda, spike probability
    - Objective: alpha (energy), beta (fairness), gamma (overload)
    - GA: population, generations, crossover, mutation, elitism
    - Feature toggles: adaptive_fuzzy, use_ga_for_fuzzy, use_ga_for_routes, enable_faults, stochastic_delay, spike_events
    - Scenarios: comma-separated from `peak_up, peak_down, inter_floor, mixed`

    Then calls `run_benchmarks(cfg)` → writes `research/results/benchmark_results_user.json` + matplotlib plots.

    ---

    ## Research Track — `research/` Package

    ### `research/core/config.py` — Config Dataclasses (224 lines)

    15 nested dataclasses for complete experiment parameterization:

    | Dataclass | Key Fields |
    |---|---|
    | `BuildingConfig` | `num_floors=20`, `num_elevators=4`, `capacity=10` |
    | `TrafficConfig` | `mode`, `duration_seconds=600`, `base_lambda_per_min=3.0`, `spike_probability=0.05` |
    | `ObjectiveConfig` | `alpha=0.20` (energy), `beta=0.25` (fairness), `gamma=3.0` (overload) |
    | `GAConfig` | `population=30`, `generations=50`, `crossover_rate=0.85`, `mutation_rate=0.15`, `elitism=2` |
    | `FuzzyConfig` | All 9 membership triangle `(a,b,c)` params + 5 output values |
    | `FuzzyAdaptationConfig` | Per-mode rule weight multipliers for peak_up, peak_down, inter_floor |
    | `FuzzyGAParamSpace` | `triangle_gene_count=15`, bounds, mutation sigmas |
    | `RouteGAConfig` | `generations=30`, `population=18`, `reversal_penalty=1.8` |
    | `RuntimeConfig` | `travel_time_per_floor_base=3.0`, `travel_time_noise_std=0.45`, `fault_probability_per_tick=0.0015` |
    | `DynamicTrafficConfig` | `window_size=30`, `peak_ratio_threshold=0.68` |
    | `ExperimentConfig` | Master config composing all above + scenarios list |

    JSON serialization: `load_experiment_config(path)` / `dump_results(path, payload)`.

    ---

    ### `research/core/models.py` — Domain Models (91 lines)

    | Dataclass | Purpose |
    |---|---|
    | `PassengerGroupRequest` | request_id, timestamp, floor, direction, passenger_count, destination, spike_tag |
    | `ElevatorState` | id, current_floor, direction, capacity, current_load, stop_queue, energy_consumed, failed_until |
    | `RuleActivation` | rule_name, firing_strength, consequent_label, weighted_output |
    | `DecisionExplanation` | elevator_id, score, memberships dict, rule_activations list, traffic_mode |
    | `DispatchDecision` | request_id, selected_elevator, score, explanation |
    | `SimulationMetrics` | avg_wait, p95_wait, throughput_per_min, net_energy, fairness_variance, overload_violations, served, dropped |
    | `FitnessTerms` | avg_wait, energy, variance, overload_penalty; `.objective(α, β, γ)` → scalar |

    ---

    ### `research/fuzzy/adaptive_system.py` — Adaptive Fuzzy (198 lines)

    #### `AdaptiveFuzzySystem`

    10-rule compact rule base (vs. 17 in legacy):

    | Rule | Antecedents | Consequent |
    |---|---|---|
    | R1 | distance=near, direction=same, load=light | very_high |
    | R2 | distance=near, direction=same, load=moderate | high |
    | R3 | distance=medium, direction=same, queue=short | high |
    | R4 | distance=near, direction=idle | high |
    | R5 | distance=medium, direction=idle | medium |
    | R6 | distance=far, direction=idle | low |
    | R7 | direction=opposite, passby=not_passable | very_low |
    | R8 | distance=far, direction=opposite | very_low |
    | R9 | queue=long, load=heavy | low |
    | R10 | passby=passable, direction=same | very_high |

    **Key methods:**
    - `adapt_rule_weights(traffic_mode)` — scales rule weights per mode (peak_up boosts R10, R1; suppresses R9)
    - `set_optimized_parameters(flat_vector)` — injects GA-evolved 15+ float vector into membership triangles and rule weights
    - `reset_rule_weights()` — restores canonical weights
    - `evaluate(elevator, request, mode)` → `DecisionExplanation` with full firing trace

    **Membership functions:** Triangular `tri(x, a, b, c)` for all 9 linguistic variables.

    ---

    ### `research/ga/fuzzy_genetic_optimizer.py` — Fuzzy Parameter GA (107 lines)

    #### `FuzzyParameterGA`
    Evolves flat float vector: 15 triangle params + N rule weights.

    | Operation | Detail |
    |---|---|
    | Chromosome | `[d_near_a, d_near_b, d_near_c, d_med_a, ..., rule_w1, rule_w2, ...]` |
    | Crossover | Single-point; produces 2 children |
    | Mutation | Gaussian: σ=0.6 for triangles, σ=0.08 for rule weights |
    | Selection | k=3 tournament |
    | Fitness | Simulation-in-the-loop: `FitnessTerms.objective(alpha, beta, gamma)` |

    `score_terms(waits, energy, overload_count)` → `FitnessTerms` (static helper).

    ---

    ### `research/ga/route_genetic_optimizer.py` — Route Order GA

    Lighter per-elevator GA for stop ordering. Configurable via `RouteGAConfig`. Only runs if `len(stop_queue) >= 3`.

    ---

    ### `research/simulation/environment.py` — Stochastic Environment (245 lines)

    #### `StochasticElevatorEnvironment`

    Parameterized simulation world with realistic noise:

    | Feature | Detail |
    |---|---|
    | Stochastic travel time | Gaussian noise: `N(base=3.0, σ=0.45)` clamped at min=2.2 |
    | Fault injection | Per-tick probability 0.0015; duration 12–45s uniformly |
    | Traffic spikes | `spike_probability` chance of 1.8–3.2× lambda burst |
    | Passenger groups | 1–3 per request normally; 1–4 during spike |
    | Poisson sampler | Knuth algorithm (since `random.Random` lacks `.poisson`) |

    **`run(strategy, duration, mode, ...)` → `SimulationMetrics`:**
    Each tick: inject faults → generate requests → dispatch via strategy → route GA optimize → step all elevators → optional realtime callback.

    ---

    ### `research/strategies/` — 5 Dispatch Strategies

    All implement `DispatchStrategy` interface: `assign(req, elevators, mode, time) → DispatchDecision`.

    | Strategy | Logic |
    |---|---|
    | `FCFSDispatch` | Always picks elevator with lowest ID (baseline) |
    | `LOOKDispatch` | Nearest elevator moving in same direction; else nearest idle |
    | `GreedyNearestDispatch` | Closest elevator by floor distance, ignoring direction |
    | `FuzzyOnlyDispatch` | Full fuzzy scoring without traffic-adaptive rule adjustment |
    | `HybridAdaptiveDispatch` | Fuzzy scoring + `adapt_rule_weights(mode)` per request; penalizes overloaded elevator by -40 score |

    ---

    ### `research/evaluation/benchmark.py` — Benchmark Runner (165 lines)

    #### `run_benchmarks(config)` — Full Pipeline

    ```
    1. Build AdaptiveFuzzySystem from config.fuzzy
    2. If use_ga_for_fuzzy:
        Run FuzzyParameterGA to evolve membership params
        (simulation-in-the-loop fitness for ga_tuning_duration_seconds)
        Apply best_vector to fuzzy_model
    3. Build all 5 strategies
    4. For each scenario in config.scenarios:
        For each strategy:
            Create fresh StochasticElevatorEnvironment
            Run full simulation
            Collect SimulationMetrics + explainability log
    5. Return dict: rows, summary (averaged per strategy), GA history, explanations
    ```

    `_summarize(rows)` → per-strategy averages across all scenarios.

    ---

    ### `research/visualization/plots.py` — Matplotlib Plots (87 lines)

    Gracefully skips if matplotlib not installed. Writes to `research/results/`.

    | Plot | File |
    |---|---|
    | GA convergence curve | `ga_convergence.png` |
    | Avg wait by strategy (bar) | `wait_comparison.png` |
    | Fairness variance by strategy (bar) | `fairness_comparison.png` |
    | Traffic heatmap (scenario × strategy avg wait) | `traffic_heatmap_wait.png` |

    All configurable via `VisualizationConfig` (DPI, colors, rotation).

    ---

    ## Test Suite — `test/` (12 modules)

    | File | Coverage |
    |---|---|
    | `test_config.py` | All constants exist with correct types |
    | `test_elevator.py` | State machine transitions, LOOK sort, passing-by eligibility, door animation, fault states |
    | `test_fuzzy.py` | All 9 MFs, rule firing, defuzzify, `score_all_elevators`, critical override |
    | `test_ga.py` | `fitness`, `multi_fitness`, crossover, mutation, repair, `optimize_all_routes` |
    | `test_request.py` | Validation edge cases, deduplication, full lifecycle |
    | `test_simulation.py` | Clock, Poisson generation, `SimulationEngine.step()`, `predict_position` |
    | `test_traffic.py` | Mode detection thresholds, `DemandForecaster` smoothing |
    | `test_logger.py` | Log storage, summary output (no-crash) |
    | `test_visualizer.py` | `render_shaft` and `render_status` (no-crash) |
    | `test_integration.py` | End-to-end: create requests → fuzzy assign → GA optimize → simulate ticks |
    | `test_edge_cases.py` | Top floor UP, ground floor DOWN, empty queue, full capacity, fire recall, overload |
    | `test_research_track.py` | Research imports, `AdaptiveFuzzySystem.evaluate`, all 5 strategies dispatch |

    ---

    ## Demo Scripts — `Demo/` (5 files)

    | Script | Content |
    |---|---|
    | `01_problem_explainer.py` | Text walkthrough of the dispatch problem and soft-computing approach |
    | `02_fuzzy_logic_visualizer.py` | Prints all membership function values for sample input distances |
    | `03_fuzzy_comparison.py` | Side-by-side: fuzzy dispatch vs. random assignment |
    | `04_ga_visualizer.py` | Step-by-step GA convergence for a route optimization problem |
    | `05_combined_system_demo.py` | Full demo: 3 simultaneous hall calls → Fuzzy assign → GA optimize → live tick simulation with metrics |

    ---

    ## Complete Data Flow (Per Request)

    ```
    User Input  (floor, direction, destination)
        │
        ▼
    RequestQueue.create_request()
        Validate (floor range, direction logic)
        Deduplicate (same floor+direction already active?)
        Create Request object → add to pending list
        │
        ▼
    DemandForecaster.record(slot, floor)
        Exponential smoothing on slot demand count
        │
        ▼
    fuzzy.score_all_elevators(elevators, floor, direction)
        For each elevator:
        ├── compute distance
        ├── compute direction_compatibility()
        ├── compute load_ratio
        ├── compute queue_len
        ├── compute passing_by_factor()
        ├── check critical override (already passed floor?)
        ├── evaluate_rules() → 17 fired rules
        └── defuzzify_centroid() → score
        Sort by: highest score → prefer IDLE → lower ID
        │
        ▼
    Assign to best elevator
        RequestQueue.assign_request() → pending to active
        Elevator.add_stop(pickup_floor)
        Elevator.add_stop(destination_floor)
        │
        ▼
    ga.optimize_all_routes(elevators)    [if total_stops > 1]
        Encode all elevator queues as flat [(eid, floor),...] chromosome
        Run GA: FCFS seed → tournament → OX1 crossover → swap mutation → repair
        Fitness: -(0.4×distance + 0.35×energy + 0.25×comfort)
        Apply best routes via Elevator.set_route()
        │
        ▼
    Start elevator movement (if IDLE + has stops)
        │
        ▼
    TrafficAnalyzer.record_request(direction, floor)
        Update sliding window
        Re-analyze → detect mode (UP_PEAK / DOWN_PEAK / INTER_FLOOR / BALANCED / LIGHT)
        │
        ▼
    Logger.log_request(request, score, improvement, reason)
        │
        ▼
    Visualizer.render_shaft(elevators, num_floors)
        ASCII grid with elevator positions, stop markers, status line
        │
        ▼
    [Background: SimulationEngine ticks]
        Each tick:
        Elevator.update_tick() → state machine advances
        FLOOR_ARRIVAL events:
            ├── alight_passengers(floor) → decrement load, increment passengers_served
            └── board_passenger(at floor) → increment load, add destination stop, record pickup_time
        REQUEST_SERVED when elevator arrives at destination_floor
        MetricsCollector.ingest_events() → tracks wait_times, ride_times, energy
    ```

    ---

    ## Key Design Decisions

    | Decision | Rationale |
    |---|---|
    | No magic numbers | All constants in `config.py`; easy to tune without hunting through code |
    | 13-state machine | Models real physics: acceleration ramps, leveling precision, door animations, fault modes |
    | Global joint GA | Per-car GA misses inter-elevator coordination; joint chromosome captures fleet-wide trade-offs |
    | Mamdani + centroid | Interpretable rules; centroid smoother and more intuitive than max-defuzz |
    | Passing-by hard override | Prevents already-passed elevator from scoring medium via distance rules |
    | Dual passenger lifecycle | `picked_up ≠ served`; destination added as stop at boarding, not at request time |
    | Adaptive rule weights | Traffic mode biases relevant rules without retraining; fast and interpretable |
    | Dual-track architecture | Legacy for interactive demos; research for rigorous ablation benchmarking |
    | Explainability log | Every dispatch stores full membership activations + rule firing strengths for post-analysis |
    | Stochastic research env | Models real-world travel jitter, faults, traffic spikes; more rigorous than legacy DES |

    ---

    ## Dependencies

    | Library | Used In | Required? |
    |---|---|---|
    | `random` | elevator.py, ga.py, simulation.py, research/* | ✅ stdlib |
    | `collections` | ga.py (Counter), traffic.py (deque), simulation.py | ✅ stdlib |
    | `dataclasses` | research/core/* | ✅ stdlib |
    | `math` | simulation.py, research/simulation/* | ✅ stdlib |
    | `statistics` | research/ga/*, research/simulation/* | ✅ stdlib |
    | `json`, `pathlib` | research/core/config.py | ✅ stdlib |
    | `matplotlib` | research/visualization/plots.py | ⚠️ optional (skipped gracefully) |

    **No pip dependencies required for core functionality.**
