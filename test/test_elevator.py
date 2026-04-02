import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import math
import random

from config import (
    MAX_CAPACITY,
    FLOOR_TRAVEL_TIME,
    STATE_IDLE,
    STATE_MOVING_UP,
    STATE_MOVING_DOWN,
    STATE_DOOR_OPEN,
    STATE_DOOR_CLOSING,
    DIR_UP,
    DIR_DOWN,
    DIR_IDLE,
)
from elevator import Elevator, Passenger


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run_until_state(elev, target_state, max_ticks=2000):
    for _ in range(max_ticks):
        elev.update_tick()
        if elev.state == target_state:
            return True
    return False


def run():
    random.seed(12345)

    # 2a
    e = Elevator(elevator_id=0, num_floors=20, start_floor=0)
    check(e.current_floor == 0.0, "init floor")
    check(e.state == STATE_IDLE, "init state")
    check(e.direction == DIR_IDLE, "init direction")
    check(e.stop_queue == [], "init queue")
    check(e.current_load == 0, "init load")
    check(e.energy_consumed == 0.0, "init energy")
    check(e.passengers_served == 0, "init served")

    # 2b
    check(e.add_stop(5) is True, "add_stop first true")
    check(e.stop_queue == [5], "queue [5]")
    check(e.add_stop(5) is False, "dedupe false")
    check(e.stop_queue == [5], "queue dedupe")
    e.add_stop(3)
    e.add_stop(8)
    check(set(e.stop_queue) == {3, 5, 8}, "all stops present")

    # 2c
    e2 = Elevator(1, 20, 4)
    e2.direction = DIR_IDLE
    for f in [10, 2, 7, 1, 15]:
        e2.stop_queue.append(f)
    e2._sort_stops()
    check(e2.stop_queue == [7, 10, 15, 2, 1], f"LOOK up order got {e2.stop_queue}")

    # 2d
    e3 = Elevator(2, 20, 10)
    e3.direction = DIR_DOWN
    for f in [3, 12, 7, 15, 1]:
        e3.stop_queue.append(f)
    e3._sort_stops()
    check(e3.stop_queue == [7, 3, 1, 12, 15], f"LOOK down order got {e3.stop_queue}")

    # 2e
    e4 = Elevator(3, 20, 0)
    for i in range(MAX_CAPACITY):
        ok = e4.board_passenger(Passenger(0, 1 + (i % 5), 0.0))
        check(ok, "boarding under capacity should pass")
    check(e4.board_passenger(Passenger(0, 9, 0.0)) is False, "boarding over capacity fails")
    check(e4.current_load == MAX_CAPACITY, "load equals max")

    # 2f
    e5 = Elevator(4, 20, 2)
    p = Passenger(2, 8, 0.0)
    check(e5.board_passenger(p) is True, "board passenger")
    check(e5.current_load == 1, "load 1")
    check(8 in e5.stop_queue, "dest in queue")
    out = e5.alight_passengers(8)
    check(len(out) == 1, "one alighted")
    check(e5.current_load == 0, "load 0")
    check(e5.passengers_served == 1, "served 1")
    check(all(x.destination_floor != 8 for x in e5.passengers), "dest removed")

    # 2g
    e6 = Elevator(5, 20, 3)
    e6.state = STATE_MOVING_UP
    e6.direction = DIR_UP
    check(e6.is_passing_by_eligible(7, DIR_UP)[0] is True, "eligible up ahead")
    check(e6.is_passing_by_eligible(1, DIR_UP)[0] is False, "not eligible passed")
    check(e6.is_passing_by_eligible(7, DIR_DOWN)[0] is False, "not eligible wrong dir")
    e6.state = STATE_IDLE
    e6.direction = DIR_IDLE
    check(e6.is_passing_by_eligible(19, DIR_DOWN)[0] is True, "idle eligible any")

    # 2h
    e7 = Elevator(6, 20, 0)
    e7.add_stop(2)
    seen = set()
    for _ in range(2000):
        e7.update_tick()
        seen.add(e7.state)
        if e7.state == STATE_DOOR_OPEN:
            break
    check(STATE_MOVING_UP in seen or "ACCEL_UP" in seen, "visited moving/accel up")
    check(e7.state == STATE_DOOR_OPEN, f"reached door open got {e7.state}")
    check(abs(e7.current_floor - 2.0) <= 0.1, f"at floor 2 got {e7.current_floor}")

    check(run_until_state(e7, STATE_DOOR_CLOSING), "reaches door closing")
    check(run_until_state(e7, STATE_IDLE), "returns idle")
    check(e7.total_floors_traveled > 0, "traveled positive")
    check(e7.energy_consumed > 0, "energy positive")

    # 2i
    e8 = Elevator(7, 20, 10)
    e8.add_stop(0)
    # force downward motion start
    e8.state = STATE_MOVING_DOWN
    e8.direction = DIR_DOWN
    for _ in range(4000):
        e8.update_tick()
        if e8.state == STATE_IDLE and not e8.stop_queue:
            break
    check(e8.energy_regenerated > 0, "regen positive")
    check(e8.energy_regenerated < e8.energy_consumed, "regen less than consumed")

    # 2j
    e9 = Elevator(8, 20, 0)
    e9.add_stop(5)
    eta = e9.get_eta_to_next_stop()
    check(abs(eta - (5 * FLOOR_TRAVEL_TIME)) <= 0.001, f"eta expected {5*FLOOR_TRAVEL_TIME} got {eta}")

    # 2k
    s = e9.get_status_dict()
    for k in [
        "id", "floor", "state", "direction", "stop_queue", "load", "eta_next",
        "total_traveled", "passengers_served", "energy_consumed", "energy_regenerated",
    ]:
        check(k in s, f"status key {k}")

    # 2l
    e10 = Elevator(9, 20, 0)
    e10.state = STATE_MOVING_DOWN
    e10.direction = DIR_DOWN
    for _ in range(200):
        e10.update_tick()
        check(e10.current_floor >= 0.0, f"floor went negative: {e10.current_floor}")

    print(f"BLOCK 2 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
