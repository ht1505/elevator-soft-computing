"""
elevator.py — Elevator class with full state machine and LOOK algorithm.

Implements the 5-state machine (IDLE, MOVING_UP, MOVING_DOWN, DOOR_OPEN,
DOOR_CLOSING) along with the LOOK algorithm for directional serving and
passing-by pickup logic.
"""

import copy
import random
from config import (
    FLOOR_TRAVEL_TIME, DOOR_OPEN_TIME, DOOR_CLOSE_TIME, MAX_CAPACITY,
    DIR_UP, DIR_DOWN, DIR_IDLE,
    STATE_IDLE, STATE_MOVING_UP, STATE_MOVING_DOWN,
    STATE_DOOR_OPEN, STATE_DOOR_CLOSING,
    STATE_ACCEL_UP, STATE_ACCEL_DOWN, STATE_DECEL_UP, STATE_DECEL_DOWN,
    STATE_LEVELING, STATE_DOOR_PRE_OPEN, STATE_DOOR_OPENING,
    STATE_OVERLOAD, STATE_DOOR_STUCK, STATE_E_STOP, STATE_FIRE_RECALL,
    ACCEL_PHASE_TIME, DECEL_PHASE_TIME, DOOR_OPENING_TIME, LEVELING_TOLERANCE,
    MAX_LOAD_KG, KG_PER_PERSON, DOOR_STUCK_THRESHOLD,
    ENERGY_PER_FLOOR, ENERGY_LOAD_FACTOR, ENERGY_REGEN_FACTOR,
    SIM_TICK_SIZE
)


class Passenger:
    """
    Represents a passenger inside an elevator.

    Attributes:
        origin_floor (int): Floor where the passenger boarded.
        destination_floor (int): Floor where the passenger wants to go.
        board_time (float): Simulation time when passenger boarded.
    """

    def __init__(self, origin_floor, destination_floor, board_time=0.0):
        """
        Create a new passenger.

        Args:
            origin_floor (int): Starting floor.
            destination_floor (int): Target floor.
            board_time (float): Time of boarding.
        """
        self.origin_floor = origin_floor
        self.destination_floor = destination_floor
        self.board_time = board_time

    def __repr__(self):
        return f"Passenger({self.origin_floor}→{self.destination_floor})"


class Elevator:
    """
    Represents a single elevator with full 13-state machine.

    States: IDLE → ACCEL_UP/DOWN → MOVING_UP/DOWN → DECEL_UP/DOWN → LEVELING →
            DOOR_PRE_OPEN → DOOR_OPENING → DOOR_OPEN → DOOR_CLOSING
            + Fault states: OVERLOAD, DOOR_STUCK, E_STOP, FIRE_RECALL
    
    Uses the LOOK algorithm for directional service with realistic physics:
    - Acceleration phase: linear ramp from 0 to max speed
    - Constant speed phase: steady movement
    - Deceleration phase: linear ramp back to 0
    - Leveling: sub-floor precision alignment
    - Door animation: 0.0 (closed) → 1.0 (open)

    Attributes:
        id (int): Unique elevator identifier.
        current_floor (float): Current position (e.g. 3.5 = between 3 and 4).
        state (str): Current state from the 13-state machine.
        direction (str): Current movement direction (UP/DOWN/IDLE).
        stop_queue (list): Ordered list of floor stops to serve.
        passengers (list): List of Passenger objects currently onboard.
        current_load (int): Number of passengers onboard.
        door_position (float): Door animation state (0.0=closed, 1.0=open).
        reopen_count (int): Number of times door has reopened this cycle.
        total_floors_traveled (float): Cumulative floors traveled.
        energy_consumed (float): Total energy used.
        energy_regenerated (float): Energy recovered from descent.
        passengers_served (int): Total passengers delivered.
        door_timer (float): Countdown timer for door operations.
        accel_timer (float): Acceleration phase timer.
        decel_timer (float): Deceleration phase timer.
        num_floors (int): Total floors in the building.
    """

    def __init__(self, elevator_id, num_floors, start_floor=0):
        """
        Initialize an elevator.

        Args:
            elevator_id (int): Unique ID for this elevator.
            num_floors (int): Total number of floors in the building.
            start_floor (int): Starting floor position.
        """
        self.id = elevator_id
        self.current_floor = float(start_floor)  # float for fractional positions
        self.state = STATE_IDLE
        self.direction = DIR_IDLE
        self.stop_queue = []                      # ordered floor stops
        self.passengers = []                      # onboard passengers
        self.current_load = 0                     # passenger count
        self.door_position = 0.0                  # door animation: 0.0=closed, 1.0=open
        self.reopen_count = 0                     # times door reopened this cycle
        self.total_floors_traveled = 0.0          # cumulative distance
        self.energy_consumed = 0.0                # energy tracking
        self.energy_regenerated = 0.0             # regen tracking
        self.passengers_served = 0                # delivery count
        self.door_timer = 0.0                     # door operation timer
        self.accel_timer = 0.0                    # acceleration phase timer
        self.decel_timer = 0.0                    # deceleration phase timer
        self.num_floors = num_floors              # building height
        self._last_floor_event = -1               # avoid duplicate floor events

    def add_stop(self, floor):
        """
        Add a floor to the stop queue if not already present.

        Args:
            floor (int): Floor number to add.

        Returns:
            bool: True if stop was added, False if already queued.
        """
        if floor in self.stop_queue:
            return False  # already queued — skip duplicate
        self.stop_queue.append(floor)
        self._sort_stops()  # re-sort based on LOOK algorithm
        return True

    def set_route(self, route):
        """
        Replace the entire stop queue with a GA-optimized route.

        Args:
            route (list): Ordered list of floor stops from GA.
        """
        self.stop_queue = list(route)  # replace with optimized order

    def _sort_stops(self):
        """
        Sort stop queue according to the LOOK algorithm.

        LOOK UP: serve ascending stops first.
        LOOK DOWN: serve descending stops first.
        IDLE: sort ascending by default.
        """
        if not self.stop_queue:
            return

        current = int(round(self.current_floor))

        if self.direction == DIR_UP or self.direction == DIR_IDLE:
            # Split into ahead (above or equal) and behind (below)
            ahead = sorted([f for f in self.stop_queue if f >= current])
            behind = sorted([f for f in self.stop_queue if f < current], reverse=True)
            self.stop_queue = ahead + behind  # serve ahead first, then reverse
        elif self.direction == DIR_DOWN:
            # Split into ahead (below or equal) and behind (above)
            ahead = sorted([f for f in self.stop_queue if f <= current], reverse=True)
            behind = sorted([f for f in self.stop_queue if f > current])
            self.stop_queue = ahead + behind  # serve ahead first, then reverse

    def is_passing_by_eligible(self, request_floor, request_direction):
        """
        Check if the elevator can pick up a request as a passing-by stop.

        The elevator must be:
          1. Moving in the same direction as the request
          2. Not yet passed the request floor

        Args:
            request_floor (int): The floor of the request.
            request_direction (str): Direction of the request (UP/DOWN).

        Returns:
            tuple: (eligible: bool, reason: str)
        """
        # Elevator at exact floor → stop immediately
        if abs(self.current_floor - request_floor) < 0.1:
            return True, "Elevator at request floor — STOP NOW"

        # Elevator is IDLE → always eligible (will move to floor)
        if self.state == STATE_IDLE or self.direction == DIR_IDLE:
            return True, "Elevator is IDLE — can serve any request"

        # Moving UP + request is UP
        if self.direction == DIR_UP and request_direction == DIR_UP:
            if self.current_floor < request_floor:
                return True, "Moving UP, floor NOT yet passed -- PASSING-BY ELIGIBLE"
            else:
                return False, f"Moving UP but floor {request_floor} ALREADY PASSED (at {self.current_floor:.1f})"

        # Moving DOWN + request is DOWN
        if self.direction == DIR_DOWN and request_direction == DIR_DOWN:
            if self.current_floor > request_floor:
                return True, "Moving DOWN, floor NOT yet passed -- PASSING-BY ELIGIBLE"
            else:
                return False, f"Moving DOWN but floor {request_floor} ALREADY PASSED (at {self.current_floor:.1f})"

        # Moving in opposite direction
        if self.direction == DIR_UP and request_direction == DIR_DOWN:
            return False, "Elevator moving UP, request is DOWN — opposite direction"
        if self.direction == DIR_DOWN and request_direction == DIR_UP:
            return False, "Elevator moving DOWN, request is UP — opposite direction"

        return False, "Direction mismatch"

    def can_board(self):
        """
        Check if the elevator has capacity for more passengers.

        Returns:
            bool: True if current_load < MAX_CAPACITY.
        """
        return self.current_load < MAX_CAPACITY

    def board_passenger(self, passenger):
        """
        Add a passenger to the elevator.

        Args:
            passenger (Passenger): The passenger boarding.

        Returns:
            bool: True if boarded successfully, False if at capacity.
        """
        if not self.can_board():
            return False  # at full capacity
        self.passengers.append(passenger)
        self.current_load = len(self.passengers)
        
        # Reset reopen count when passengers board during DOOR_OPEN
        if self.state == STATE_DOOR_OPEN:
            self.reopen_count = 0
        
        # Add destination to stops if not already there
        if passenger.destination_floor not in self.stop_queue:
            self.stop_queue.append(passenger.destination_floor)
            self._sort_stops()
        return True

    def emergency_stop(self):
        """
        Engage emergency stop.

        Clears all stops, sets state to E_STOP, and emits an event.

        Returns:
            tuple: (event_type, elevator_id, message)
        """
        self.stop_queue = []
        self.state = STATE_E_STOP
        self.direction = DIR_IDLE
        return ("E_STOP", self.id, "Emergency stop activated")

    def fire_recall(self, lobby=0):
        """
        Activate fire recall mode.

        Clears all stops, sets lobby as single destination, moves toward it.

        Args:
            lobby (int): Lobby floor number (default 0).

        Returns:
            tuple: (event_type, elevator_id, message)
        """
        self.stop_queue = [lobby]
        self.state = STATE_FIRE_RECALL
        # Determine direction toward lobby
        if self.current_floor < lobby:
            self.direction = DIR_UP
        elif self.current_floor > lobby:
            self.direction = DIR_DOWN
        else:
            self.direction = DIR_IDLE
        return ("FIRE_RECALL", self.id, f"Fire recall activated - moving to floor {lobby}")

    def alight_passengers(self, floor):
        """
        Remove all passengers whose destination is this floor.

        Args:
            floor (int): Current floor to check for alighting.

        Returns:
            list: Passengers who alighted.
        """
        alighting = [p for p in self.passengers if p.destination_floor == floor]
        self.passengers = [p for p in self.passengers if p.destination_floor != floor]
        self.current_load = len(self.passengers)
        self.passengers_served += len(alighting)  # increment served count
        
        # Reset reopen count when passengers alight during DOOR_OPEN
        if self.state == STATE_DOOR_OPEN and len(alighting) > 0:
            self.reopen_count = 0
        
        return alighting

    def get_next_stop(self):
        """
        Get the next floor this elevator should visit.

        Returns:
            int or None: Next floor in stop queue, or None if empty.
        """
        if self.stop_queue:
            return self.stop_queue[0]
        return None

    def arrive_at_floor(self, floor):
        """
        Process arrival at a specific floor.

        Removes the floor from stop queue, transitions to DOOR_PRE_OPEN.

        Args:
            floor (int): The floor arrived at.
        """
        # Remove this floor from stop queue
        if floor in self.stop_queue:
            self.stop_queue.remove(floor)

        # Snap position to exact floor
        self.current_floor = float(floor)
        
        # Transition to door pre-open for safety check
        self.state = STATE_DOOR_PRE_OPEN

    def update_tick(self, tick_size=None):
        """
        Advance the elevator state by one simulation tick.

        Implements the full 13-state machine with realistic physics:
        IDLE → ACCEL_UP/DOWN → MOVING_UP/DOWN → DECEL_UP/DOWN → 
        LEVELING → DOOR_PRE_OPEN → DOOR_OPENING → DOOR_OPEN → DOOR_CLOSING

        Plus fault states: OVERLOAD, DOOR_STUCK, E_STOP, FIRE_RECALL

        Args:
            tick_size (float): Time step in seconds.

        Returns:
            list: Events generated this tick (e.g. floor arrivals).
        """
        if tick_size is None:
            tick_size = SIM_TICK_SIZE

        events = []
        max_speed = 1.0 / FLOOR_TRAVEL_TIME  # floors per second

        # ─── Emergency/Fault States ──────────────────────────────────────
        if self.state == STATE_E_STOP:
            # Emergency stop — do nothing, stay in this state
            return events

        if self.state == STATE_FIRE_RECALL:
            # Fire recall — move to lobby (treat as normal movement to target)
            next_stop = self.get_next_stop()
            if next_stop is not None:
                # Move toward lobby normally
                if self.current_floor < next_stop:
                    self.state = STATE_ACCEL_UP
                    self.direction = DIR_UP
                    self.accel_timer = ACCEL_PHASE_TIME
                elif self.current_floor > next_stop:
                    self.state = STATE_ACCEL_DOWN
                    self.direction = DIR_DOWN
                    self.accel_timer = ACCEL_PHASE_TIME
            return events

        if self.state == STATE_OVERLOAD:
            # Overload state — wait for passengers to exit
            # (Passengers exit during DOOR_OPEN, then return to normal)
            if self.current_load < MAX_LOAD_KG / KG_PER_PERSON:
                # Capacity OK now, transition to door opening
                self.state = STATE_DOOR_OPENING
                self.door_timer = DOOR_OPENING_TIME
                self.door_position = 0.0
                events.append(("OVERLOAD_RESOLVED", self.id, self.current_floor))
            return events

        if self.state == STATE_DOOR_STUCK:
            # Door stuck — remain in fault state or transition to IDLE after timeout
            # (In real system, would alert maintenance)
            return events

        # ─── Acceleration Phase ──────────────────────────────────────────
        if self.state == STATE_ACCEL_UP:
            # Accelerate upward: speed ramps from 0 to max_speed linearly
            self.accel_timer -= tick_size
            progress = max(0.0, 1.0 - self.accel_timer / ACCEL_PHASE_TIME)  # 0→1
            current_speed = max_speed * progress
            movement = current_speed * tick_size
            self.current_floor += movement
            self._clamp_current_floor()
            self.total_floors_traveled += movement
            self._apply_energy_cost(movement)

            # Check if accel phase is complete
            if self.accel_timer <= 0:
                self.state = STATE_MOVING_UP
                self.accel_timer = 0.0
                events.append(("ACCEL_COMPLETE", self.id, self.current_floor))

            # Check if we're close to deceleration point
            next_stop = self.get_next_stop()
            if next_stop is not None and self.current_floor >= next_stop - 1.0:
                # Start deceleration 1 floor before target
                self.state = STATE_DECEL_UP
                self.decel_timer = DECEL_PHASE_TIME
                events.append(("DECEL_START", self.id, self.current_floor))

            return events

        if self.state == STATE_ACCEL_DOWN:
            # Accelerate downward: speed ramps from 0 to max_speed linearly
            self.accel_timer -= tick_size
            progress = max(0.0, 1.0 - self.accel_timer / ACCEL_PHASE_TIME)  # 0→1
            current_speed = max_speed * progress
            movement = current_speed * tick_size
            self.current_floor -= movement
            self._clamp_current_floor()
            self.total_floors_traveled += movement
            self._apply_energy_cost(movement, regen=True)

            # Check if accel phase is complete
            if self.accel_timer <= 0:
                self.state = STATE_MOVING_DOWN
                self.accel_timer = 0.0
                events.append(("ACCEL_COMPLETE", self.id, self.current_floor))

            # Check if we're close to deceleration point
            next_stop = self.get_next_stop()
            if next_stop is not None and self.current_floor <= next_stop + 1.0:
                # Start deceleration 1 floor before target
                self.state = STATE_DECEL_DOWN
                self.decel_timer = DECEL_PHASE_TIME
                events.append(("DECEL_START", self.id, self.current_floor))

            return events

        # ─── Constant Speed Phase ───────────────────────────────────────
        if self.state == STATE_MOVING_UP:
            # Move at constant speed upward
            movement = max_speed * tick_size
            self.current_floor += movement
            self._clamp_current_floor()
            self.total_floors_traveled += movement
            self._apply_energy_cost(movement)

            # Check if we should start decelerating (1 floor away)
            next_stop = self.get_next_stop()
            if next_stop is not None and self.current_floor >= next_stop - 1.0:
                self.state = STATE_DECEL_UP
                self.decel_timer = DECEL_PHASE_TIME
                events.append(("DECEL_START", self.id, self.current_floor))

            return events

        if self.state == STATE_MOVING_DOWN:
            # Move at constant speed downward
            movement = max_speed * tick_size
            self.current_floor -= movement
            self._clamp_current_floor()
            self.total_floors_traveled += movement
            self._apply_energy_cost(movement, regen=True)

            # Check if we should start decelerating (1 floor away)
            next_stop = self.get_next_stop()
            if next_stop is not None and self.current_floor <= next_stop + 1.0:
                self.state = STATE_DECEL_DOWN
                self.decel_timer = DECEL_PHASE_TIME
                events.append(("DECEL_START", self.id, self.current_floor))

            return events

        # ─── Deceleration Phase ─────────────────────────────────────────
        if self.state == STATE_DECEL_UP:
            # Decelerate upward: speed ramps from max_speed to 0 linearly
            self.decel_timer -= tick_size
            progress = self.decel_timer / DECEL_PHASE_TIME  # 1→0
            progress = max(0.0, progress)
            current_speed = max_speed * progress
            movement = current_speed * tick_size
            self.current_floor += movement
            self._clamp_current_floor()
            self.total_floors_traveled += movement
            self._apply_energy_cost(movement)

            # Check if decel phase is complete
            if self.decel_timer <= 0:
                self.state = STATE_LEVELING
                self.decel_timer = 0.0
                events.append(("LEVELING_START", self.id, self.current_floor))

            return events

        if self.state == STATE_DECEL_DOWN:
            # Decelerate downward: speed ramps from max_speed to 0 linearly
            self.decel_timer -= tick_size
            progress = self.decel_timer / DECEL_PHASE_TIME  # 1→0
            progress = max(0.0, progress)
            current_speed = max_speed * progress
            movement = current_speed * tick_size
            self.current_floor -= movement
            self._clamp_current_floor()
            self.total_floors_traveled += movement
            self._apply_energy_cost(movement, regen=True)

            # Check if decel phase is complete
            if self.decel_timer <= 0:
                self.state = STATE_LEVELING
                self.decel_timer = 0.0
                events.append(("LEVELING_START", self.id, self.current_floor))

            return events

        # ─── Leveling Phase (Floor Alignment) ───────────────────────────
        if self.state == STATE_LEVELING:
            # Snap position to nearest integer floor within tolerance
            next_stop = self.get_next_stop()
            if next_stop is not None:
                error = abs(self.current_floor - next_stop)
                if error <= LEVELING_TOLERANCE:
                    # Within tolerance — snap to exact floor and prepare door
                    self.arrive_at_floor(next_stop)
                    events.append(("LEVELED", self.id, next_stop))
                    events.append(("FLOOR_ARRIVAL", self.id, next_stop))
                else:
                    # Still need to fine-tune — move slowly toward target
                    micro_speed = 0.1  # very slow movement
                    if self.current_floor < next_stop:
                        self.current_floor += micro_speed * tick_size
                    else:
                        self.current_floor -= micro_speed * tick_size
                    self._clamp_current_floor()
            else:
                # No next stop — shouldn't happen, but go idle
                self.state = STATE_IDLE
                self.direction = DIR_IDLE

            return events

        # ─── Door Pre-Open (Safety Check) ───────────────────────────────
        if self.state == STATE_DOOR_PRE_OPEN:
            # 1-tick safety check: verify capacity before opening door
            current_load_kg = self.current_load * KG_PER_PERSON
            if current_load_kg >= MAX_LOAD_KG:
                # Overload detected — go to overload state, emit event
                self.state = STATE_OVERLOAD
                events.append(("OVERLOAD", self.id, f"Current load {current_load_kg} kg >= {MAX_LOAD_KG} kg"))
            else:
                # Capacity OK — proceed to door opening
                self.state = STATE_DOOR_OPENING
                self.door_timer = DOOR_OPENING_TIME
                self.door_position = 0.0
                self.reopen_count = 0

            return events

        # ─── Door Opening Phase ─────────────────────────────────────────
        if self.state == STATE_DOOR_OPENING:
            # Animate door opening: door_position 0.0 → 1.0
            self.door_timer -= tick_size
            elapsed = DOOR_OPENING_TIME - self.door_timer
            self.door_position = min(1.0, elapsed / DOOR_OPENING_TIME)

            if self.door_timer <= 0:
                # Door fully open
                self.state = STATE_DOOR_OPEN
                self.door_timer = DOOR_OPEN_TIME
                self.door_position = 1.0
                events.append(("DOOR_OPEN", self.id, self.current_floor))

            return events

        # ─── Door Open (Dwell Time) ───────────────────────────────────
        if self.state == STATE_DOOR_OPEN:
            # Dwell at the floor — passengers alight/board
            self.door_timer -= tick_size
            if self.door_timer <= 0:
                # Dwell time complete — start closing door
                self.state = STATE_DOOR_CLOSING
                self.door_timer = DOOR_CLOSE_TIME
                events.append(("DOOR_OPEN_END", self.id, self.current_floor))

            return events

        # ─── Door Closing Phase ──────────────────────────────────────
        if self.state == STATE_DOOR_CLOSING:
            # Animate door closing: door_position 1.0 → 0.0
            # Also handle door obstruction (5% chance per tick)
            self.door_timer -= tick_size
            elapsed = DOOR_CLOSE_TIME - self.door_timer
            self.door_position = max(0.0, 1.0 - elapsed / DOOR_CLOSE_TIME)

            # Simulate door obstruction: 5% chance per tick -> force reopen
            if random.random() < 0.05:
                # Obstruction detected — reopen the door
                self.reopen_count += 1
                if self.reopen_count >= DOOR_STUCK_THRESHOLD:
                    # Too many reopens — door stuck fault
                    self.state = STATE_DOOR_STUCK
                    self.door_position = 0.5  # partially open
                    events.append(("DOOR_STUCK", self.id, 
                                 f"Door reopened {self.reopen_count} times - stuck"))
                else:
                    # Reopen the door
                    self.state = STATE_DOOR_OPENING
                    self.door_timer = DOOR_OPENING_TIME
                    self.door_position = 0.0
                    events.append(("DOOR_OBSTRUCTION", self.id, 
                                 f"Obstruction detected - reopen #{self.reopen_count}"))
                return events

            if self.door_timer <= 0:
                # Door fully closed — resume movement or go idle
                self.state = STATE_IDLE
                self.door_position = 0.0
                events.append(("DOOR_CLOSE_END", self.id, self.current_floor))
                self._resume_after_door_close(events)

            return events

        # ─── Idle State ──────────────────────────────────────────────────
        if self.state == STATE_IDLE:
            # Check if there are stops to serve
            if self.stop_queue:
                next_stop = self.stop_queue[0]
                current = int(round(self.current_floor))

                if next_stop > current:
                    self.state = STATE_ACCEL_UP
                    self.direction = DIR_UP
                    self.accel_timer = ACCEL_PHASE_TIME
                elif next_stop < current:
                    self.state = STATE_ACCEL_DOWN
                    self.direction = DIR_DOWN
                    self.accel_timer = ACCEL_PHASE_TIME
                else:
                    # Already at the floor — go straight to door pre-check
                    self.arrive_at_floor(next_stop)
                    events.append(("FLOOR_ARRIVAL", self.id, next_stop))

        return events

    def _apply_energy_cost(self, distance, regen=False):
        """
        Apply energy cost for movement.

        Args:
            distance (float): Distance traveled in floors.
            regen (bool): Whether to apply regenerative braking.
        """
        load_energy = (ENERGY_PER_FLOOR + ENERGY_LOAD_FACTOR * self.current_load) * distance
        self.energy_consumed += load_energy
        if regen:
            self.energy_regenerated += load_energy * ENERGY_REGEN_FACTOR

    def _clamp_current_floor(self):
        """Keep position within physical shaft bounds."""
        self.current_floor = max(0.0, min(float(self.num_floors), self.current_floor))

    def _has_reached_floor(self, target_floor):
        """
        Check if elevator has reached or passed the target floor.

        Args:
            target_floor (int): Floor to check against.

        Returns:
            bool: True if reached within threshold of one tick's travel.
        """
        threshold = (1.0 / FLOOR_TRAVEL_TIME) * SIM_TICK_SIZE + 0.01
        return abs(self.current_floor - target_floor) < threshold

    def _start_moving(self):
        """
        Start moving toward the next stop in queue.
        Sets direction and state based on next stop relative to current floor.
        """
        if not self.stop_queue:
            self.state = STATE_IDLE
            self.direction = DIR_IDLE
            return

        next_stop = self.stop_queue[0]
        current = round(self.current_floor)

        if next_stop > current:
            self.state = STATE_MOVING_UP
            self.direction = DIR_UP
        elif next_stop < current:
            self.state = STATE_MOVING_DOWN
            self.direction = DIR_DOWN
        else:
            # Already at the floor — arrive immediately
            self.arrive_at_floor(next_stop)

    def _resume_after_door_close(self, events):
        """
        Decide what to do after door closes.

        If stops remain: transition to IDLE, which will start movement next tick.
        If no stops: stay IDLE.

        Args:
            events (list): Event list to append to.
        """
        # Simply return to IDLE state — the IDLE handler will decide next action
        self.state = STATE_IDLE
        self.direction = DIR_IDLE
        # If there are stops, IDLE will start movement in next tick

    def get_eta_to_next_stop(self):
        """
        Calculate estimated time of arrival to the next stop.

        Returns:
            float: ETA in seconds, or 0.0 if no next stop.
        """
        next_stop = self.get_next_stop()
        if next_stop is None:
            return 0.0

        distance = abs(next_stop - self.current_floor)
        travel_time = distance * FLOOR_TRAVEL_TIME  # seconds
        return travel_time

    def get_status_dict(self):
        """
        Get a dictionary summarizing elevator status.

        Returns:
            dict: Current elevator status.
        """
        return {
            "id": self.id,
            "floor": self.current_floor,
            "state": self.state,
            "direction": self.direction,
            "stop_queue": list(self.stop_queue),
            "load": f"{self.current_load}/{MAX_CAPACITY}",
            "door_position": self.door_position,
            "reopen_count": self.reopen_count,
            "eta_next": self.get_eta_to_next_stop(),
            "total_traveled": self.total_floors_traveled,
            "passengers_served": self.passengers_served,
            "energy_consumed": self.energy_consumed,
            "energy_regenerated": self.energy_regenerated,
        }

    def __repr__(self):
        return (f"Elevator(E{self.id}, floor={self.current_floor:.1f}, "
                f"state={self.state}, dir={self.direction}, "
                f"stops={self.stop_queue}, load={self.current_load}/{MAX_CAPACITY})")
