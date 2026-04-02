import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import io
from contextlib import redirect_stdout

from elevator import Elevator
from logger import Logger
from request import Request
from traffic import TrafficAnalyzer
from config import DIR_UP


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run():
    # 8a
    lg = Logger()
    check(hasattr(lg, "request_logs") and isinstance(lg.request_logs, list), "logger request_logs list")
    check(len(lg.request_logs) == 0, "logger request log empty")

    # 8b
    req = Request(5, DIR_UP, 0.0, destination_floor=9)
    req.assigned_elevator = 1
    req.picked_up = True
    req.served = True
    req.wait_time = 12.0
    lg.log_request(req, score=87.3, improvement=12.5, reason="R1+R15")
    check(len(lg.request_logs) == 1, "one request log entry")
    entry = lg.request_logs[0]
    check(entry["request_id"] == req.request_id, "request id stored")
    check(abs(entry["fuzzy_score"] - 87.3) < 1e-9, "score stored")
    check(abs(entry["ga_improvement"] - 12.5) < 1e-9, "improvement stored")
    check(entry["reason"] == "R1+R15", "reason stored")

    # 8c
    lg.log_event("CAPACITY_FULL", "All elevators full", timestamp=42.0)
    check(len(lg.system_events) >= 1, "event stored")
    e = lg.system_events[-1]
    check(e["type"] == "CAPACITY_FULL" and e["message"] == "All elevators full" and e["time"] == 42.0, "event fields")

    # 8d
    elevators = [Elevator(0, 10, 0), Elevator(1, 10, 3)]
    ta = TrafficAnalyzer()
    buf = io.StringIO()
    with redirect_stdout(buf):
        lg.print_full_summary(elevators, ta)
    out = buf.getvalue()
    check(len(out.strip()) > 0, "summary output non-empty")

    print(f"BLOCK 8 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
