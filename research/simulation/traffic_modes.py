from __future__ import annotations

import random
from typing import Tuple


def sample_origin_destination(mode: str, num_floors: int, rng: random.Random) -> Tuple[int, str, int]:
    if mode == "peak_up":
        origin = 0 if rng.random() < 0.75 else rng.randint(0, num_floors)
        if origin >= num_floors:
            origin = max(0, num_floors - 1)
        dest = rng.randint(max(1, origin + 1), num_floors)
        return origin, "UP", dest
    if mode == "peak_down":
        origin = num_floors if rng.random() < 0.75 else rng.randint(0, num_floors)
        if origin <= 0:
            origin = 1
        dest = rng.randint(0, max(0, origin - 1))
        return origin, "DOWN", dest
    if mode == "inter_floor":
        origin = rng.randint(1, max(1, num_floors - 1))
        direction = rng.choice(["UP", "DOWN"])
        if direction == "UP":
            dest = rng.randint(origin + 1, num_floors)
        else:
            dest = rng.randint(0, origin - 1)
        return origin, direction, dest

    origin = rng.randint(0, num_floors)
    if origin == 0:
        return origin, "UP", rng.randint(1, num_floors)
    if origin == num_floors:
        return origin, "DOWN", rng.randint(0, num_floors - 1)

    direction = rng.choice(["UP", "DOWN"])
    if direction == "UP":
        return origin, direction, rng.randint(origin + 1, num_floors)
    return origin, direction, rng.randint(0, origin - 1)
