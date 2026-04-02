import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import math
import random

from config import DIR_UP, DIR_DOWN, DIR_IDLE, STATE_IDLE, STATE_DOOR_OPEN, STATE_MOVING_DOWN
from elevator import Elevator, Passenger
from request import RequestQueue, Request
from traffic import TrafficAnalyzer, DemandForecaster
from logger import Logger
from ga import optimize_route, compute_total_distance
from simulation import SimulationEngine, SimulationClock
from fuzzy import compute_fuzzy_score
from main import process_request


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def build(num_elevators, num_floors):
    elevators = [Elevator(i, num_floors, 0) for i in range(num_elevators)]
    rq = RequestQueue(num_floors)
    ta = TrafficAnalyzer()
    lg = Logger()
    fc = DemandForecaster(ta)
    se = SimulationEngine(elevators, rq, num_floors)
    return elevators, rq, ta, lg, fc, se


def pipe(req, elevators, rq, ta, lg, fc, se, floors):
    process_request(req, elevators, rq, ta, lg, None, floors, fc, se)


def run():
    random.seed(7)

    # 11a
    elevators, rq, ta, lg, fc, se = build(1, 5)
    req, _ = rq.create_request(2, DIR_UP, 0.0, destination_floor=4)
    pipe(req, elevators, rq, ta, lg, fc, se, 5)
    se.run_until(120)
    check(req in rq.completed, "single elevator request completes")

    # 11b
    elevators, rq, ta, lg, fc, se = build(1, 10)
    elevators[0].current_floor = 5.0
    elevators[0].state = STATE_IDLE
    elevators[0].direction = DIR_IDLE
    req, _ = rq.create_request(5, DIR_UP, 0.0, destination_floor=8)
    pipe(req, elevators, rq, ta, lg, fc, se, 10)
    se.step()
    check(elevators[0].state == STATE_DOOR_OPEN, f"instant serve should open door within 1 tick, got {elevators[0].state}")

    # 11c
    elevators, rq, ta, lg, fc, se = build(2, 20)
    elevators[0].current_floor = 1.0
    elevators[0].state = STATE_MOVING_DOWN
    elevators[0].direction = DIR_DOWN
    elevators[1].current_floor = 18.0
    elevators[1].state = "MOVING_UP"
    elevators[1].direction = DIR_UP
    req, _ = rq.create_request(10, DIR_UP, 0.0, destination_floor=15)
    pipe(req, elevators, rq, ta, lg, fc, se, 20)
    check(req.assigned_elevator is not None, "assigned even when moving away")
    assigned = next(e for e in elevators if e.id == req.assigned_elevator)
    check(10 in assigned.stop_queue, "chosen queue includes pickup floor")

    # 11d
    e = Elevator(0, 30, 0)
    stops = [2, 18, 5, 20, 1, 9, 15, 6, 12, 3, 14, 8]
    e.stop_queue = stops[:]
    route, _ = optimize_route(e, verbose=False)
    check(sorted(route) == sorted(stops), "route is valid permutation for long queue")
    check(compute_total_distance(route, 0) <= compute_total_distance(stops, 0), "optimized <= fcfs long queue")

    # 11e
    c = SimulationClock()
    prev = c.current_time
    for _ in range(100):
        c.advance()
        check(c.current_time >= prev, "clock non-decreasing")
        prev = c.current_time
    c.advance_to(80.0)
    c.advance_to(50.0)
    check(c.current_time == 80.0, "advance_to does not regress")

    # 11f
    RequestQueue.reset_id_counter()
    q1 = RequestQueue(10)
    ids = []
    for floor in [1, 2, 3, 4, 5]:
        r, _ = q1.create_request(floor, DIR_UP, 0.0)
        ids.append(r.request_id)
    q2 = RequestQueue(10)
    for i in range(3):
        r, _ = q2.create_request(i + 6, DIR_DOWN, 0.0)
        ids.append(r.request_id)
    check(len(set(ids)) == 8, "request IDs unique across queues")

    # 11g
    rng = random.Random(7)
    for _ in range(500):
        e = Elevator(0, 20, rng.randint(0, 20))
        e.current_floor = float(rng.randint(0, 20))
        e.direction = rng.choice([DIR_UP, DIR_DOWN, DIR_IDLE])
        e.state = rng.choice([STATE_IDLE, "MOVING_UP", "MOVING_DOWN"])
        e.current_load = rng.randint(0, 8)
        e.stop_queue = [rng.randint(0, 20) for _ in range(rng.randint(0, 5))]
        rf = rng.randint(0, 20)
        rd = rng.choice([DIR_UP, DIR_DOWN])
        score, _reason, _rules = compute_fuzzy_score(e, rf, rd)
        check(math.isfinite(score), f"fuzzy finite {score}")
        check(0 <= score <= 100, f"fuzzy in range {score}")

    # 11h
    e = Elevator(0, 20, 0)
    e.stop_queue = [5, 5, 5]
    route, _ = optimize_route(e, verbose=False)
    check(isinstance(route, list) and len(route) == 3, f"identical stops route len 3 got {route}")

    # 11i
    e = Elevator(0, 20, 3)
    e.direction = DIR_UP
    e.add_stop(10)
    e._sort_stops()
    check(e.stop_queue == [10], "single stop LOOK sort")

    # 11j
    p = Passenger(2, 8, 0.0)
    check(isinstance(repr(p), str), "Passenger repr str")
    check(isinstance(repr(Elevator(0, 10)), str), "Elevator repr str")
    check(isinstance(repr(Request(5, DIR_UP)), str), "Request repr str")

    print(f"BLOCK 11 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
