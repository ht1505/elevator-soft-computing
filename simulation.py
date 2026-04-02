"""
simulation.py — Discrete-Event Simulation Engine for the Smart Elevator System.

Implements:
  - Simulation clock with configurable tick size
  - Event scheduler for elevator operations
  - Position prediction for timer-based requests
  - Live simulation stepping with event callbacks
  - Automatic passenger boarding at pickup floors
  - Automatic passenger alighting at destination floors
"""

import time as real_time
import random
import math
from config import (
    FLOOR_TRAVEL_TIME, DOOR_OPEN_TIME, DOOR_CLOSE_TIME,
    SIM_POISSON_LAMBDA_LIGHT, SIM_POISSON_LAMBDA_PEAK, SIM_POISSON_LAMBDA_INTER,
    SIM_SCENARIO_DURATION,
    SIM_TICK_SIZE, DIR_UP, DIR_DOWN, DIR_IDLE,
    STATE_IDLE, STATE_MOVING_UP, STATE_MOVING_DOWN,
    STATE_DOOR_OPEN, STATE_DOOR_CLOSING
)
from elevator import Passenger


def generate_poisson_requests(lam, duration, num_floors, rng_seed=None):
    """
    Generate Poisson arrivals as (timestamp, floor, direction, destination).

    Inter-arrival time is sampled from expovariate(lam / 60) where lam is
    requests per minute.
    """
    rng = random.Random(rng_seed)
    events = []
    t = 0.0
    rate_per_second = lam / 60.0

    if rate_per_second <= 0:
        return events

    while True:
        t += rng.expovariate(rate_per_second)
        if t > duration:
            break

        floor = rng.randint(0, num_floors)
        if floor <= 0:
            direction = DIR_UP
        elif floor >= num_floors:
            direction = DIR_DOWN
        else:
            direction = rng.choice([DIR_UP, DIR_DOWN])

        if direction == DIR_UP:
            destination = rng.randint(floor + 1, num_floors)
        else:
            destination = rng.randint(0, floor - 1)

        events.append((t, floor, direction, destination))

    return events


class BenchmarkScenario:
    """Factory helpers for benchmark request traces."""

    @staticmethod
    def morning_rush(num_floors):
        rng = random.Random(101)
        events = []
        t = 0.0
        rate_per_second = SIM_POISSON_LAMBDA_PEAK / 60.0
        low_band = min(2, num_floors)

        while True:
            t += rng.expovariate(rate_per_second)
            if t > SIM_SCENARIO_DURATION:
                break

            if rng.random() < 0.8:
                floor = rng.randint(0, low_band)
            else:
                floor = rng.randint(0, num_floors)

            if floor >= num_floors:
                floor = max(0, num_floors - 1)
            direction = DIR_UP
            destination = rng.randint(max(floor + 1, min(3, num_floors)), num_floors)
            events.append((t, floor, direction, destination))

        return events

    @staticmethod
    def evening_rush(num_floors):
        rng = random.Random(202)
        events = []
        t = 0.0
        rate_per_second = SIM_POISSON_LAMBDA_PEAK / 60.0
        high_floor = max(0, num_floors - 2)

        while True:
            t += rng.expovariate(rate_per_second)
            if t > SIM_SCENARIO_DURATION:
                break

            if rng.random() < 0.8:
                floor = rng.randint(high_floor, num_floors)
            else:
                floor = rng.randint(0, num_floors)

            if floor <= 0:
                floor = 1 if num_floors >= 1 else 0
            direction = DIR_DOWN
            destination = rng.randint(0, min(floor - 1, max(2, num_floors // 3)))
            events.append((t, floor, direction, destination))

        return events

    @staticmethod
    def inter_floor(num_floors):
        return generate_poisson_requests(
            SIM_POISSON_LAMBDA_INTER,
            SIM_SCENARIO_DURATION,
            num_floors,
            rng_seed=303,
        )


class MetricsCollector:
    """Collects KPI metrics from simulation events and queue state."""

    def __init__(self, name="scenario"):
        self.name = name
        self.wait_times = []
        self.ride_times = []
        self.total_energy_consumed = 0.0
        self.total_energy_regenerated = 0.0
        self.passengers_served = 0
        self.passengers_missed = 0
        self._seen_request_ids = set()

    def ingest_events(self, events, request_queue, elevators):
        for event in events:
            if isinstance(event, tuple) and len(event) >= 2 and event[0] == "REQUEST_SERVED":
                req = event[1]
                if req.request_id in self._seen_request_ids:
                    continue
                self._seen_request_ids.add(req.request_id)
                self.passengers_served += 1
                if req.wait_time is not None:
                    self.wait_times.append(req.wait_time)
                if req.pickup_time is not None and req.dropoff_time is not None:
                    self.ride_times.append(req.dropoff_time - req.pickup_time)

        self.total_energy_consumed = sum(e.energy_consumed for e in elevators)
        self.total_energy_regenerated = sum(e.energy_regenerated for e in elevators)

    def finalize(self, request_queue):
        self.passengers_missed = len([r for r in request_queue.all_requests if not r.picked_up])

    @staticmethod
    def _percentile(values, p):
        if not values:
            return 0.0
        data = sorted(values)
        idx = min(len(data) - 1, max(0, int(math.ceil((p / 100.0) * len(data)) - 1)))
        return data[idx]

    def as_dict(self, duration_seconds):
        avg_wait = sum(self.wait_times) / len(self.wait_times) if self.wait_times else 0.0
        p95_wait = self._percentile(self.wait_times, 95)
        avg_ride = sum(self.ride_times) / len(self.ride_times) if self.ride_times else 0.0
        throughput = (self.passengers_served / max(duration_seconds, 1.0)) * 60.0
        net_energy = self.total_energy_consumed - self.total_energy_regenerated
        energy_per_trip = net_energy / self.passengers_served if self.passengers_served else 0.0

        return {
            "avg_wait": avg_wait,
            "p95_wait": p95_wait,
            "avg_ride": avg_ride,
            "throughput": throughput,
            "net_energy": net_energy,
            "energy_per_trip": energy_per_trip,
            "served": self.passengers_served,
            "missed": self.passengers_missed,
        }

    def report(self, duration_seconds):
        stats = self.as_dict(duration_seconds)
        print(f"\n  KPI Report — {self.name}")
        print("  " + "-" * 48)
        print(f"  Average wait time:      {stats['avg_wait']:.2f}s")
        print(f"  95th percentile wait:   {stats['p95_wait']:.2f}s")
        print(f"  Average ride time:      {stats['avg_ride']:.2f}s")
        print(f"  Throughput:             {stats['throughput']:.2f} passengers/min")
        print(f"  Net energy:             {stats['net_energy']:.2f}")
        print(f"  Energy per trip:        {stats['energy_per_trip']:.2f}")
        print(f"  Passengers served:      {stats['served']}")
        print(f"  Passengers missed:      {stats['missed']}")


class SimulationClock:
    """
    Discrete-event simulation clock.

    Tracks simulation time and manages scheduled events.

    Attributes:
        current_time (float): Current simulation time in seconds.
        tick_size (float): Duration of each simulation tick.
        events (list): Scheduled future events.
        event_log (list): History of processed events.
    """

    def __init__(self, tick_size=SIM_TICK_SIZE):
        """
        Initialize the simulation clock.

        Args:
            tick_size (float): Time step per tick in seconds.
        """
        self.current_time = 0.0
        self.tick_size = tick_size
        self.events = []       # scheduled events: (time, event_type, data)
        self.event_log = []    # processed event history

    def reset(self):
        """Reset the clock to time 0."""
        self.current_time = 0.0
        self.events = []
        self.event_log = []

    def schedule_event(self, time, event_type, data=None):
        """
        Schedule a future event.

        Args:
            time (float): Simulation time when event should fire.
            event_type (str): Type of event (e.g., 'NEW_REQUEST').
            data (dict or None): Event payload.
        """
        self.events.append((time, event_type, data))
        # Keep events sorted by time
        self.events.sort(key=lambda e: e[0])

    def get_due_events(self):
        """
        Get all events that are due at or before current time.

        Returns:
            list: List of (time, event_type, data) tuples.
        """
        due = []
        remaining = []
        for event in self.events:
            if event[0] <= self.current_time:
                due.append(event)
                self.event_log.append(event)  # log processed events
            else:
                remaining.append(event)
        self.events = remaining
        return due

    def advance(self):
        """
        Advance the clock by one tick.

        Returns:
            float: The new current time.
        """
        self.current_time += self.tick_size
        return self.current_time

    def advance_to(self, target_time):
        """
        Advance the clock to a specific time.

        Args:
            target_time (float): Target simulation time.
        """
        self.current_time = max(self.current_time, target_time)


def predict_position(elevator, future_time, current_time):
    """
    Predict an elevator's position at a future simulation time.

    Accounts for:
      - Current movement speed and direction
      - Pending stops along the way
      - Door open/close times at each stop
      - Direction reversals

    Args:
        elevator: Elevator object.
        future_time (float): Target prediction time.
        current_time (float): Current simulation time.

    Returns:
        tuple: (predicted_floor, predicted_direction, predicted_state)
    """
    delta_time = future_time - current_time  # time to simulate forward

    if delta_time <= 0:
        # Predicting for current time or past — return current state
        return elevator.current_floor, elevator.direction, elevator.state

    # Start from current state
    pos = elevator.current_floor
    direction = elevator.direction
    state = elevator.state
    stops = list(elevator.stop_queue)  # copy to not modify original
    remaining_time = delta_time
    speed = 1.0 / FLOOR_TRAVEL_TIME   # floors per second

    # Handle door states first
    if state == STATE_DOOR_OPEN:
        door_remaining = elevator.door_timer
        if remaining_time <= door_remaining:
            return pos, direction, STATE_DOOR_OPEN  # still in door open
        remaining_time -= door_remaining
        # Now door closing
        close_time = DOOR_CLOSE_TIME
        if remaining_time <= close_time:
            return pos, direction, STATE_DOOR_CLOSING
        remaining_time -= close_time
        state = STATE_IDLE  # door done, check for next action

    elif state == STATE_DOOR_CLOSING:
        close_remaining = elevator.door_timer
        if remaining_time <= close_remaining:
            return pos, direction, STATE_DOOR_CLOSING
        remaining_time -= close_remaining
        state = STATE_IDLE

    # Now simulate movement through stops
    while remaining_time > 0 and stops:
        next_stop = stops[0]
        distance = abs(next_stop - pos)
        travel_time = distance * FLOOR_TRAVEL_TIME  # time to reach stop

        if remaining_time < travel_time:
            # Won't reach the stop — calculate partial position
            if next_stop > pos:
                pos += speed * remaining_time
                direction = DIR_UP
                state = STATE_MOVING_UP
            elif next_stop < pos:
                pos -= speed * remaining_time
                direction = DIR_DOWN
                state = STATE_MOVING_DOWN
            remaining_time = 0
        else:
            # Arrive at the stop
            remaining_time -= travel_time
            pos = float(next_stop)
            stops.pop(0)

            # Door open time
            if remaining_time <= DOOR_OPEN_TIME:
                state = STATE_DOOR_OPEN
                return pos, direction, state
            remaining_time -= DOOR_OPEN_TIME

            # Door close time
            if remaining_time <= DOOR_CLOSE_TIME:
                state = STATE_DOOR_CLOSING
                return pos, direction, state
            remaining_time -= DOOR_CLOSE_TIME

            # Determine next direction
            if stops:
                if stops[0] > pos:
                    direction = DIR_UP
                elif stops[0] < pos:
                    direction = DIR_DOWN
            else:
                direction = DIR_IDLE
                state = STATE_IDLE

    # If we ran out of stops but still have time — elevator is IDLE at last position
    if not stops:
        direction = DIR_IDLE
        state = STATE_IDLE

    return pos, direction, state


class SimulationEngine:
    """
    Full simulation engine that drives elevator movement and event processing.

    Coordinates clock ticks, elevator updates, request processing, and
    provides live simulation capability for timer-based scenarios.

    Core improvement: automatically boards passengers at pickup floors
    and adds their destination floors to the elevator's stop queue,
    so elevators actually carry passengers to their destinations.

    Attributes:
        clock (SimulationClock): The simulation clock.
        elevators (list): List of all Elevator objects.
        request_queue: RequestQueue object.
        num_floors (int): Total floors in the building.
        quiet (bool): When True, suppress per-tick console output.
    """

    def __init__(self, elevators, request_queue, num_floors):
        """
        Initialize the simulation engine.

        Args:
            elevators (list): List of Elevator objects.
            request_queue: RequestQueue object.
            num_floors (int): Total floors.
        """
        self.clock            = SimulationClock()
        self.elevators        = elevators
        self.request_queue    = request_queue
        self.num_floors       = num_floors
        self.request_callback = None
        self.quiet            = False   # set True to suppress per-tick prints

    def _log(self, msg: str) -> None:
        """Print a simulation message only when not in quiet mode."""
        if not self.quiet:
            print(msg, flush=True)

    def step(self):
        """
        Advance the simulation by one tick.

        Updates all elevators, processes due events, handles
        passenger boarding (at pickup floors) and alighting
        (at destination floors).

        Returns:
            list: All events generated this tick.
        """
        self.clock.advance()
        all_events = []

        # Update each elevator
        for elevator in self.elevators:
            events = elevator.update_tick(self.clock.tick_size)
            all_events.extend(events)

        # Process scheduled events
        due_events = self.clock.get_due_events()
        for event_time, event_type, event_data in due_events:
            if event_type == "NEW_REQUEST" and event_data is not None:
                floor = event_data.get("floor")
                direction = event_data.get("direction")
                destination = event_data.get("destination")
                req, _message = self.request_queue.create_request(
                    floor,
                    direction,
                    timestamp=event_time,
                    destination_floor=destination,
                )
                if req is not None and self.request_callback is not None:
                    self.request_callback(req)
                    all_events.append(("REQUEST_CREATED", req))
            else:
                all_events.append((event_type, event_data))

        # Handle FLOOR_ARRIVAL events — board and alight passengers
        for event in all_events:
            if event[0] == "FLOOR_ARRIVAL":
                elev_id  = event[1]
                floor    = event[2]
                elevator = self.elevators[elev_id]
                t        = self.clock.current_time

                # ─── Step A: Alight passengers whose destination is this floor ───
                alighted = elevator.alight_passengers(floor)
                if alighted:
                    self._log(f"    t={t:.1f}s  E{elev_id}  F{floor}  "
                              f"-> {len(alighted)} passenger(s) dropped off")

                # Complete served requests (passenger reached destination)
                for req in list(self.request_queue.active):
                    if (req.assigned_elevator == elev_id
                            and req.destination_floor == floor
                            and req.picked_up
                            and not req.served):
                        self.request_queue.complete_request(req, t)
                        all_events.append(("REQUEST_SERVED", req))
                        self._log(f"    t={t:.1f}s  [OK] Req #{req.request_id} served "
                                  f"(wait {req.wait_time:.1f}s)")

                # ─── Step B: Board passengers waiting at this pickup floor ───
                pickup_requests = self.request_queue.get_pickup_requests_at_floor(
                    elev_id, floor
                )
                for req in pickup_requests:
                    if elevator.can_board() and req.destination_floor is not None:
                        passenger = Passenger(
                            origin_floor      = req.floor,
                            destination_floor = req.destination_floor,
                            board_time        = t,
                        )
                        if elevator.board_passenger(passenger):
                            self.request_queue.pickup_request(req, t)
                            self._log(f"    t={t:.1f}s  E{elev_id}  F{floor}  "
                                      f"-> picked up  dest F{req.destination_floor}")
                    elif not elevator.can_board():
                        self._log(f"    t={t:.1f}s  [!!] E{elev_id} at capacity -- "
                                  f"cannot board at F{floor}")

        return all_events

    def run_until(self, target_time, visualizer=None, live_display=False,
                  display_interval=3.0):
        """
        Run the simulation until target_time, one tick at a time.

        Live shaft snapshots are printed every display_interval seconds when
        live_display=True.  All per-event messages are gated by self.quiet.

        Args:
            target_time:      Simulation time to run until (seconds).
            visualizer:       Visualizer instance (optional).
            live_display:     Print shaft snapshots at each interval.
            display_interval: Seconds between shaft snapshots.

        Returns:
            list: All events generated during the run.
        """
        all_events        = []
        last_display_time = self.clock.current_time

        while self.clock.current_time < target_time:
            events = self.step()
            all_events.extend(events)

            if live_display and visualizer:
                elapsed = self.clock.current_time - last_display_time
                if elapsed >= display_interval:
                    print(f"\n  ─── t={self.clock.current_time:.1f}s ─────────────────────",
                          flush=True)
                    visualizer.render_shaft(self.elevators, self.num_floors)
                    last_display_time = self.clock.current_time
                    real_time.sleep(0.05)

        # Always end on a clean newline so subsequent output is not appended
        print(flush=True)
        return all_events

    def predict_all_positions(self, future_time):
        """
        Predict all elevators' positions at a future time.

        Args:
            future_time (float): Target simulation time.

        Returns:
            list: List of (predicted_floor, predicted_direction, predicted_state)
                  for each elevator.
        """
        predictions = []
        for elevator in self.elevators:
            pred = predict_position(elevator, future_time, self.clock.current_time)
            predictions.append(pred)
        return predictions

    def get_current_time(self):
        """
        Get the current simulation time.

        Returns:
            float: Current time in seconds.
        """
        return self.clock.current_time
