import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random

from config import (
    MAX_CAPACITY,
    DIR_UP,
    DIR_DOWN,
    MODE_UP_PEAK,
    MODE_DOWN_PEAK,
)
from elevator import Elevator, Passenger
from request import RequestQueue
from traffic import TrafficAnalyzer, DemandForecaster
from logger import Logger
from ga import compute_total_distance
from simulation import SimulationEngine
from fuzzy import score_all_elevators
from main import process_request


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def build_system(num_elevators=3, num_floors=15):
    elevators = [Elevator(i, num_floors, 0) for i in range(num_elevators)]
    rq = RequestQueue(num_floors)
    ta = TrafficAnalyzer()
    lg = Logger()
    fc = DemandForecaster(ta)
    se = SimulationEngine(elevators, rq, num_floors)
    return elevators, rq, ta, lg, fc, se


def run_full_pipeline(req, elevators, rq, ta, lg, fc, se, num_floors):
    process_request(
        req,
        elevators,
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


def run():
    random.seed(42)

    # 10a
    elevators, rq, ta, lg, fc, se = build_system(3, 15)
    req, _ = rq.create_request(7, DIR_UP, 0.0, destination_floor=12)
    run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 15)
    count_with_7 = sum(1 for e in elevators if 7 in e.stop_queue)
    check(count_with_7 == 1, f"exactly one elevator has pickup floor 7, got {count_with_7}")
    assigned = next(e for e in elevators if e.id == req.assigned_elevator)
    check(7 in assigned.stop_queue and 12 in assigned.stop_queue, "assigned queue has pickup and destination")
    check(req.assigned_elevator is not None, "request assigned")
    check(req.fuzzy_score is not None and req.fuzzy_score > 0, "fuzzy score set")

    # 10b
    elevators, rq, ta, lg, fc, se = build_system(3, 15)
    rng = random.Random(42)
    created = 0
    i = 0
    while created < 10:
        floor = rng.randint(0, 15)
        if floor == 0:
            direction = DIR_UP
            dest = rng.randint(1, 15)
        elif floor == 15:
            direction = DIR_DOWN
            dest = rng.randint(0, 14)
        else:
            direction = rng.choice([DIR_UP, DIR_DOWN])
            if direction == DIR_UP:
                dest = rng.randint(floor + 1, 15)
            else:
                dest = rng.randint(0, floor - 1)
        req, _ = rq.create_request(floor, direction, float(i), destination_floor=dest)
        i += 1
        if req is None:
            continue
        run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 15)
        created += 1
    check(len(rq.pending) == 0, "none stuck pending")
    check(len(rq.active) + len(rq.completed) == len(rq.all_requests), "all requests active/completed")

    # 10c
    elevators, rq, ta, lg, fc, se = build_system(3, 15)
    for i in range(MAX_CAPACITY):
        elevators[0].board_passenger(Passenger(0, 10, 0.0))
    req, _ = rq.create_request(1, DIR_UP, 0.0, destination_floor=6)
    run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 15)
    cap_events = [ev for ev in lg.system_events if ev["type"] == "CAPACITY_FULL"]
    check(req.assigned_elevator != 0 or len(cap_events) > 0, "overflow handled without crash")

    # 10d
    rq2 = RequestQueue(15)
    r1, _ = rq2.create_request(5, DIR_UP, 0.0)
    before = len(rq2.pending)
    r2, _ = rq2.create_request(5, DIR_UP, 1.0)
    after = len(rq2.pending)
    check(r2 is None, "duplicate request rejected")
    check(before == after, "queue length unchanged on duplicate")

    # 10e
    r_bad, msg = rq2.create_request(0, DIR_DOWN, 0.0)
    check(r_bad is None and "Invalid request" in msg, "ground down rejected")

    # 10f
    elevators, rq, ta, lg, fc, se = build_system(2, 10)
    rng = random.Random(42)
    created = 0
    i = 0
    while created < 5:
        floor = rng.randint(0, 10)
        if floor == 0:
            direction = DIR_UP
            dest = rng.randint(1, 10)
        elif floor == 10:
            direction = DIR_DOWN
            dest = rng.randint(0, 9)
        else:
            direction = rng.choice([DIR_UP, DIR_DOWN])
            dest = rng.randint(floor + 1, 10) if direction == DIR_UP else rng.randint(0, floor - 1)
        req, _ = rq.create_request(floor, direction, float(i), destination_floor=dest)
        i += 1
        if req is None:
            continue
        run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 10)
        created += 1
    se.run_until(300)
    check(len(rq.completed) >= 1, "at least one completed")
    for e in elevators:
        check(e.energy_consumed > 0, "energy consumed positive")
    total_served = sum(e.passengers_served for e in elevators)
    check(total_served == len(rq.completed), f"passengers served {total_served} == completed {len(rq.completed)}")

    # 10g
    ta = TrafficAnalyzer()
    for i in range(8):
        ta.record_request(DIR_UP, floor=i)
    for i in range(2):
        ta.record_request(DIR_DOWN, floor=i)
    check(ta.get_mode() == MODE_UP_PEAK, f"expected up peak got {ta.get_mode()}")
    for i in range(8):
        ta.record_request(DIR_DOWN, floor=i)
    for i in range(2):
        ta.record_request(DIR_UP, floor=i)
    check(ta.get_mode() == MODE_DOWN_PEAK, f"expected down peak got {ta.get_mode()}")
    check(len(ta.mode_history) >= 1, "mode history transitioned")

    # 10h
    elevators, rq, ta, lg, fc, se = build_system(3, 15)
    rng = random.Random(42)
    ga_improvements = []
    created = 0
    i = 0
    while created < 10:
        floor = rng.randint(0, 15)
        if floor == 0:
            direction = DIR_UP
            dest = rng.randint(1, 15)
        elif floor == 15:
            direction = DIR_DOWN
            dest = rng.randint(0, 14)
        else:
            direction = rng.choice([DIR_UP, DIR_DOWN])
            dest = rng.randint(floor + 1, 15) if direction == DIR_UP else rng.randint(0, floor - 1)
        req, _ = rq.create_request(floor, direction, float(i), destination_floor=dest)
        i += 1
        if req is None:
            continue
        run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 15)
        ga_improvements.append(req.ga_improvement if req.ga_improvement is not None else 0.0)
        created += 1
    for val in ga_improvements:
        check(val >= 0.0, f"ga improvement non-negative got {val}")

    # 10i
    elevators, rq, ta, lg, fc, se = build_system(3, 15)
    se.run_until(30.0)
    preds = se.predict_all_positions(60.0)
    for pfloor, _pdir, _pstate in preds:
        check(0 <= pfloor <= 15, f"predicted floor in range {pfloor}")
    req, _ = rq.create_request(4, DIR_UP, 60.0, destination_floor=9)
    run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 15)
    se.run_until(60.0)
    check(req in rq.active or req in rq.completed, "request processed without crash")

    # 10j
    elevators, rq, ta, lg, fc, se = build_system(5, 20)
    rng = random.Random(42)
    requests = []
    used_pairs = set()
    while len(requests) < 25:
        floor = rng.randint(0, 20)
        if floor == 0:
            direction = DIR_UP
            dest = rng.randint(1, 20)
        elif floor == 20:
            direction = DIR_DOWN
            dest = rng.randint(0, 19)
        else:
            direction = rng.choice([DIR_UP, DIR_DOWN])
            dest = rng.randint(floor + 1, 20) if direction == DIR_UP else rng.randint(0, floor - 1)
        if (floor, direction) in used_pairs:
            continue
        used_pairs.add((floor, direction))

        req, _ = rq.create_request(floor, direction, 0.0, destination_floor=dest)
        if req is not None:
            requests.append(req)
            run_full_pipeline(req, elevators, rq, ta, lg, fc, se, 20)

    assigned_once = [r for r in requests if r.assigned_elevator is not None]
    check(len(assigned_once) == len(requests), "each request assigned exactly once")

    while se.get_current_time() < 600:
        se.step()
        for e in elevators:
            check(0 <= e.current_floor <= 20, f"floor in bounds during stress: {e.current_floor}")

    check(len(rq.completed) >= 15, f"at least 15 completed, got {len(rq.completed)}")

    print(f"BLOCK 10 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
