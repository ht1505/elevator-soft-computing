from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from research.core.models import DispatchDecision, ElevatorState, PassengerGroupRequest


class DispatchStrategy(ABC):
    name = "abstract"

    @abstractmethod
    def assign(
        self,
        request: PassengerGroupRequest,
        elevators: List[ElevatorState],
        traffic_mode: str,
        current_time: float,
    ) -> DispatchDecision:
        raise NotImplementedError


class RouteOptimizer(ABC):
    @abstractmethod
    def optimize(self, elevators: List[ElevatorState]) -> None:
        raise NotImplementedError
