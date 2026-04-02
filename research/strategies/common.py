"""
research/strategies/common.py — Shared utilities for dispatch strategy implementations.

Provides:
    eta_score       — scalar cost estimate for assigning an elevator
    look_route      — LOOK-algorithm stop ordering (mirrors elevator.py _sort_stops)
    _make_decision  — factory for DispatchDecision + DecisionExplanation, eliminates
                      boilerplate across all five strategy files
"""

from __future__ import annotations

from typing import Dict, List, Optional

from research.core.models import DecisionExplanation, DispatchDecision, ElevatorState


def eta_score(e: ElevatorState, floor: int) -> float:
    """
    Estimate the time cost for elevator e to accept one more request at floor.

    A simple linear model:
        cost = |current_floor − floor| + (queue_length × 1.5)

    The 1.5 factor penalises each pending stop roughly one floor's worth of
    additional delay. Does not account for direction — use LOOKDispatch or
    FuzzyDispatch for direction-aware scoring.

    Args:
        e:     ElevatorState object.
        floor: Target floor for the new request.

    Returns:
        Non-negative float; lower is better.
    """
    return abs(e.current_floor - floor) + len(e.stop_queue) * 1.5


def look_route(start_floor: int, stops: List[int], direction: str) -> List[int]:
    """
    Sort a list of floor stops using the LOOK algorithm.

    LOOK scans in one direction first (serving all stops ahead), then
    reverses and serves the remaining stops.  This mirrors the behaviour
    of Elevator._sort_stops() in the root-level elevator.py.

    Args:
        start_floor: Current integer floor of the elevator.
        stops:       Unsorted list of floor stops (may contain duplicates).
        direction:   Current travel direction ("UP" or "DOWN").

    Returns:
        Ordered list of unique floor stops.
    """
    if not stops:
        return []
    uniq  = sorted(set(stops))
    above = [s for s in uniq if s >= start_floor]
    below = [s for s in uniq if s <  start_floor]

    if direction == "DOWN":
        # Serve descending stops first, then sweep up
        return list(reversed(below)) + list(reversed(above))
    # Default UP: serve ascending stops first, then sweep down
    return above + list(reversed(below))


def _make_decision(
    request_id:      int,
    elevator_id:     int,
    score:           float,
    traffic_mode:    str,
    policy_name:     str,
    policy_metadata: Optional[Dict] = None,
) -> DispatchDecision:
    """
    Build a DispatchDecision with an embedded DecisionExplanation.

    This factory eliminates the repetitive construction of
    DecisionExplanation + DispatchDecision across all strategy files.

    Args:
        request_id:      ID of the hall-call request being assigned.
        elevator_id:     ID of the chosen elevator.
        score:           Numeric suitability score in [0, 100].
        traffic_mode:    Current traffic mode string (for logging/explainability).
        policy_name:     Short human-readable label (e.g. "fcfs", "look").
        policy_metadata: Optional dict of diagnostic key–value pairs to include
                         in the memberships field of DecisionExplanation.

    Returns:
        Fully populated DispatchDecision.
    """
    explanation = DecisionExplanation(
        elevator_id      = elevator_id,
        score            = score,
        memberships      = {policy_name: policy_metadata or {}},
        rule_activations = [],
        traffic_mode     = traffic_mode,
    )
    return DispatchDecision(
        request_id        = request_id,
        selected_elevator = elevator_id,
        score             = score,
        explanation       = explanation,
    )
