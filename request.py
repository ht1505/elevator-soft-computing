"""
request.py — Request class and queue manager for the Smart Elevator System.

Handles creation, validation, deduplication, and storage of elevator requests.
"""

from config import DIR_UP, DIR_DOWN


class Request:
    """
    Represents a single elevator hall-call request.

    Attributes:
        request_id (int): Unique identifier for this request.
        floor (int): The floor where the request was made.
        direction (str): Direction the passenger wants to go (UP/DOWN).
        timestamp (float): Simulation time when the request was created.
        assigned_elevator (int or None): ID of the elevator assigned to serve this request.
        pickup_time (float or None): Simulation time when passenger was picked up.
        dropoff_time (float or None): Simulation time when passenger was dropped off.
        wait_time (float or None): Time waited = pickup_time - timestamp.
        fuzzy_score (float or None): The winning fuzzy score for assignment.
        ga_improvement (float or None): Percentage improvement from GA optimization.
        destination_floor (int or None): Floor the passenger wants to reach.
        picked_up (bool): Whether the passenger has been picked up.
        served (bool): Whether this request has been fully served (dropped off).
    """

    # Class-level counter for unique IDs
    _next_id = 0

    def __init__(self, floor, direction, timestamp=0.0, destination_floor=None):
        """
        Create a new Request.

        Args:
            floor (int): Floor where request originates.
            direction (str): UP or DOWN.
            timestamp (float): Simulation timestamp of request creation.
            destination_floor (int or None): Target floor for the passenger.
        """
        Request._next_id += 1
        self.request_id = Request._next_id
        self.floor = floor
        self.direction = direction
        self.timestamp = timestamp
        self.assigned_elevator = None        # set after fuzzy assignment
        self.pickup_time = None              # set when elevator arrives at pickup floor
        self.dropoff_time = None             # set when passenger reaches destination
        self.wait_time = None                # computed at pickup
        self.fuzzy_score = None              # best fuzzy score at assignment
        self.ga_improvement = None           # GA improvement percentage
        self.destination_floor = destination_floor  # where the passenger goes
        self.picked_up = False               # passenger boarded the elevator
        self.served = False                  # fully served flag (dropped off)

    def mark_assigned(self, elevator_id, score):
        """
        Mark this request as assigned to an elevator.

        Args:
            elevator_id (int): The elevator ID serving this request.
            score (float): The fuzzy suitability score.
        """
        self.assigned_elevator = elevator_id
        self.fuzzy_score = score

    def mark_picked_up(self, current_time):
        """
        Mark this request as picked up (elevator arrived at request floor).

        Args:
            current_time (float): Current simulation time.
        """
        self.picked_up = True
        self.pickup_time = current_time
        self.wait_time = current_time - self.timestamp  # compute waiting time

    def mark_served(self, current_time):
        """
        Mark this request as fully served (passenger dropped off at destination).

        Args:
            current_time (float): Current simulation time.
        """
        self.served = True
        self.dropoff_time = current_time

    def __repr__(self):
        """String representation for debugging."""
        return (f"Request(id={self.request_id}, floor={self.floor}, "
                f"dir={self.direction}, t={self.timestamp}, "
                f"assigned=E{self.assigned_elevator}, "
                f"picked_up={self.picked_up}, served={self.served})")


class RequestQueue:
    """
    Manages all requests in the system — active, pending, and completed.

    Provides deduplication, validation, and retrieval methods.

    Attributes:
        all_requests (list): Complete history of all requests.
        pending (list): Requests not yet assigned to an elevator.
        active (list): Requests assigned but not yet fully served.
        completed (list): Requests that have been fully served.
        num_floors (int): Total number of floors in the building.
    """

    def __init__(self, num_floors):
        """
        Initialize the request queue.

        Args:
            num_floors (int): Total number of floors (0 to num_floors).
        """
        self.all_requests = []
        self.pending = []
        self.active = []
        self.completed = []
        self.num_floors = num_floors

    def validate_request(self, floor, direction):
        """
        Validate a request before creating it.

        Args:
            floor (int): Requested floor.
            direction (str): UP or DOWN.

        Returns:
            tuple: (is_valid, error_message)
        """
        # Check floor range
        if floor < 0 or floor > self.num_floors:
            return False, f"Floor must be between 0 and {self.num_floors}."

        # Edge case: requesting UP from top floor
        if floor == self.num_floors and direction == DIR_UP:
            return False, f"Cannot go UP from the top floor ({self.num_floors})."

        # Edge case: requesting DOWN from ground floor
        if floor == 0 and direction == DIR_DOWN:
            return False, "Cannot go DOWN from the ground floor (0)."

        # Check direction validity
        if direction not in (DIR_UP, DIR_DOWN):
            return False, f"Direction must be '{DIR_UP}' or '{DIR_DOWN}'."

        return True, ""

    def is_duplicate(self, floor, direction):
        """
        Check if an identical request (same floor + direction) is already pending or active.

        Args:
            floor (int): Requested floor.
            direction (str): UP or DOWN.

        Returns:
            bool: True if duplicate exists.
        """
        # Check pending requests
        for req in self.pending:
            if req.floor == floor and req.direction == direction:
                return True

        # Check active (assigned but not yet picked up) requests
        for req in self.active:
            if req.floor == floor and req.direction == direction and not req.picked_up:
                return True

        return False

    def create_request(self, floor, direction, timestamp=0.0, destination_floor=None):
        """
        Create and register a new request after validation and deduplication.

        Args:
            floor (int): Requested floor.
            direction (str): UP or DOWN.
            timestamp (float): When the request was made.
            destination_floor (int or None): Passenger's destination.

        Returns:
            tuple: (Request or None, message)
        """
        # Validate
        is_valid, error = self.validate_request(floor, direction)
        if not is_valid:
            return None, f"Invalid request: {error}"

        # Deduplication check
        if self.is_duplicate(floor, direction):
            return None, f"Duplicate: Floor {floor} {direction} already queued."

        # Create the request
        req = Request(floor, direction, timestamp, destination_floor)
        self.all_requests.append(req)
        self.pending.append(req)
        return req, f"Request #{req.request_id} created: Floor {floor} {direction} at t={timestamp}s"

    def assign_request(self, request, elevator_id, score):
        """
        Move a request from pending to active after assignment.

        Args:
            request (Request): The request to assign.
            elevator_id (int): Elevator ID.
            score (float): Fuzzy score.
        """
        request.mark_assigned(elevator_id, score)  # record assignment
        if request in self.pending:
            self.pending.remove(request)            # remove from pending
        self.active.append(request)                 # add to active

    def pickup_request(self, request, current_time):
        """
        Mark a request as picked up (passenger boarded elevator).
        Request stays in active list until fully served (dropped off).

        Args:
            request (Request): The request to mark as picked up.
            current_time (float): Current simulation time.
        """
        request.mark_picked_up(current_time)  # record pickup time

    def complete_request(self, request, current_time):
        """
        Move a request from active to completed (passenger dropped off).

        Args:
            request (Request): The request to complete.
            current_time (float): Current simulation time.
        """
        request.mark_served(current_time)     # mark as fully served
        if request in self.active:
            self.active.remove(request)       # move from active
        self.completed.append(request)        # to completed

    def get_pickup_requests_at_floor(self, elevator_id, floor):
        """
        Get active requests waiting to be picked up at a specific floor
        for a specific elevator.

        Args:
            elevator_id (int): The elevator ID.
            floor (int): The floor to check.

        Returns:
            list: Requests waiting for pickup at this floor.
        """
        return [r for r in self.active
                if r.assigned_elevator == elevator_id
                and r.floor == floor
                and not r.picked_up]

    def get_unserved_for_elevator(self, elevator_id):
        """
        Get all active (unserved) requests assigned to a specific elevator.

        Args:
            elevator_id (int): The elevator ID.

        Returns:
            list: List of active Request objects for that elevator.
        """
        return [r for r in self.active
                if r.assigned_elevator == elevator_id and not r.served]

    def get_stats(self):
        """
        Get summary statistics about the request queue.

        Returns:
            dict: Statistics including counts and averages.
        """
        wait_times = [r.wait_time for r in self.completed if r.wait_time is not None]
        return {
            "total_requests": len(self.all_requests),
            "pending": len(self.pending),
            "active": len(self.active),
            "completed": len(self.completed),
            "avg_wait_time": sum(wait_times) / len(wait_times) if wait_times else 0.0,
            "best_wait_time": min(wait_times) if wait_times else 0.0,
            "worst_wait_time": max(wait_times) if wait_times else 0.0,
        }

    @staticmethod
    def reset_id_counter():
        """Reset the request ID counter (useful for testing)."""
        Request._next_id = 0
