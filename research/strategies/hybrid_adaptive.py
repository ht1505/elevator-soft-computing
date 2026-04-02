from __future__ import annotations

from typing import List

from research.core.interfaces import DispatchStrategy
from research.core.models import DispatchDecision, ElevatorState, PassengerGroupRequest
from research.fuzzy.adaptive_system import AdaptiveFuzzySystem


class HybridAdaptiveDispatch(DispatchStrategy):
    name = "hybrid_adaptive"

    def __init__(self, fuzzy_model: AdaptiveFuzzySystem, adaptive_mode: bool = True):
        self.fuzzy_model = fuzzy_model
        self.adaptive_mode = adaptive_mode

    def assign(self, request: PassengerGroupRequest, elevators: List[ElevatorState], traffic_mode: str, current_time: float) -> DispatchDecision:
        if self.adaptive_mode:
            self.fuzzy_model.adapt_rule_weights(traffic_mode)
        else:
            self.fuzzy_model.reset_rule_weights()

        best_expl = None
        for elev in elevators:
            if elev.failed_until > current_time:
                continue
            expl = self.fuzzy_model.evaluate(elev, request, traffic_mode)

            if elev.available_capacity < request.passenger_count:
                expl.score -= 40.0

            if best_expl is None or expl.score > best_expl.score:
                best_expl = expl

        if best_expl is None:
            fallback = elevators[0]
            best_expl = self.fuzzy_model.evaluate(fallback, request, traffic_mode)

        return DispatchDecision(
            request_id=request.request_id,
            selected_elevator=best_expl.elevator_id,
            score=best_expl.score,
            explanation=best_expl,
        )
