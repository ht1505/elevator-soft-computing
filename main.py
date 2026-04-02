"""
main.py — Smart Elevator Management System Entry Point & Menu Loop.

Orchestrates all modules:
  elevator.py  → Elevator state machine + LOOK algorithm
  request.py   → Request creation + queue management
  fuzzy.py     → Fuzzy logic scoring for elevator assignment
  ga.py        → Genetic algorithm for route optimization
  traffic.py   → Traffic pattern analyzer
  simulation.py→ Discrete-event simulation engine
  visualizer.py→ ASCII shaft rendering
  logger.py    → Request/event logging + summary output
  config.py    → All constants (no magic numbers)

═══════════════════════════════════════════════════════════════════
CLASS DIAGRAM & DATA FLOW
═══════════════════════════════════════════════════════════════════

  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   main.py    │────▶│  request.py  │────▶│  elevator.py │
  │  (Menu Loop  │     │  (Request    │     │  (State      │
  │   + Control) │     │   Queue)     │     │   Machine)   │
  └──────┬───────┘     └──────────────┘     └──────────────┘
         │                    │                     ▲
         │                    ▼                     │
         │             ┌──────────────┐             │
         │             │   fuzzy.py   │─────────────┤
         │             │  (Scoring)   │             │
         │             └──────────────┘             │
         │                    │                     │
         │                    ▼                     │
         │             ┌──────────────┐             │
         │             │    ga.py     │─────────────┘
         │             │  (Route      │
         │             │   Optimizer) │
         │             └──────────────┘
         │
         ├────────────▶┌──────────────┐
         │             │  traffic.py  │
         │             │  (Pattern    │
         │             │   Analyzer)  │
         │             └──────────────┘
         │
         ├────────────▶┌──────────────┐
         │             │simulation.py │
         │             │  (Clock +    │
         │             │   Events)    │
         │             └──────────────┘
         │
         ├────────────▶┌──────────────┐
         │             │visualizer.py │
         │             │  (ASCII      │
         │             │   Shaft)     │
         │             └──────────────┘
         │
         └────────────▶┌──────────────┐
                       │  logger.py   │
                       │  (Logs +     │
                       │   Summary)   │
                       └──────────────┘

DATA FLOW PER REQUEST:
  1. User input → validate → create Request object
  2. For each Elevator: compute fuzzy score (fuzzy.py)
     - Distance, direction compatibility, load, queue, passing-by
  3. Assign to highest-scoring elevator
    4. Global GA jointly optimizes stop sequences across all elevators (ga.py)
  5. Record in traffic analyzer (traffic.py)
  6. Log assignment details (logger.py)
  7. Display ASCII shaft (visualizer.py)
  8. If timer-based: run simulation engine (simulation.py)

═══════════════════════════════════════════════════════════════════
"""

import sys
from elevator import Elevator, Passenger
from request import Request, RequestQueue
from fuzzy import score_all_elevators
from ga import optimize_all_routes
from traffic import TrafficAnalyzer, DemandForecaster
from simulation import (
    SimulationEngine, predict_position,
    BenchmarkScenario, MetricsCollector
)
from visualizer import Visualizer
from logger import Logger
from config import (
    DIR_UP, DIR_DOWN, DIR_IDLE, MAX_CAPACITY,
    SIM_MAX_FLOORS, SIM_MAX_ELEVATORS, SIM_SCENARIO_DURATION,
    FORECAST_SLOTS, FORECAST_SLOT_SECONDS, BENCHMARK_SETTLE_SECONDS,
    STATE_IDLE, STATE_MOVING_UP, STATE_MOVING_DOWN,
    STATE_DOOR_OPEN, STATE_DOOR_CLOSING,
    FLOOR_TRAVEL_TIME, DOOR_OPEN_TIME, DOOR_CLOSE_TIME
)


# ═══════════════════════════════════════════════════════════════
#  STARTUP INPUT — Number of Elevators & Floors
# ═══════════════════════════════════════════════════════════════

def get_startup_input():
    """
    Get the number of elevators and floors from the user at startup.

    Validates:
            - Elevators: integer between 2 and SIM_MAX_ELEVATORS
            - Floors: integer between 5 and SIM_MAX_FLOORS

    Returns:
        tuple: (num_elevators, num_floors)
    """
    print("\n  ╔═══════════════════════════════════════╗")
    print("  ║   SMART ELEVATOR MANAGEMENT SYSTEM    ║")
    print("  ║         System Configuration          ║")
    print("  ╚═══════════════════════════════════════╝\n")

    # Get number of elevators
    while True:
        try:
            num_elevators = int(input(f"  Enter number of elevators (2-{SIM_MAX_ELEVATORS}): "))
            if 2 <= num_elevators <= SIM_MAX_ELEVATORS:
                break
            else:
                print(f"  [!!] Must be between 2 and {SIM_MAX_ELEVATORS}. Try again.")
        except ValueError:
            print("  ✗ Error: Please enter a valid integer.")

    # Get number of floors
    while True:
        try:
            num_floors = int(input(f"  Enter number of floors (5-{SIM_MAX_FLOORS}): "))
            if 5 <= num_floors <= SIM_MAX_FLOORS:
                break
            else:
                print(f"  [!!] Must be between 5 and {SIM_MAX_FLOORS}. Try again.")
        except ValueError:
            print("  ✗ Error: Please enter a valid integer.")

    print(f"\n  [OK] System initialized: {num_elevators} elevators, {num_floors} floors")
    return num_elevators, num_floors


# ═══════════════════════════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════════════════════════

def show_menu():
    """Display the main menu options."""
    print("\n  ╔═══════════════════════════════════════╗")
    print("  ║   SMART ELEVATOR MANAGEMENT SYSTEM    ║")
    print("  ╠═══════════════════════════════════════╣")
    print("  ║  1. Manual Request Entry              ║")
    print("  ║  2. Timer-Based Request Simulation    ║")
    print("  ║  3. Show Current Elevator Status      ║")
    print("  ║  4. Show Summary / Logs               ║")
    print("  ║  5. Exit                              ║")
    print("  ║  6. Run Benchmark Scenarios           ║")
    print("  ╚═══════════════════════════════════════╝")


def _build_benchmark_components(num_elevators, num_floors):
    elevators = [
        Elevator(elevator_id=i, num_floors=num_floors, start_floor=0)
        for i in range(num_elevators)
    ]
    request_queue = RequestQueue(num_floors)
    traffic_analyzer = TrafficAnalyzer()
    forecaster = DemandForecaster(traffic_analyzer)
    logger = Logger()
    sim_engine = SimulationEngine(elevators, request_queue, num_floors)
    return elevators, request_queue, traffic_analyzer, forecaster, logger, sim_engine


def run_benchmark_scenarios(num_elevators, num_floors):
    """Run all benchmark presets and print KPI comparisons."""
    print("\n  Running benchmark scenarios (stochastic simulation)...")

    scenario_defs = [
        ("Morning Rush", BenchmarkScenario.morning_rush(num_floors)),
        ("Evening Rush", BenchmarkScenario.evening_rush(num_floors)),
        ("Inter-Floor", BenchmarkScenario.inter_floor(num_floors)),
    ]

    results = []

    for scenario_name, requests in scenario_defs:
        print(f"\n  ── Scenario: {scenario_name} ({len(requests)} requests) ──")

        (elevators, request_queue, traffic_analyzer,
         forecaster, logger, sim_engine) = _build_benchmark_components(num_elevators, num_floors)

        def _benchmark_request_handler(req, elv=elevators, rq=request_queue,
                                       ta=traffic_analyzer, lg=logger,
                                       fc=forecaster, se=sim_engine):
            slot_idx = int(se.get_current_time() // FORECAST_SLOT_SECONDS) % FORECAST_SLOTS
            fc.record(slot_idx, floor=req.floor)
            process_request(
                req,
                elv,
                rq,
                ta,
                lg,
                visualizer=None,
                num_floors=num_floors,
                forecaster=fc,
                sim_engine=se,
                use_prediction=False,
                prediction_time=None,
            )

        sim_engine.request_callback = _benchmark_request_handler

        for ts, floor, direction, destination in requests:
            sim_engine.clock.schedule_event(
                ts,
                "NEW_REQUEST",
                {
                    "floor": floor,
                    "direction": direction,
                    "destination": destination,
                },
            )

        collector = MetricsCollector(name=scenario_name)
        end_time = SIM_SCENARIO_DURATION + BENCHMARK_SETTLE_SECONDS
        while sim_engine.get_current_time() < end_time:
            events = sim_engine.step()
            collector.ingest_events(events, request_queue, elevators)

        collector.finalize(request_queue)
        collector.report(SIM_SCENARIO_DURATION)
        results.append((scenario_name, collector.as_dict(SIM_SCENARIO_DURATION)))

    print("\n  KPI Comparison (side-by-side)")
    print("  " + "-" * 118)
    print(f"  {'Scenario':<14} | {'Avg Wait(s)':>10} | {'P95 Wait(s)':>11} | {'Avg Ride(s)':>11} | {'Throughput/min':>14} | {'Net Energy':>10} | {'Energy/Trip':>11} | {'Missed':>6}")
    print("  " + "-" * 118)
    for name, k in results:
        print(
            f"  {name:<14} | {k['avg_wait']:>10.2f} | {k['p95_wait']:>11.2f} | {k['avg_ride']:>11.2f} | "
            f"{k['throughput']:>14.2f} | {k['net_energy']:>10.2f} | {k['energy_per_trip']:>11.2f} | {k['missed']:>6}"
        )
    print("  " + "-" * 118)


# ═══════════════════════════════════════════════════════════════
#  CORE ASSIGNMENT LOGIC — Fuzzy + GA Pipeline
# ═══════════════════════════════════════════════════════════════

def process_request(request, elevators, request_queue, traffic_analyzer,
                    logger, visualizer, num_floors,
                    forecaster=None, sim_engine=None,
                    use_prediction=False, prediction_time=None):
    """
    Full pipeline to process a single hall-call request.

    Steps:
      1. Passing-by check on all elevators
      2. Position prediction (if timer-based)
      3. Fuzzy scoring on all elevators
      4. Assign to highest-scoring elevator
    5. Global GA route optimization
      6. Traffic analysis update
      7. Logging
      8. Display

    Args:
        request: Request object to process.
        elevators (list): All Elevator objects.
        request_queue: RequestQueue manager.
        traffic_analyzer: TrafficAnalyzer instance.
        logger: Logger instance.
        visualizer: Visualizer instance.
        num_floors (int): Total floors.
        sim_engine: SimulationEngine (if running timer-based).
        use_prediction (bool): Whether to use position prediction.
        prediction_time (float): Future time for prediction.
    """
    print(f"\n════════════════════════════════════════════")
    print(f"  Processing Request #{request.request_id}: Floor {request.floor} {request.direction}")
    print(f"  ════════════════════════════════════════════")

    # ─── Step 1 & 2: Passing-by check (with prediction if timer-based) ───
    print("\n  Position & Passing-By Check:")

    if use_prediction and prediction_time is not None and sim_engine is not None:
        # Predict positions at the future request time
        predictions = sim_engine.predict_all_positions(prediction_time)
        for i, (pred_floor, pred_dir, pred_state) in enumerate(predictions):
            elev = elevators[i]
            print(f"    Position Check: E{elev.id} at floor {pred_floor:.1f}, target floor {request.floor}")

            if pred_dir == DIR_DOWN and pred_floor > request.floor:
                print(f"    E{elev.id} is ABOVE floor {request.floor} and MOVING DOWN")
                print(f"    Floor {request.floor} NOT yet passed -- PASSING-BY ELIGIBLE")
            elif pred_dir == DIR_DOWN and pred_floor <= request.floor:
                print(f"    E{elev.id} is BELOW floor {request.floor} -- floor ALREADY PASSED")
                print(f"    E{elev.id} cannot serve. Checking next...")
            elif pred_dir == DIR_UP and pred_floor < request.floor:
                print(f"    E{elev.id} is BELOW floor {request.floor} and MOVING UP")
                print(f"    Floor {request.floor} NOT yet passed -- PASSING-BY ELIGIBLE")
            elif pred_dir == DIR_UP and pred_floor >= request.floor:
                print(f"    E{elev.id} is ABOVE floor {request.floor} -- floor ALREADY PASSED")
                print(f"    E{elev.id} cannot serve. Checking next...")
            elif pred_dir == DIR_IDLE:
                print(f"    E{elev.id} is IDLE at floor {pred_floor:.1f} -- can serve")
            else:
                print(f"    E{elev.id}: dir={pred_dir}, evaluating...")
    else:
        # Standard passing-by check for manual requests
        for elev in elevators:
            eligible, reason = elev.is_passing_by_eligible(request.floor, request.direction)
            print(f"    E{elev.id} at floor {elev.current_floor:.1f}: {reason}")

    # ─── Step 3: Fuzzy scoring ───────────────────────────────
    _fuzzy_best, _fuzzy_best_score, all_scores = score_all_elevators(
        elevators, request.floor, request.direction, verbose=True
    )

    # Use fuzzy score directly for assignment ranking
    scored_rows = []
    for elev, fuzzy_score, reason, fired_rules in all_scores:
        scored_rows.append((elev, fuzzy_score, reason, fired_rules))

    scored_rows.sort(key=lambda row: (
        -row[1],
        0 if row[0].state == STATE_IDLE else 1,
        row[0].id
    ))

    best_elev, best_score, reason_str, best_rules = scored_rows[0]

    print("\n  Fuzzy Assignment Scores:")
    for elev, fuzzy_score, reason, _rules in scored_rows:
        marker = "  [ASSIGNED]" if elev.id == best_elev.id else ""
        print(f"    E{elev.id}: fuzzy={fuzzy_score:.2f}{marker}")

    # ─── Edge case: all elevators at full capacity ───────────
    if best_elev.current_load >= MAX_CAPACITY:
        # Find any elevator not at full capacity
        available = [e for e in elevators if e.current_load < MAX_CAPACITY]
        if available:
            # Re-score only available elevators
            available_ids = {e.id for e in available}
            rescored = [row for row in scored_rows if row[0].id in available_ids]
            rescored.sort(key=lambda row: (-row[1], row[0].id))
            best_elev, best_score, reason_str, best_rules = rescored[0]
            print(f"\n  [!!] Primary E{best_elev.id} at capacity. Reassigning...")
        else:
            print(f"\n  [!!] All elevators at full capacity. Request queued for later.")
            logger.log_event("CAPACITY_FULL",
                             f"All elevators full for floor {request.floor} {request.direction}",
                             request.timestamp)
            return

    # ─── Step 4: Assign the request ──────────────────────────
    request_queue.assign_request(request, best_elev.id, best_score)
    best_elev.add_stop(request.floor)
    if request.destination_floor is not None:
        best_elev.add_stop(request.destination_floor)

    # Determine assignment quality
    all_moving_away = all(
        not e.is_passing_by_eligible(request.floor, request.direction)[0]
        for e in elevators
        if e.state != STATE_IDLE
    )
    if all_moving_away and best_elev.state != STATE_IDLE:
        logger.log_event("NON_OPTIMAL",
                         f"Non-optimal assignment: E{best_elev.id} for floor {request.floor}",
                         request.timestamp)
        print(f"\n  [!!] Non-optimal assignment: all elevators moving away.")

    print(f"\n  E{best_elev.id} ASSIGNED. (fuzzy={best_score:.2f}) ", end="")

    # ─── Step 5: Global GA route optimization ────────────────
    total_stops = sum(len(e.stop_queue) for e in elevators)
    if total_stops > 1:
        best_assignment, improvement = optimize_all_routes(elevators, verbose=True)
        request.ga_improvement = improvement
        print("  Global GA updated fleet routes:")
        for elev in sorted(elevators, key=lambda e: e.id):
            print(f"    E{elev.id}: {best_assignment.get(elev.id, [])}")
    else:
        improvement = 0.0
        request.ga_improvement = 0.0
        print("  Global GA skipped — fleet has <=1 total pending stop.")

    # ─── Step 6: Start elevator if idle ──────────────────────
    if best_elev.state == STATE_IDLE and best_elev.stop_queue:
        next_stop = best_elev.stop_queue[0]
        if next_stop > best_elev.current_floor:
            best_elev.state = STATE_MOVING_UP
            best_elev.direction = DIR_UP
        elif next_stop < best_elev.current_floor:
            best_elev.state = STATE_MOVING_DOWN
            best_elev.direction = DIR_DOWN
        else:
            # Already at pickup floor — open door immediately
            if next_stop in best_elev.stop_queue:
                best_elev.stop_queue.remove(next_stop)
            best_elev.current_floor = float(next_stop)
            best_elev.state = STATE_DOOR_OPEN
            best_elev.door_timer = DOOR_OPEN_TIME
            print(f"  E{best_elev.id} already at floor {next_stop} — door opening!")

    # ─── Step 7: Record traffic + log ────────────────────────
    traffic_analyzer.record_request(request.direction, request.floor)
    traffic_analyzer.print_analysis(elevators, num_floors, forecaster=forecaster)
    logger.log_request(request, best_score, improvement, reason_str)

    # ─── Step 8: Display ASCII shaft ─────────────────────────
    if visualizer is not None:
        print()
        visualizer.render_shaft(elevators, num_floors)


# ═══════════════════════════════════════════════════════════════
#  FEATURE 1: MANUAL REQUEST ENTRY
# ═══════════════════════════════════════════════════════════════

def manual_request(elevators, request_queue, traffic_analyzer,
                   logger, visualizer, num_floors, forecaster, sim_engine):
    """
    Handle manual request entry from the user.

    Prompts for floor and direction, validates, then processes.

    Args:
        All system components.
    """
    print("\n  ── Manual Request Entry ──")

    # Get floor number
    while True:
        try:
            floor = int(input(f"  Enter floor number (0-{num_floors}): "))
            if 0 <= floor <= num_floors:
                break
            else:
                print(f"  [!!] Floor must be between 0 and {num_floors}.")
        except ValueError:
            print("  [!!] Please enter a valid integer.")

    # Get direction
    while True:
        direction = input("  Enter direction (UP/DOWN): ").strip().upper()
        if direction in (DIR_UP, DIR_DOWN):
            break
        else:
            print("  [!!] Direction must be 'UP' or 'DOWN'.")

    # Create request
    timestamp = sim_engine.get_current_time()
    req, message = request_queue.create_request(floor, direction, timestamp)
    print(f"  {message}")

    if req is None:
        return  # validation failed or duplicate

    slot_idx = int(sim_engine.get_current_time() // FORECAST_SLOT_SECONDS) % FORECAST_SLOTS
    forecaster.record(slot_idx, floor=floor)

    # Get destination floor for passenger simulation
    if direction == DIR_UP:
        while True:
            try:
                dest = int(input(f"  Enter destination floor ({floor + 1}-{num_floors}): "))
                if floor < dest <= num_floors:
                    req.destination_floor = dest
                    break
                else:
                    print(f"  [!!] Destination must be above floor {floor} and at most {num_floors}.")
            except ValueError:
                print("  [!!] Please enter a valid integer.")
    else:
        while True:
            try:
                dest = int(input(f"  Enter destination floor (0-{floor - 1}): "))
                if 0 <= dest < floor:
                    req.destination_floor = dest
                    break
                else:
                    print(f"  [!!] Destination must be below floor {floor} and at least 0.")
            except ValueError:
                print("  [!!] Please enter a valid integer.")

    # Process through fuzzy + GA pipeline
    process_request(req, elevators, request_queue, traffic_analyzer,
                    logger, visualizer, num_floors, forecaster, sim_engine)


# ═══════════════════════════════════════════════════════════════
#  FEATURE 2: TIMER-BASED REQUEST SIMULATION
# ═══════════════════════════════════════════════════════════════

def timer_based_request(elevators, request_queue, traffic_analyzer,
                        logger, visualizer, num_floors, forecaster, sim_engine):
    """
    Handle timer-based request simulation.

    User specifies floor, direction, and future time.
    System predicts elevator positions and processes accordingly.

    Args:
        All system components.
    """
    print("\n  ── Timer-Based Request Simulation ──")

    # Get floor number
    while True:
        try:
            floor = int(input(f"  Enter floor number (0-{num_floors}): "))
            if 0 <= floor <= num_floors:
                break
            else:
                print(f"  [!!] Floor must be between 0 and {num_floors}.")
        except ValueError:
            print("  [!!] Please enter a valid integer.")

    # Get direction
    while True:
        direction = input("  Enter direction (UP/DOWN): ").strip().upper()
        if direction in (DIR_UP, DIR_DOWN):
            break
        else:
            print("  [!!] Direction must be 'UP' or 'DOWN'.")

    # Get time
    while True:
        try:
            req_time = float(input("  Enter time of request (seconds from start): "))
            if req_time >= 0:
                break
            else:
                print("  [!!] Time must be non-negative.")
        except ValueError:
            print("  [!!] Please enter a valid number.")

    # Get destination floor
    if direction == DIR_UP:
        while True:
            try:
                dest = int(input(f"  Enter destination floor ({floor + 1}-{num_floors}): "))
                if floor < dest <= num_floors:
                    break
                else:
                    print(f"  [!!] Destination must be above floor {floor}.")
            except ValueError:
                print("  [!!] Please enter a valid integer.")
    else:
        while True:
            try:
                dest = int(input(f"  Enter destination floor (0-{floor - 1}): "))
                if 0 <= dest < floor:
                    break
                else:
                    print(f"  [!!] Destination must be below floor {floor}.")
            except ValueError:
                print("  [!!] Please enter a valid integer.")

    # Create request
    req, message = request_queue.create_request(floor, direction, req_time, dest)
    print(f"  {message}")

    if req is None:
        return

    slot_idx = int(sim_engine.get_current_time() // FORECAST_SLOT_SECONDS) % FORECAST_SLOTS
    forecaster.record(slot_idx, floor=floor)

    # Run simulation up to the request time if needed
    current_time = sim_engine.get_current_time()
    if req_time > current_time:
        print(f"\n  Simulating from t={current_time:.1f}s to t={req_time:.1f}s...")
        sim_engine.run_until(req_time, visualizer, live_display=True, display_interval=3.0)

    # Process with position prediction
    use_pred = req_time > 0  # use prediction if request is at future time
    process_request(req, elevators, request_queue, traffic_analyzer,
                    logger, visualizer, num_floors, forecaster, sim_engine,
                    use_prediction=use_pred, prediction_time=req_time)

    # Ask if user wants to run the live simulation forward
    print(f"\n  Request processed at t={req_time:.1f}s.")
    run_sim = input("  Run live simulation forward? (y/n): ").strip().lower()
    if run_sim == 'y':
        while True:
            try:
                sim_duration = float(input("  Simulate for how many seconds? "))
                if sim_duration > 0:
                    break
                else:
                    print("  ✗ Duration must be positive.")
            except ValueError:
                print("  ✗ Please enter a valid number.")

        target = sim_engine.get_current_time() + sim_duration
        print(f"\n  Running live simulation to t={target:.1f}s...")
        sim_engine.run_until(target, visualizer, live_display=True, display_interval=3.0)

        # Show final state
        print(f"\n  ─── Simulation Complete: t={sim_engine.get_current_time():.1f}s ───")
        visualizer.render_shaft(elevators, num_floors)


# ═══════════════════════════════════════════════════════════════
#  FEATURE 3: SHOW CURRENT STATUS
# ═══════════════════════════════════════════════════════════════

def show_status(elevators, visualizer, num_floors):
    """
    Display current elevator status and ASCII shaft.

    Args:
        elevators (list): All Elevator objects.
        visualizer: Visualizer instance.
        num_floors (int): Total floors.
    """
    visualizer.render_status(elevators)
    print()
    visualizer.render_shaft(elevators, num_floors)


# ═══════════════════════════════════════════════════════════════
#  FEATURE 4: SHOW SUMMARY / LOGS
# ═══════════════════════════════════════════════════════════════

def show_summary(elevators, logger, traffic_analyzer):
    """
    Display full summary: request table, elevator stats, system stats.

    Args:
        elevators (list): All Elevator objects.
        logger: Logger instance.
        traffic_analyzer: TrafficAnalyzer instance.
    """
    logger.print_full_summary(elevators, traffic_analyzer)


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    """
    Main entry point for the Smart Elevator Management System.

    1. Get startup configuration (elevators, floors).
    2. Initialize all system components.
    3. Run the main menu loop until exit.
    """
    # ─── Startup ─────────────────────────────────────────────
    num_elevators, num_floors = get_startup_input()

    # ─── Initialize elevators (all start at floor 0, IDLE) ───
    elevators = []
    for i in range(num_elevators):
        elev = Elevator(elevator_id=i, num_floors=num_floors, start_floor=0)
        elevators.append(elev)

    # ─── Initialize system components ────────────────────────
    request_queue = RequestQueue(num_floors)
    traffic_analyzer = TrafficAnalyzer()
    forecaster = DemandForecaster(traffic_analyzer)
    logger = Logger()
    visualizer = Visualizer(num_floors, num_elevators)
    sim_engine = SimulationEngine(elevators, request_queue, num_floors)

    print(f"\n  System ready: {num_elevators} elevators at floor 0, {num_floors} floors.")
    visualizer.render_shaft(elevators, num_floors)

    # ─── Main menu loop ─────────────────────────────────────
    while True:
        show_menu()

        try:
            choice = int(input("\n  Enter your choice (1-6): "))
        except ValueError:
            print("  [!!] Invalid input. Please enter a number 1-6.")
            continue

        if choice == 1:
            # Feature 1: Manual Request Entry
            manual_request(elevators, request_queue, traffic_analyzer,
                           logger, visualizer, num_floors, forecaster, sim_engine)

        elif choice == 2:
            # Feature 2: Timer-Based Request Simulation
            timer_based_request(elevators, request_queue, traffic_analyzer,
                                logger, visualizer, num_floors, forecaster, sim_engine)

        elif choice == 3:
            # Feature 3: Show Current Elevator Status
            show_status(elevators, visualizer, num_floors)

        elif choice == 4:
            # Feature 4: Show Summary / Logs
            show_summary(elevators, logger, traffic_analyzer)

        elif choice == 5:
            # Feature 5: Exit
            print("\n  " + "="*39)
            print("  FINAL SUMMARY BEFORE EXIT")
            print("  " + "="*39)
            show_summary(elevators, logger, traffic_analyzer)
            print("\n  Thank you for using the Smart Elevator Management System.")
            print("  Goodbye.\n")
            sys.exit(0)

        elif choice == 6:
            run_benchmark_scenarios(num_elevators, num_floors)

        else:
            print("  [!!] Invalid choice. Please enter a number 1-6.")


if __name__ == "__main__":
    main()
