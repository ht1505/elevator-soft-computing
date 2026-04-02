"""
fcfs.py — First-Come-First-Served dispatch strategy.

Baseline strategy: assigns each request to the elevator with the
fewest pending stops (ties broken by elevator ID). No fuzzy logic,
no direction awareness. Used as a lower-bound reference in benchmarks.
"""

from __future__ import annotations

from typing import List

from research.core.interfaces import DispatchStrategy
from research.core.models import DispatchDecision, ElevatorState, PassengerGroupRequest
from research.strategies.common import _make_decision


class FCFSDispatch(DispatchStrategy):
    """First-Come-First-Served dispatcher (baseline)."""

    name = "fcfs"

    def assign(
        self,
        request:      PassengerGroupRequest,
        elevators:    List[ElevatorState],
        traffic_mode: str,
        current_time: float,
    ) -> DispatchDecision:
        """
        Assign request to the elevator with the shortest queue.

        Args:
            request:      Incoming hall-call.
            elevators:    All elevator states.
            traffic_mode: Current traffic regime (unused, present for interface).
            current_time: Simulation time in seconds.

        Returns:
            DispatchDecision for the chosen elevator.
        """
        candidates = [e for e in elevators if e.failed_until <= current_time]
        if not candidates:
            candidates = elevators   # all faulted — pick least-bad option

        best  = min(candidates, key=lambda e: (len(e.stop_queue), e.elevator_id))
        score = max(0.0, 100.0 - len(best.stop_queue) * 5.0)

        return _make_decision(
            request_id      = request.request_id,
            elevator_id     = best.elevator_id,
            score           = score,
            traffic_mode    = traffic_mode,
            policy_name     = "fcfs",
            policy_metadata = {"queue_length": len(best.stop_queue)},
        )
