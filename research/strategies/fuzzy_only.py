from __future__ import annotations

from typing import List

from research.core.interfaces import DispatchStrategy
from research.core.models import DispatchDecision, ElevatorState, PassengerGroupRequest
from research.fuzzy.adaptive_system import AdaptiveFuzzySystem


class FuzzyOnlyDispatch(DispatchStrategy):
    name = "fuzzy_only"

    def __init__(self, fuzzy_model: AdaptiveFuzzySystem):
        self.fuzzy_model = fuzzy_model

    def assign(self, request: PassengerGroupRequest, elevators: List[ElevatorState], traffic_mode: str, current_time: float) -> DispatchDecision:
        best_expl = None
        for elev in elevators:
            if elev.failed_until > current_time:
                continue
            expl = self.fuzzy_model.evaluate(elev, request, traffic_mode)
            if best_expl is None or expl.score > best_expl.score:
                best_expl = expl

        if best_expl is None:
            # Fallback to first elevator in extreme failure conditions.
            first = elevators[0]
            best_expl = self.fuzzy_model.evaluate(first, request, traffic_mode)

        return DispatchDecision(
            request_id=request.request_id,
            selected_elevator=best_expl.elevator_id,
            score=best_expl.score,
            explanation=best_expl,
        )
