"""
look.py — LOOK algorithm dispatch strategy.

Assigns each request to the nearest elevator that is either moving
in the same direction or is idle. Stop queues are re-sorted using
the LOOK algorithm from research/strategies/common.py, which mirrors
the root-level elevator.py behaviour.
"""

from __future__ import annotations

from typing import List

from research.core.interfaces import DispatchStrategy
from research.core.models import DispatchDecision, ElevatorState, PassengerGroupRequest
from research.strategies.common import _make_decision, look_route


class LOOKDispatch(DispatchStrategy):
    """LOOK algorithm dispatcher (direction-aware heuristic baseline)."""

    name = "look"

    def assign(
        self,
        request:      PassengerGroupRequest,
        elevators:    List[ElevatorState],
        traffic_mode: str,
        current_time: float,
    ) -> DispatchDecision:
        """
        Assign request to the nearest eligible elevator and update its route.

        Eligibility: elevator must not be faulted. Among eligible elevators,
        the nearest by floor distance is chosen (ties broken by queue length,
        then elevator ID).

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

        best = min(
            candidates,
            key=lambda e: (abs(e.current_floor - request.floor), len(e.stop_queue), e.elevator_id),
        )

        # Re-sort stop queue using LOOK ordering
        all_stops  = best.stop_queue + [request.floor, request.destination_floor]
        best.stop_queue = look_route(int(round(best.current_floor)), all_stops,
                                     best.direction or "UP")

        dist  = abs(best.current_floor - request.floor)
        score = max(0.0, 100.0 - dist * 3.0)

        return _make_decision(
            request_id      = request.request_id,
            elevator_id     = best.elevator_id,
            score           = score,
            traffic_mode    = traffic_mode,
            policy_name     = "look",
            policy_metadata = {"distance_to_floor": round(dist, 2)},
        )
