import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import math
import random

from config import DIR_UP, DIR_DOWN, STATE_IDLE, STATE_MOVING_UP, STATE_MOVING_DOWN
from elevator import Elevator
from fuzzy import (
    mf_distance_near,
    mf_distance_medium,
    mf_distance_far,
    mf_load_light,
    mf_load_moderate,
    mf_load_heavy,
    mf_queue_short,
    mf_queue_medium,
    mf_queue_long,
    defuzzify_centroid,
    compute_fuzzy_score,
    score_all_elevators,
)


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run():
    # 4a boundaries
    check(mf_distance_near(0) == 1.0, "dist near at 0")
    check(mf_distance_near(2) == 1.0, "dist near at 2")
    check(mf_distance_near(5) == 0.0, "dist near at 5")
    check(mf_distance_near(10) == 0.0, "dist near at 10")

    check(mf_distance_medium(2) == 0.0, "dist med 2")
    check(mf_distance_medium(5) == 1.0, "dist med 5")
    check(mf_distance_medium(9) == 0.0, "dist med 9")

    check(mf_distance_far(6) == 0.0, "dist far 6")
    check(mf_distance_far(10) == 1.0, "dist far 10")
    check(mf_distance_far(15) == 1.0, "dist far 15")

    check(mf_load_light(0.0) == 1.0 and mf_load_light(0.6) == 0.0, "load light boundaries")
    check(mf_load_moderate(0.2) == 0.0 and mf_load_moderate(0.5) == 1.0 and mf_load_moderate(0.8) == 0.0, "load moderate boundaries")
    check(mf_load_heavy(0.6) == 0.0 and mf_load_heavy(1.0) == 1.0, "load heavy boundaries")

    check(mf_queue_short(2) == 1.0 and mf_queue_short(5) == 0.0, "queue short boundaries")
    check(mf_queue_medium(2) == 0.0 and mf_queue_medium(4) == 1.0 and mf_queue_medium(7) == 0.0, "queue medium boundaries")
    check(mf_queue_long(5) == 0.0 and mf_queue_long(8) == 1.0, "queue long boundaries")

    # 4b all memberships in [0,1]
    funcs = [
        (mf_distance_near, 0.0, 20.0),
        (mf_distance_medium, 0.0, 20.0),
        (mf_distance_far, 0.0, 20.0),
        (mf_load_light, 0.0, 1.5),
        (mf_load_moderate, 0.0, 1.5),
        (mf_load_heavy, 0.0, 1.5),
        (mf_queue_short, 0.0, 20.0),
        (mf_queue_medium, 0.0, 20.0),
        (mf_queue_long, 0.0, 20.0),
    ]
    for fn, lo, hi in funcs:
        for i in range(100):
            x = lo + (hi - lo) * (i / 99)
            v = fn(x)
            check(0.0 <= v <= 1.0, f"{fn.__name__} out of range at {x}: {v}")

    # 4c/4d
    check(defuzzify_centroid([]) == 0.0, "empty centroid")
    check(abs(defuzzify_centroid([("R1", 1.0, 95)]) - 95.0) < 1e-9, "single centroid")

    # 4e
    e = Elevator(0, 20, 3)
    e.state = STATE_MOVING_UP
    e.direction = DIR_UP
    e.current_load = 0
    e.stop_queue = []
    score1, _, _ = compute_fuzzy_score(e, request_floor=5, request_direction=DIR_UP)
    check(score1 > 60, f"near same dir should be high, got {score1}")

    score2, _, _ = compute_fuzzy_score(e, request_floor=1, request_direction=DIR_UP)
    check(score2 < 30, f"already passed should be low, got {score2}")

    e.state = STATE_IDLE
    e.direction = "IDLE"
    score3, _, _ = compute_fuzzy_score(e, request_floor=9, request_direction=DIR_DOWN)
    check(score3 >= 50, f"idle should be moderate/high, got {score3}")

    # 4f
    e0 = Elevator(0, 20, 10)
    e0.state = STATE_MOVING_DOWN
    e0.direction = DIR_DOWN

    e1 = Elevator(1, 20, 4)
    e1.state = STATE_MOVING_UP
    e1.direction = DIR_UP
    e1.current_load = 0

    e2 = Elevator(2, 20, 0)
    e2.state = STATE_IDLE
    e2.direction = "IDLE"

    best_elev, best_score, all_scores = score_all_elevators([e0, e1, e2], 5, DIR_UP, verbose=False)
    extracted = [row[1] for row in all_scores]
    check(extracted == sorted(extracted, reverse=True), "scores sorted desc")
    check(best_elev.id in (1, 2), f"best should not be E0, got E{best_elev.id}")
    check(isinstance(all_scores, list) and len(all_scores) == 3, "all_scores list len 3")

    # 4g
    e4 = Elevator(4, 20, 8)
    e4.state = STATE_MOVING_UP
    e4.direction = DIR_UP
    s, _, _ = compute_fuzzy_score(e4, request_floor=3, request_direction=DIR_UP)
    check(s < 20, f"already-passed override should be very low, got {s}")

    print(f"BLOCK 4 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
