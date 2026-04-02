"""
environment.py — Stochastic Elevator Simulation Environment (Research Track).

Provides a parameterised, discrete-time simulation world used by the
benchmark runner (evaluation/benchmark.py) to evaluate all 5 dispatch
strategies under controlled but realistic conditions.

Realistic features modelled:
    • Poisson passenger arrivals (Knuth sampler from utils.py)
    • Traffic spikes: λ × [1.8, 3.2] with configurable probability
    • Gaussian travel-time noise per floor segment
    • Random elevator faults with configurable duration
    • Passenger groups (1–3 normal, 1–4 during spike)
    • Per-tick route GA optimisation for each elevator

Cross-reference:
    utils.poisson_sample — shared Knuth Poisson sampler
    utils.percentile     — shared empirical percentile
    research/core/config.py → RuntimeConfig, RouteGAConfig, DynamicTrafficConfig
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import variance
from typing import Dict, List, Optional

from research.core.config import DynamicTrafficConfig, RouteGAConfig, RuntimeConfig
from research.core.models import (
    DispatchDecision,
    ElevatorState,
    PassengerGroupRequest,
    SimulationMetrics,
)
from research.ga.route_genetic_optimizer import RouteGeneticOptimizer
from research.simulation.traffic_analyzer import DynamicTrafficAnalyzer
from research.simulation.traffic_modes import sample_origin_destination
from utils import percentile, poisson_sample   # shared pure utilities


# ═══════════════════════════════════════════════════════════════
#  INTERNAL REQUEST STATE TRACKER
# ═══════════════════════════════════════════════════════════════

@dataclass
class SimRequestState:
    """Tracks the lifecycle of one request inside the simulation."""
    req:               PassengerGroupRequest
    assigned_elevator: int
    pickup_time:  Optional[float] = None
    dropoff_time: Optional[float] = None


# ═══════════════════════════════════════════════════════════════
#  STOCHASTIC ELEVATOR ENVIRONMENT
# ═══════════════════════════════════════════════════════════════

class StochasticElevatorEnvironment:
    """
    Discrete-time stochastic simulation of a multi-elevator building.

    Each call to run() drives the simulation forward second-by-second,
    generating passenger requests, dispatching them via the supplied
    strategy, optionally optimising routes, and stepping each elevator.

    Metrics are accumulated internally and returned as SimulationMetrics
    at the end of run().

    Args:
        num_floors:            Number of floors in the building.
        num_elevators:         Number of elevators.
        capacity:              Maximum passengers per elevator.
        seed:                  RNG seed for reproducibility.
        runtime_config:        Physics and timing parameters.
        route_ga_config:       Route optimisation GA parameters.
        dynamic_traffic_config:Traffic-mode detection parameters.
    """

    def __init__(
        self,
        num_floors:             int,
        num_elevators:          int,
        capacity:               int,
        seed:                   int = 42,
        runtime_config:         Optional[RuntimeConfig]        = None,
        route_ga_config:        Optional[RouteGAConfig]        = None,
        dynamic_traffic_config: Optional[DynamicTrafficConfig] = None,
    ) -> None:
        self.rng               = random.Random(seed)
        self.num_floors        = num_floors
        self.runtime_config    = runtime_config    or RuntimeConfig()
        self.route_ga_config   = route_ga_config   or RouteGAConfig()
        self.dynamic_traffic_config = dynamic_traffic_config or DynamicTrafficConfig()

        self.elevators: List[ElevatorState] = [
            ElevatorState(
                elevator_id   = i,
                current_floor = 0.0,
                direction     = "IDLE",
                capacity      = capacity,
            )
            for i in range(num_elevators)
        ]

        self.time:            float                      = 0.0
        self._id_counter:     int                        = 0
        self.requests:        Dict[int, SimRequestState] = {}
        self.wait_times:      List[float]                = []
        self.overload_violations: int                    = 0
        self.dropped:         int                        = 0
        self.assignment_log:  List[DispatchDecision]     = []

        self.traffic_analyzer  = DynamicTrafficAnalyzer(config=self.dynamic_traffic_config)
        self.route_optimizer   = RouteGeneticOptimizer(seed=seed + 7, config=self.route_ga_config)

    # ───────────────────────────────────────────────────────────
    #  INTERNAL HELPERS
    # ───────────────────────────────────────────────────────────

    def _sample_travel_time_per_floor(self, stochastic_delay: bool) -> float:
        """Return travel time per floor, optionally with Gaussian jitter."""
        base = self.runtime_config.travel_time_per_floor_base
        if not stochastic_delay:
            return base
        noisy = self.rng.gauss(base, self.runtime_config.travel_time_noise_std)
        return max(self.runtime_config.travel_time_per_floor_min, noisy)

    def _maybe_inject_fault(self, enable_faults: bool) -> None:
        """Randomly fault an elevator for a short duration."""
        if not enable_faults:
            return
        cfg = self.runtime_config
        for e in self.elevators:
            if e.failed_until > self.time:
                continue   # already faulted
            if self.rng.random() < cfg.fault_probability_per_tick:
                e.failed_until = self.time + self.rng.uniform(
                    cfg.fault_duration_min_seconds,
                    cfg.fault_duration_max_seconds,
                )

    def _generate_requests(
        self,
        mode:               str,
        lam_per_min:        float,
        spike_probability:  float,
        enable_spike_events: bool,
    ) -> List[PassengerGroupRequest]:
        """
        Generate zero or more Poisson-distributed passenger requests for this tick.

        Spike events temporarily multiply λ by a random factor in [1.8, 3.2].
        Uses poisson_sample() from utils (Knuth algorithm).
        """
        effective_lam = lam_per_min
        spike         = False

        if enable_spike_events and self.rng.random() < spike_probability:
            effective_lam *= self.rng.uniform(1.8, 3.2)
            spike = True

        # Convert λ/min → expected arrivals per tick (1 tick = 1 second)
        arrivals_per_tick = effective_lam / 60.0
        count = poisson_sample(arrivals_per_tick, self.rng)

        out: List[PassengerGroupRequest] = []
        for _ in range(count):
            self._id_counter += 1
            floor, direction, dest = sample_origin_destination(
                mode, self.num_floors, self.rng
            )
            max_group = (
                self.runtime_config.passenger_group_max_spike
                if spike
                else self.runtime_config.passenger_group_max_base
            )
            out.append(
                PassengerGroupRequest(
                    request_id      = self._id_counter,
                    timestamp       = self.time,
                    floor           = floor,
                    direction       = direction,
                    passenger_count = self.rng.randint(1, max_group),
                    destination_floor = dest,
                    spike_tag       = spike,
                )
            )
        return out

    def _dispatch_request(self, req: PassengerGroupRequest,
                           decision: DispatchDecision) -> None:
        """Assign a request to an elevator and register it in the request log."""
        e = self.elevators[decision.selected_elevator]

        if e.available_capacity < req.passenger_count:
            self.overload_violations += 1
            self.dropped += 1
            return

        if req.floor not in e.stop_queue:
            e.stop_queue.append(req.floor)
        if req.destination_floor not in e.stop_queue:
            e.stop_queue.append(req.destination_floor)

        self.requests[req.request_id] = SimRequestState(
            req               = req,
            assigned_elevator = e.elevator_id,
        )
        self.assignment_log.append(decision)

    def _step_elevator(self, e: ElevatorState, stochastic_delay: bool) -> None:
        """
        Advance one elevator by one simulation tick.

        Movement uses a simple position-step model:
            speed = 1 floor / travel_time_per_floor

        When the elevator reaches a stop within 0.2 floors, it snaps to
        the exact floor and processes boarding/alighting.
        """
        if e.failed_until > self.time:
            return   # elevator is faulted — do nothing this tick
        if not e.stop_queue:
            e.direction = "IDLE"
            return

        target = e.stop_queue[0]
        if abs(e.current_floor - target) < 0.2:
            e.current_floor = float(target)
            e.stop_queue.pop(0)
            self._process_floor_stop(e, target)
            return

        tpf   = self._sample_travel_time_per_floor(stochastic_delay)
        speed = 1.0 / max(tpf, 1e-6)
        step  = min(self.runtime_config.max_floor_step_per_tick, speed)

        cfg = self.runtime_config
        if target > e.current_floor:
            e.direction    = "UP"
            e.current_floor = min(target, e.current_floor + step)
            e.energy_consumed += cfg.energy_up_base + cfg.energy_up_load_factor * e.current_load
        else:
            e.direction    = "DOWN"
            e.current_floor = max(target, e.current_floor - step)
            e.energy_consumed += cfg.energy_down_base + cfg.energy_down_load_factor * e.current_load

    def _process_floor_stop(self, e: ElevatorState, floor: int) -> None:
        """Board waiting passengers and alight passengers at destination floor."""
        for rs in self.requests.values():
            if rs.assigned_elevator != e.elevator_id:
                continue
            # Pick-up
            if rs.pickup_time is None and rs.req.floor == floor:
                if e.available_capacity >= rs.req.passenger_count:
                    e.current_load += rs.req.passenger_count
                    rs.pickup_time  = self.time
                else:
                    self.overload_violations += 1
                    self.dropped += 1
            # Drop-off
            elif (rs.pickup_time is not None
                  and rs.dropoff_time is None
                  and rs.req.destination_floor == floor):
                e.current_load = max(0, e.current_load - rs.req.passenger_count)
                rs.dropoff_time = self.time
                self.wait_times.append(rs.pickup_time - rs.req.timestamp)

    def _optimize_routes(self) -> None:
        """Run route GA on every non-faulted elevator with a qualifying queue."""
        for e in self.elevators:
            if e.failed_until > self.time:
                continue
            if len(e.stop_queue) < self.route_ga_config.min_route_length_for_optimization:
                continue
            e.stop_queue = self.route_optimizer.optimize(e.current_floor, e.stop_queue)

    # ───────────────────────────────────────────────────────────
    #  PUBLIC: RUN FULL SIMULATION
    # ───────────────────────────────────────────────────────────

    def run(
        self,
        strategy,
        duration_seconds:    int,
        mode:                str,
        base_lambda_per_min: float,
        spike_probability:   float,
        enable_faults:       bool,
        stochastic_delay:    bool,
        enable_spike_events: bool,
        use_route_ga:        bool = True,
        realtime_callback    = None,
        realtime_interval:   Optional[int] = None,
    ) -> SimulationMetrics:
        """
        Simulate the building for duration_seconds, one second per tick.

        Each tick:
            1. Inject random faults (if enabled)
            2. Generate Poisson passenger requests
            3. Dispatch each request via strategy.assign()
            4. Optionally run route GA on all elevators
            5. Step all elevators forward by one tick
            6. Optional realtime callback for live visualisation

        Args:
            strategy:            Any object implementing assign(req, elevators, mode, time).
            duration_seconds:    Total simulation time in seconds.
            mode:                Traffic mode ("peak_up", "peak_down", "inter_floor", "mixed").
            base_lambda_per_min: Base Poisson arrival rate.
            spike_probability:   Probability of a traffic spike per tick.
            enable_faults:       Whether random elevator faults are active.
            stochastic_delay:    Whether Gaussian travel-time noise is active.
            enable_spike_events: Whether traffic spikes are active.
            use_route_ga:        Whether route GA optimisation runs each tick.
            realtime_callback:   Optional fn(elevators, num_floors, time) for live display.
            realtime_interval:   Seconds between realtime callback invocations.

        Returns:
            SimulationMetrics with aggregated KPIs.
        """
        self.time = 0.0
        if realtime_interval is None:
            realtime_interval = self.runtime_config.realtime_interval_seconds

        while self.time < duration_seconds:
            self._maybe_inject_fault(enable_faults)

            incoming = self._generate_requests(
                mode, base_lambda_per_min, spike_probability, enable_spike_events
            )
            for req in incoming:
                self.traffic_analyzer.record(req.floor, req.direction)
                dynamic_mode = self.traffic_analyzer.current_mode or mode
                decision     = strategy.assign(req, self.elevators, dynamic_mode, self.time)
                self._dispatch_request(req, decision)

            if use_route_ga:
                self._optimize_routes()

            for e in self.elevators:
                self._step_elevator(e, stochastic_delay)

            if (realtime_callback is not None
                    and int(self.time) % max(1, realtime_interval) == 0):
                realtime_callback(self.elevators, self.num_floors, self.time)

            self.time += self.runtime_config.simulation_step_seconds

        # ─── Aggregate metrics ──────────────────────────────────
        served      = len(self.wait_times)
        avg_wait    = sum(self.wait_times) / served if served else 0.0
        p95_wait    = percentile(self.wait_times, 95)
        throughput  = served / max(1.0, duration_seconds / 60.0)
        net_energy  = sum(e.energy_consumed for e in self.elevators)
        fairness    = variance(self.wait_times) if len(self.wait_times) > 1 else 0.0

        return SimulationMetrics(
            avg_wait             = avg_wait,
            p95_wait             = p95_wait,
            throughput_per_min   = throughput,
            net_energy           = net_energy,
            fairness_variance    = fairness,
            overload_violations  = self.overload_violations,
            served               = served,
            dropped              = self.dropped,
        )
