import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import (
    DIR_UP,
    DIR_DOWN,
    MODE_LIGHT,
    MODE_UP_PEAK,
    MODE_DOWN_PEAK,
    MODE_BALANCED,
    MODE_INTER_FLOOR,
)
from traffic import TrafficAnalyzer


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run():
    # 6a
    ta = TrafficAnalyzer()
    check(ta.current_mode == MODE_LIGHT, "initial mode light")
    check(len(ta.window) == 0, "initial window empty")

    # 6b
    ta = TrafficAnalyzer()
    for i in range(7):
        ta.record_request(DIR_UP, floor=i)
    ta.record_request(DIR_DOWN, floor=9)
    check(ta.get_mode() == MODE_UP_PEAK, f"expected UP_PEAK got {ta.get_mode()}")

    # 6c
    ta = TrafficAnalyzer()
    for i in range(7):
        ta.record_request(DIR_DOWN, floor=i)
    ta.record_request(DIR_UP, floor=9)
    check(ta.get_mode() == MODE_DOWN_PEAK, f"expected DOWN_PEAK got {ta.get_mode()}")

    # 6d
    ta = TrafficAnalyzer()
    for _ in range(5):
        ta.record_request(DIR_UP, floor=5)
    for _ in range(5):
        ta.record_request(DIR_DOWN, floor=5)
    check(ta.get_mode() == MODE_BALANCED, f"expected BALANCED got {ta.get_mode()}")

    # 6e
    ta = TrafficAnalyzer()
    for i in range(8):
        ta.record_request(DIR_UP if i % 2 == 0 else DIR_DOWN, floor=i)
    check(ta.get_mode() == MODE_INTER_FLOOR, f"expected INTER_FLOOR got {ta.get_mode()}")

    # 6f
    ta = TrafficAnalyzer()
    check(ta.get_mode() == MODE_LIGHT, "fresh light")
    ta.record_request(DIR_UP, floor=1)
    ta.record_request(DIR_DOWN, floor=2)
    check(ta.get_mode() == MODE_LIGHT, "still light under 3 samples")

    # 6g
    ta = TrafficAnalyzer(window_size=5)
    for _ in range(5):
        ta.record_request(DIR_DOWN, floor=1)
    for _ in range(5):
        ta.record_request(DIR_UP, floor=2)
    check(ta.get_mode() == MODE_UP_PEAK, f"window eviction expected UP_PEAK got {ta.get_mode()}")

    # 6h
    ta = TrafficAnalyzer()
    ta.current_mode = MODE_LIGHT
    for mode in [MODE_LIGHT, MODE_UP_PEAK, MODE_DOWN_PEAK, MODE_BALANCED, MODE_INTER_FLOOR]:
        ta.current_mode = mode
        pos = ta.get_idle_repositioning(num_floors=20, num_elevators=3)
        check(len(pos) == 3, f"{mode} length 3")
        for p in pos:
            check(0 <= p <= 20, f"{mode} position range {p}")

    # 6i
    ta = TrafficAnalyzer()
    for i in range(5):
        ta.record_request(DIR_UP if i % 2 == 0 else DIR_DOWN, floor=i)
    summary = ta.get_analysis_summary()
    check(isinstance(summary, str) and len(summary) > 0, "summary non-empty str")
    check(ta.get_mode() in summary, "summary includes mode")

    # 6j
    ta = TrafficAnalyzer()
    for _ in range(8):
        ta.record_request(DIR_UP, floor=1)
    for _ in range(10):
        ta.record_request(DIR_DOWN, floor=1)
    check(len(ta.mode_history) >= 2, "mode history has transitions")
    valid_modes = {MODE_LIGHT, MODE_UP_PEAK, MODE_DOWN_PEAK, MODE_BALANCED, MODE_INTER_FLOOR}
    for old, new in ta.mode_history:
        check(old in valid_modes and new in valid_modes, "history tuple valid")

    print(f"BLOCK 6 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
