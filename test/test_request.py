import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DIR_UP, DIR_DOWN
from request import Request, RequestQueue


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def run():
    # 3a
    RequestQueue.reset_id_counter()
    r1 = Request(1, DIR_UP)
    r2 = Request(2, DIR_DOWN)
    r3 = Request(3, DIR_UP)
    check((r1.request_id, r2.request_id, r3.request_id) == (1, 2, 3), "request id increments")

    # 3b
    q = RequestQueue(num_floors=20)
    check(q.validate_request(0, DIR_DOWN)[0] is False, "ground down invalid")
    check(q.validate_request(20, DIR_UP)[0] is False, "top up invalid")
    check(q.validate_request(-1, DIR_UP)[0] is False, "negative floor invalid")
    check(q.validate_request(21, DIR_UP)[0] is False, "out of range invalid")
    check(q.validate_request(5, DIR_UP)[0] is True, "normal valid")
    check(q.validate_request(5, "LEFT")[0] is False, "invalid direction")

    # 3c
    q = RequestQueue(num_floors=20)
    req_a, _ = q.create_request(5, DIR_UP, 0.0)
    req_dup, msg_dup = q.create_request(5, DIR_UP, 1.0)
    check(req_a is not None, "first request created")
    check(req_dup is None and "Duplicate" in msg_dup, "duplicate rejected")
    req_b, _ = q.create_request(5, DIR_DOWN, 2.0)
    check(req_b is not None, "different direction allowed")

    # 3d
    q = RequestQueue(num_floors=20)
    req, _ = q.create_request(7, DIR_UP, 0.0)
    check(req in q.pending, "in pending")
    q.assign_request(req, elevator_id=0, score=88.0)
    check(req in q.active and req not in q.pending, "moved to active")
    q.pickup_request(req, current_time=5.0)
    check(req.picked_up is True and req.wait_time >= 0, "picked up set")
    q.complete_request(req, current_time=15.0)
    check(req in q.completed and req not in q.active, "moved to completed")

    # 3e
    q = RequestQueue(num_floors=20)
    waits = [10.0, 20.0, 30.0]
    for i, w in enumerate(waits, start=1):
        req, _ = q.create_request(i, DIR_UP, 0.0)
        q.assign_request(req, 0, 50.0)
        q.pickup_request(req, w)
        q.complete_request(req, w + 5)
    s = q.get_stats()
    check(abs(s["avg_wait_time"] - 20.0) < 1e-9, f"avg wait {s['avg_wait_time']}")
    check(abs(s["best_wait_time"] - 10.0) < 1e-9, "best wait")
    check(abs(s["worst_wait_time"] - 30.0) < 1e-9, "worst wait")
    check(s["total_requests"] == 3, "total requests")
    check(s["completed"] == 3, "completed count")

    # 3f
    q = RequestQueue(num_floors=20)
    a, _ = q.create_request(5, DIR_UP, 0.0)
    b, _ = q.create_request(6, DIR_UP, 0.0)
    # force same floor for both while keeping dedupe valid path
    b.floor = 5
    q.assign_request(a, elevator_id=0, score=1.0)
    q.assign_request(b, elevator_id=1, score=1.0)
    picked = q.get_pickup_requests_at_floor(0, 5)
    check(len(picked) == 1 and picked[0].request_id == a.request_id, "pickup floor/elevator filtering")

    print(f"BLOCK 3 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
