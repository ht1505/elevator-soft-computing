import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import io
from contextlib import redirect_stdout

from config import STATE_IDLE, STATE_MOVING_UP, STATE_DOOR_OPEN, DIR_IDLE, DIR_UP
from elevator import Elevator
from visualizer import Visualizer


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run():
    v = Visualizer(num_floors=10, num_elevators=3)
    e0 = Elevator(0, 10, 2)
    e1 = Elevator(1, 10, 5)
    e2 = Elevator(2, 10, 8)

    e0.state = STATE_IDLE
    e0.direction = DIR_IDLE
    e1.state = STATE_MOVING_UP
    e1.direction = DIR_UP
    e2.state = STATE_DOOR_OPEN
    e2.direction = DIR_IDLE

    # 9a + 9b + 9d
    buf = io.StringIO()
    with redirect_stdout(buf):
        v.render_shaft([e0, e1, e2], num_floors=10)
    out = buf.getvalue()
    check(len(out.strip()) > 0, "shaft output non-empty")
    check("E0" in out and "E1" in out and "E2" in out, "all elevator IDs in output")
    for n in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
        check(n in out, f"floor {n} appears")

    # 9c
    with redirect_stdout(io.StringIO()):
        v.render_status([e0, e1, e2])
    check(True, "render_status no exception")

    print(f"BLOCK 9 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
