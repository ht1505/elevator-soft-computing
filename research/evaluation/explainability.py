from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from research.core.models import DispatchDecision


def serialize_decisions(decisions: List[DispatchDecision], limit: int = 200) -> List[Dict]:
    payload = []
    for d in decisions[:limit]:
        payload.append(
            {
                "request_id": d.request_id,
                "selected_elevator": d.selected_elevator,
                "score": d.score,
                "traffic_mode": d.explanation.traffic_mode,
                "memberships": d.explanation.memberships,
                "rule_activations": [asdict(r) for r in d.explanation.rule_activations],
            }
        )
    return payload
