"""
traffic.py — Traffic Pattern Analyzer for the Smart Elevator System.

Tracks recent requests in a sliding window and detects traffic modes:
  UP_PEAK, DOWN_PEAK, INTER_FLOOR, BALANCED, LIGHT

Provides behavioral recommendations for elevator positioning and
GA/fuzzy weight adjustments based on detected patterns.
"""

from collections import deque
from config import (
    TRAFFIC_WINDOW_SIZE,
    FORECAST_ALPHA, FORECAST_SLOTS,
    DIR_UP, DIR_DOWN,
    MODE_UP_PEAK, MODE_DOWN_PEAK, MODE_INTER_FLOOR,
    MODE_BALANCED, MODE_LIGHT
)


class DemandForecaster:
    """
    Exponential smoothing forecaster over fixed time slots.
    """

    def __init__(self, traffic_analyzer):
        self.traffic_analyzer = traffic_analyzer
        self.slot_counts = [0.0 for _ in range(FORECAST_SLOTS)]
        self.slot_floor_history = [[] for _ in range(FORECAST_SLOTS)]
        self.last_slot = 0

    def record(self, slot_index, floor=None):
        """Record a request in the given slot using exponential smoothing."""
        idx = int(slot_index) % FORECAST_SLOTS
        self.slot_counts[idx] = FORECAST_ALPHA * 1.0 + (1.0 - FORECAST_ALPHA) * self.slot_counts[idx]
        if floor is not None:
            self.slot_floor_history[idx].append(int(floor))
            if len(self.slot_floor_history[idx]) > 50:
                self.slot_floor_history[idx] = self.slot_floor_history[idx][-50:]
        self.last_slot = idx

    def predict_next_slot(self, current_slot):
        """Return the smoothed demand estimate for the next slot."""
        next_slot = (int(current_slot) + 1) % FORECAST_SLOTS
        return self.slot_counts[next_slot]

    def _adjacent_busy_centroid(self, slot_index, num_floors):
        prev_idx = (slot_index - 1) % FORECAST_SLOTS
        next_idx = (slot_index + 1) % FORECAST_SLOTS
        floors = self.slot_floor_history[prev_idx] + self.slot_floor_history[slot_index] + self.slot_floor_history[next_idx]
        if not floors:
            return max(0, num_floors // 2)
        centroid = sum(floors) / len(floors)
        return max(0, min(num_floors, int(round(centroid))))

    def recommend_preposition(self, num_elevators, num_floors):
        """
        Recommend idle pre-positioning floors.

        If predicted next-slot demand is high, center around historical
        adjacent-slot floor centroid; otherwise use the analyzer default.
        """
        prediction = self.predict_next_slot(self.last_slot)
        if prediction > 0.5:
            center = self._adjacent_busy_centroid(self.last_slot, num_floors)
            positions = []
            half = num_elevators // 2
            for i in range(num_elevators):
                offset = i - half
                target = max(0, min(num_floors, center + offset))
                positions.append(target)
            return positions

        return self.traffic_analyzer.get_idle_repositioning(num_floors, num_elevators)


class TrafficAnalyzer:
    """
    Analyzes elevator request traffic patterns using a sliding window.

    Maintains a window of recent requests and classifies the current
    traffic mode based on directional distribution.

    Attributes:
        window (deque): Sliding window of recent request directions.
        window_size (int): Maximum number of requests to track.
        current_mode (str): Detected traffic mode.
        mode_history (list): History of mode changes for logging.
    """

    def __init__(self, window_size=TRAFFIC_WINDOW_SIZE):
        """
        Initialize the traffic analyzer.

        Args:
            window_size (int): Number of recent requests to analyze.
        """
        self.window = deque(maxlen=window_size)  # auto-evicts oldest
        self.window_size = window_size
        self.current_mode = MODE_LIGHT           # initial mode — no data
        self.mode_history = []                    # track mode transitions

    def record_request(self, direction, floor=None):
        """
        Record a new request direction into the analysis window.

        Args:
            direction (str): UP or DOWN.
            floor (int or None): The floor of the request (for inter-floor analysis).
        """
        self.window.append({
            "direction": direction,
            "floor": floor
        })
        # Re-analyze after each new request
        self._analyze()

    def _analyze(self):
        """
        Analyze the current window and determine traffic mode.

        Mode detection rules:
          LIGHT:       fewer than 3 requests in window
          UP_PEAK:     >65% requests going UP
          DOWN_PEAK:   >65% requests going DOWN
          INTER_FLOOR: requests spread across many floors, mixed directions
          BALANCED:    roughly equal UP and DOWN
        """
        total = len(self.window)

        # Not enough data — light traffic
        if total < 3:
            self._set_mode(MODE_LIGHT)
            return

        # Count direction distribution
        up_count = sum(1 for r in self.window if r["direction"] == DIR_UP)
        down_count = sum(1 for r in self.window if r["direction"] == DIR_DOWN)

        up_ratio = up_count / total     # fraction of UP requests
        down_ratio = down_count / total # fraction of DOWN requests

        # Classify based on thresholds
        if up_ratio > 0.65:
            self._set_mode(MODE_UP_PEAK)
        elif down_ratio > 0.65:
            self._set_mode(MODE_DOWN_PEAK)
        else:
            # Check for inter-floor pattern (many different floors)
            floors = [r["floor"] for r in self.window if r["floor"] is not None]
            unique_floors = len(set(floors))

            if unique_floors >= total * 0.6:
                # Requests spread across many floors — inter-floor traffic
                self._set_mode(MODE_INTER_FLOOR)
            else:
                self._set_mode(MODE_BALANCED)

    def _set_mode(self, new_mode):
        """
        Set the traffic mode and log transitions.

        Args:
            new_mode (str): The new traffic mode.
        """
        if new_mode != self.current_mode:
            self.mode_history.append((self.current_mode, new_mode))
            self.current_mode = new_mode

    def get_mode(self):
        """
        Get the current traffic mode.

        Returns:
            str: Current traffic mode string.
        """
        return self.current_mode

    def get_idle_repositioning(self, num_floors, num_elevators):
        """
        Recommend idle elevator parking positions based on current traffic mode.

        Args:
            num_floors (int): Total number of floors.
            num_elevators (int): Total number of elevators.

        Returns:
            list: Recommended parking floors for idle elevators.
        """
        if self.current_mode == MODE_UP_PEAK:
            # Morning rush: park at lobby (floor 0) for quick UP service
            return [0] * num_elevators

        elif self.current_mode == MODE_DOWN_PEAK:
            # Evening rush: park at upper floors
            top = num_floors
            positions = []
            for i in range(num_elevators):
                # Distribute near top
                pos = max(0, top - i * 2)
                positions.append(pos)
            return positions

        elif self.current_mode == MODE_LIGHT:
            # Light traffic: distribute evenly (floor 0, mid, top)
            positions = []
            step = num_floors / max(num_elevators - 1, 1) if num_elevators > 1 else 0
            for i in range(num_elevators):
                positions.append(int(round(i * step)))
            return positions

        else:
            # BALANCED or INTER_FLOOR: distribute evenly
            positions = []
            step = num_floors / max(num_elevators - 1, 1) if num_elevators > 1 else num_floors // 2
            for i in range(num_elevators):
                positions.append(int(round(i * step)))
            return positions

    def get_analysis_summary(self):
        """
        Get a printable summary of current traffic analysis.

        Returns:
            str: Summary string with statistics and mode.
        """
        total = len(self.window)
        if total == 0:
            return "Traffic Analysis: No requests recorded yet."

        up_count = sum(1 for r in self.window if r["direction"] == DIR_UP)
        down_count = sum(1 for r in self.window if r["direction"] == DIR_DOWN)

        summary = (
            f"Traffic Analysis: {up_count}/{total} requests going UP, "
            f"{down_count}/{total} going DOWN -> Mode: {self.current_mode}"
        )
        return summary

    def print_analysis(self, elevators=None, num_floors=None, forecaster=None):
        """
        Print traffic analysis with repositioning recommendations.

        Args:
            elevators (list or None): List of elevators for repositioning.
            num_floors (int or None): Total floors.
        """
        print(f"\n  {self.get_analysis_summary()}")

        if elevators is not None and num_floors is not None:
            # Check for idle elevators to reposition
            idle_elevators = [e for e in elevators if e.direction == "IDLE"]
            if idle_elevators and self.current_mode in (MODE_UP_PEAK, MODE_DOWN_PEAK, MODE_LIGHT):
                if forecaster is not None:
                    positions = forecaster.recommend_preposition(len(idle_elevators), num_floors)
                else:
                    positions = self.get_idle_repositioning(num_floors, len(idle_elevators))
                for i, elev in enumerate(idle_elevators):
                    if i < len(positions):
                        target = positions[i]
                        print(f"  Idle E{elev.id} repositioning to floor {target}")

    def get_mode_distribution(self):
        """
        Get distribution of time spent in each traffic mode.

        Returns:
            dict: Mode transition history for logging.
        """
        return {
            "current_mode": self.current_mode,
            "transitions": list(self.mode_history),
            "total_transitions": len(self.mode_history)
        }
