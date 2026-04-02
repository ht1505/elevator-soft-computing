from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import variance
from typing import List, Sequence, Tuple

from research.core.config import FuzzyGAParamSpace
from research.core.models import FitnessTerms


@dataclass
class GAHyperParams:
    population: int = 30
    generations: int = 50
    crossover_rate: float = 0.85
    mutation_rate: float = 0.15
    elitism: int = 2


class FuzzyParameterGA:
    """Optimizes fuzzy memberships and rule weights for multi-objective performance."""

    def __init__(self, seed: int = 42, param_space: FuzzyGAParamSpace | None = None):
        self.rng = random.Random(seed)
        self.history: List[float] = []
        self.param_space = param_space or FuzzyGAParamSpace()

    def chromosome_length(self, rule_count: int) -> int:
        return self.param_space.triangle_gene_count + rule_count

    def _init_individual(self, length: int) -> List[float]:
        genes = []
        for i in range(length):
            if i < self.param_space.triangle_gene_count:
                genes.append(self.rng.uniform(self.param_space.triangle_min, self.param_space.triangle_max))
            else:
                genes.append(self.rng.uniform(self.param_space.rule_weight_min, self.param_space.rule_weight_max))
        return genes

    def _crossover(self, a: Sequence[float], b: Sequence[float], crossover_rate: float) -> Tuple[List[float], List[float]]:
        if self.rng.random() > crossover_rate:
            return list(a), list(b)
        cut = self.rng.randint(1, len(a) - 2)
        c1 = list(a[:cut]) + list(b[cut:])
        c2 = list(b[:cut]) + list(a[cut:])
        return c1, c2

    def _mutate(self, genes: List[float], mutation_rate: float) -> List[float]:
        out = list(genes)
        for i in range(len(out)):
            if self.rng.random() < mutation_rate:
                sigma = self.param_space.mutate_sigma_triangle if i < self.param_space.triangle_gene_count else self.param_space.mutate_sigma_rule
                out[i] += self.rng.gauss(0.0, sigma)
        return out

    def _tournament(self, pop: List[List[float]], fit: List[float], k: int) -> List[float]:
        idxs = [self.rng.randrange(len(pop)) for _ in range(k)]
        best = max(idxs, key=lambda idx: fit[idx])
        return pop[best]

    @staticmethod
    def score_terms(waits: List[float], energy: float, overload_count: int) -> FitnessTerms:
        avg_wait = sum(waits) / len(waits) if waits else 0.0
        var = variance(waits) if len(waits) > 1 else 0.0
        return FitnessTerms(avg_wait=avg_wait, energy=energy, variance=var, overload_penalty=float(overload_count))

    def optimize(
        self,
        rule_count: int,
        evaluator,
        alpha: float,
        beta: float,
        gamma: float,
        params: GAHyperParams,
    ) -> Tuple[List[float], float]:
        length = self.chromosome_length(rule_count)
        pop = [self._init_individual(length) for _ in range(params.population)]

        best_ind = pop[0]
        best_fit = float("-inf")

        for _g in range(params.generations):
            fit = []
            for ind in pop:
                terms = evaluator(ind)
                fitness = terms.objective(alpha, beta, gamma)
                fit.append(fitness)
                if fitness > best_fit:
                    best_fit = fitness
                    best_ind = list(ind)

            self.history.append(best_fit)
            ranked = sorted(range(len(pop)), key=lambda i: fit[i], reverse=True)
            next_pop = [pop[i] for i in ranked[: params.elitism]]

            while len(next_pop) < params.population:
                p1 = self._tournament(pop, fit, self.param_space.tournament_k)
                p2 = self._tournament(pop, fit, self.param_space.tournament_k)
                c1, c2 = self._crossover(p1, p2, params.crossover_rate)
                next_pop.append(self._mutate(c1, params.mutation_rate))
                if len(next_pop) < params.population:
                    next_pop.append(self._mutate(c2, params.mutation_rate))
            pop = next_pop

        return best_ind, best_fit
