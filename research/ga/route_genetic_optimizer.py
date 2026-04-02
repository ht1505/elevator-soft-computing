from __future__ import annotations

import random
from typing import List

from research.core.config import RouteGAConfig


def _route_cost(start_floor: float, route: List[int], reversal_penalty: float) -> float:
    if not route:
        return 0.0

    current = start_floor
    cost = 0.0
    prev_dir = 0
    for stop in route:
        delta = stop - current
        dist = abs(delta)
        direction = 1 if delta > 0 else (-1 if delta < 0 else 0)
        reversal_cost = reversal_penalty if prev_dir != 0 and direction != 0 and direction != prev_dir else 0.0
        cost += dist + reversal_cost
        prev_dir = direction if direction != 0 else prev_dir
        current = stop
    return cost


class RouteGeneticOptimizer:
    def __init__(self, seed: int = 42, config: RouteGAConfig | None = None):
        self.rng = random.Random(seed)
        self.config = config or RouteGAConfig()

    def optimize(self, start_floor: float, stops: List[int]) -> List[int]:
        unique = list(dict.fromkeys(stops))
        if len(unique) < self.config.min_route_length_for_optimization:
            return unique

        def init_individual() -> List[int]:
            ind = list(unique)
            self.rng.shuffle(ind)
            return ind

        def crossover(a: List[int], b: List[int]) -> List[int]:
            if len(a) < 2 or len(b) < 2:
                return list(a)
            i = self.rng.randint(0, len(a) - 2)
            if i + 1 > len(a) - 1:
                return list(a)
            j = self.rng.randint(i + 1, len(a) - 1)
            mid = a[i:j]
            rest = [x for x in b if x not in mid]
            return rest[:i] + mid + rest[i:]

        def mutate(ind: List[int]) -> List[int]:
            out = list(ind)
            if self.rng.random() < self.config.mutation_rate:
                i = self.rng.randrange(len(out))
                j = self.rng.randrange(len(out))
                out[i], out[j] = out[j], out[i]
            return out

        pop = [init_individual() for _ in range(self.config.population)]

        for _ in range(self.config.generations):
            ranked = sorted(pop, key=lambda r: _route_cost(start_floor, r, self.config.reversal_penalty))
            next_pop = ranked[: self.config.elites]
            selection_pool = max(2, self.config.population // max(1, self.config.selection_pool_divisor))
            while len(next_pop) < self.config.population:
                p1 = ranked[self.rng.randrange(selection_pool)]
                p2 = ranked[self.rng.randrange(selection_pool)]
                child = crossover(p1, p2)
                next_pop.append(mutate(child))
            pop = next_pop

        return min(pop, key=lambda r: _route_cost(start_floor, r, self.config.reversal_penalty))
