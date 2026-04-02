"""
greedy.py — Greedy-nearest dispatch strategy.

Assigns each request to the elevator with the lowest ETA score,
which combines travel distance and queue length but ignores direction.
Slightly smarter than FCFS but less principled than LOOK or Fuzzy.
"""

from __future__ import annotations

from typing import List

from research.core.interfaces import DispatchStrategy
from research.core.models import DispatchDecision, ElevatorState, PassengerGroupRequest
from research.strategies.common import _make_decision, eta_score


class GreedyNearestDispatch(DispatchStrategy):
    """Greedy-nearest dispatcher (direction-agnostic heuristic baseline)."""

    name = "greedy_nearest"

    def assign(
        self,
        request:      PassengerGroupRequest,
        elevators:    List[ElevatorState],
        traffic_mode: str,
        current_time: float,
    ) -> DispatchDecision:
        """
        Assign request to the elevator with the lowest ETA score.

        ETA score = |current_floor − request_floor| + queue_length × 1.5

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
            candidates = elevators

        best  = min(candidates, key=lambda e: (eta_score(e, request.floor), e.elevator_id))
        eta   = eta_score(best, request.floor)
        score = max(0.0, 100.0 - eta * 5.0)

        return _make_decision(
            request_id      = request.request_id,
            elevator_id     = best.elevator_id,
            score           = score,
            traffic_mode    = traffic_mode,
            policy_name     = "greedy_nearest",
            policy_metadata = {"eta_score": round(eta, 2)},
        )
