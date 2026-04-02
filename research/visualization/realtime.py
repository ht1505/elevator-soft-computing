from __future__ import annotations

from typing import List

from research.core.models import ElevatorState


def render_snapshot(elevators: List[ElevatorState], num_floors: int, t: float) -> str:
    lines = []
    lines.append(f"\n=== Realtime Snapshot t={t:.0f}s ===")
    for floor in range(num_floors, -1, -1):
        row = [f"{floor:>2}|"]
        for e in elevators:
            marker = "   "
            if int(round(e.current_floor)) == floor:
                state = "^" if e.direction == "UP" else ("v" if e.direction == "DOWN" else "=")
                marker = f"E{e.elevator_id}{state}"
            elif floor in e.stop_queue:
                marker = " . "
            row.append(f"{marker:>4}")
        lines.append(" ".join(row))
    lines.append("    " + " ".join([f"E{e.elevator_id}:q={len(e.stop_queue)} load={e.current_load}/{e.capacity}" for e in elevators]))
    return "\n".join(lines)
