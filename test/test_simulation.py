import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import (
    FLOOR_TRAVEL_TIME,
    DOOR_OPEN_TIME,
    DOOR_CLOSE_TIME,
    SIM_TICK_SIZE,
    DIR_UP,
    DIR_IDLE,
    STATE_IDLE,
    STATE_MOVING_UP,
    STATE_DOOR_OPEN,
)
from elevator import Elevator
from request import RequestQueue
from simulation import SimulationClock, predict_position, SimulationEngine


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run():
    # 7a
    c = SimulationClock()
    check(c.current_time == 0.0, "clock time 0")
    check(c.events == [], "clock events empty")
    check(c.event_log == [], "clock log empty")

    # 7b
    c.schedule_event(5.0, "X", {"a": 1})
    c.advance_to(4.9)
    check(c.get_due_events() == [], "no due at 4.9")
    c.advance_to(5.0)
    due = c.get_due_events()
    check(len(due) == 1 and due[0][1] == "X", "due at 5.0")
    check(len(c.event_log) == 1, "event logged")
    check(c.events == [], "events consumed")

    # 7c
    c = SimulationClock()
    c.schedule_event(10, "A")
    c.schedule_event(3, "B")
    c.schedule_event(7, "C")
    check([e[0] for e in c.events] == [3, 7, 10], "events sorted")

    # 7d
    e = Elevator(0, 20, 5)
    e.state = STATE_IDLE
    e.direction = DIR_IDLE
    p = predict_position(e, future_time=999, current_time=0)
    check(abs(p[0] - 5.0) < 1e-9 and p[2] == STATE_IDLE, f"stationary predict {p}")

    # 7e
    e = Elevator(0, 20, 0)
    e.state = STATE_MOVING_UP
    e.direction = DIR_UP
    e.stop_queue = [10]
    p = predict_position(e, future_time=15, current_time=0)
    check(4.5 <= p[0] <= 5.5, f"moving predict floor {p[0]}")
    check(p[2] == STATE_MOVING_UP, f"moving state {p[2]}")

    # 7f
    e = Elevator(0, 20, 0)
    e.state = STATE_MOVING_UP
    e.direction = DIR_UP
    e.stop_queue = [2]
    p1 = predict_position(e, future_time=(6 + 1), current_time=0)
    check(p1[2] == STATE_DOOR_OPEN, f"door open phase expected got {p1[2]}")
    p2 = predict_position(e, future_time=(6 + DOOR_OPEN_TIME + DOOR_CLOSE_TIME + 1), current_time=0)
    check(p2[2] == STATE_IDLE, f"idle after door cycle expected got {p2[2]}")

    # 7g
    elevators = [Elevator(0, 10, 0), Elevator(1, 10, 0)]
    rq = RequestQueue(10)
    engine = SimulationEngine(elevators, rq, 10)
    elevators[0].add_stop(3)
    for _ in range(100):
        events = engine.step()
        check(isinstance(events, list), "step returns list")

    # 7h
    elevators = [Elevator(0, 10, 0)]
    rq = RequestQueue(10)
    engine = SimulationEngine(elevators, rq, 10)
    req, _ = rq.create_request(0, DIR_UP, timestamp=0.0, destination_floor=3)
    rq.assign_request(req, 0, 90.0)
    elevators[0].add_stop(0)
    engine.run_until(target_time=60)
    check(req in rq.completed, "request completed")
    check(req.picked_up is True, "request picked up")
    check(req.served is True, "request served")
    check(req.wait_time is not None and req.wait_time >= 0, "wait time valid")

    # 7i
    engine = SimulationEngine([Elevator(0, 10, 0)], RequestQueue(10), 10)
    engine.run_until(100.0)
    check(engine.get_current_time() <= 100.0 + SIM_TICK_SIZE, "run_until bound")

    # 7j
    engine = SimulationEngine([Elevator(0, 10, 0), Elevator(1, 10, 2), Elevator(2, 10, 5)], RequestQueue(10), 10)
    preds = engine.predict_all_positions(future_time=30)
    check(len(preds) == 3, "pred len 3")
    for item in preds:
        check(isinstance(item, tuple) and len(item) == 3, "pred tuple shape")
        check(isinstance(item[0], float) and isinstance(item[1], str) and isinstance(item[2], str), "pred element types")

    print(f"BLOCK 7 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
