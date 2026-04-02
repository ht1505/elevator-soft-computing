from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PassengerGroupRequest:
    request_id: int
    timestamp: float
    floor: int
    direction: str
    passenger_count: int
    destination_floor: int
    spike_tag: bool = False


@dataclass
class ElevatorState:
    elevator_id: int
    current_floor: float
    direction: str
    capacity: int
    current_load: int = 0
    stop_queue: List[int] = field(default_factory=list)
    energy_consumed: float = 0.0
    failed_until: float = 0.0

    @property
    def available_capacity(self) -> int:
        return max(0, self.capacity - self.current_load)

    @property
    def is_failed(self) -> bool:
        return self.failed_until > 0


@dataclass
class RuleActivation:
    rule_name: str
    firing_strength: float
    consequent_label: str
    weighted_output: float


@dataclass
class DecisionExplanation:
    elevator_id: int
    score: float
    memberships: Dict[str, Dict[str, float]]
    rule_activations: List[RuleActivation]
    traffic_mode: str


@dataclass
class DispatchDecision:
    request_id: int
    selected_elevator: int
    score: float
    explanation: DecisionExplanation


@dataclass
class SimulationMetrics:
    avg_wait: float
    p95_wait: float
    throughput_per_min: float
    net_energy: float
    fairness_variance: float
    overload_violations: int
    served: int
    dropped: int


@dataclass
class BenchmarkRow:
    strategy: str
    scenario: str
    metrics: SimulationMetrics


@dataclass
class FitnessTerms:
    avg_wait: float
    energy: float
    variance: float
    overload_penalty: float

    def objective(self, alpha: float, beta: float, gamma: float) -> float:
        return -(self.avg_wait + alpha * self.energy + beta * self.variance + gamma * self.overload_penalty)
