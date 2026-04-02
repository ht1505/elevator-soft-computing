from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from research.core.config import DynamicTrafficConfig


@dataclass
class TrafficObservation:
    floor: int
    direction: str


class DynamicTrafficAnalyzer:
    """Online traffic-mode detector from recent request stream."""

    def __init__(self, config: DynamicTrafficConfig | None = None):
        self.config = config or DynamicTrafficConfig()
        self.window = deque(maxlen=self.config.window_size)
        self.current_mode = "mixed"

    def record(self, floor: int, direction: str) -> None:
        self.window.append(TrafficObservation(floor=floor, direction=direction))
        self.current_mode = self._infer_mode()

    def _infer_mode(self) -> str:
        total = len(self.window)
        if total < self.config.min_samples_for_mode_detection:
            return "mixed"

        up = sum(1 for item in self.window if item.direction == "UP")
        down = total - up
        up_ratio = up / total
        down_ratio = down / total

        floors = [item.floor for item in self.window]
        if not floors:
            return "mixed"

        floor_span = max(floors) - min(floors)
        diversity_ratio = len(set(floors)) / max(1, total)

        if up_ratio >= self.config.peak_ratio_threshold:
            return "peak_up"
        if down_ratio >= self.config.peak_ratio_threshold:
            return "peak_down"
        if diversity_ratio >= self.config.inter_floor_diversity_threshold and floor_span >= self.config.inter_floor_span_threshold:
            return "inter_floor"
        return "mixed"
