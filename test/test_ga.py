import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random

from config import DIR_UP, DIR_IDLE
from elevator import Elevator
import ga


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def is_perm(values, baseline):
    return sorted(values) == sorted(baseline)


def run():
    random.seed(123)

    # 5a
    check(ga.fitness([], start_floor=0, direction=DIR_IDLE) == 0, "fitness empty")

    # 5b
    penalized = ga.fitness([5, 10, 3], 0, DIR_UP)
    smooth = ga.fitness([3, 5, 10], 0, DIR_UP)
    check(penalized < smooth, f"reversal should penalize: {penalized} !< {smooth}")

    # 5c
    check(ga.compute_total_distance([5, 10, 2], 0) == 18, "distance exact")

    # 5d
    pop = ga.generate_initial_population([1, 5, 8, 12], 30)
    check(len(pop) == 30, "population size")
    check(pop[0] == [1, 5, 8, 12], "first FCFS baseline")
    for c in pop:
        check(is_perm(c, [1, 5, 8, 12]), f"invalid chromosome {c}")

    # 5e
    p1 = [1, 5, 8, 12, 15]
    p2 = [15, 1, 12, 5, 8]
    for _ in range(50):
        child = ga.order_one_crossover(p1, p2)
        check(is_perm(child, p1), f"invalid OX child {child}")

    # 5f
    for _ in range(20):
        out = ga.swap_mutation([1, 5, 8, 12], mutation_rate=1.0)
        check(is_perm(out, [1, 5, 8, 12]), "mutation keeps permutation")
    unchanged = ga.swap_mutation([1, 5, 8, 12], mutation_rate=0.0)
    check(unchanged == [1, 5, 8, 12], "mutation 0 unchanged")

    # 5g
    stops = [1, 5, 8, 12]
    population = [random.sample(stops, len(stops)) for _ in range(10)]
    fitnesses = [ga.fitness(c, 0, DIR_IDLE) for c in population]
    for _ in range(100):
        selected = ga.tournament_selection(population, fitnesses, 4)
        check(is_perm(selected, stops), "tournament returns valid chromosome")

    # 5h
    e = Elevator(0, 20, 0)
    route, imp = ga.optimize_route(e, verbose=False)
    check(route == [] and imp == 0.0, "optimize_route empty")

    e1 = Elevator(0, 20, 0)
    e1.stop_queue = [6]
    route1, imp1 = ga.optimize_route(e1, verbose=False)
    check(route1 == [6] and imp1 == 0.0, f"single stop should skip GA got {route1}, {imp1}")

    # 5i
    e2 = Elevator(0, 20, 0)
    e2.stop_queue = [15, 2, 8, 5, 12]
    fcfs_distance = ga.compute_total_distance([15, 2, 8, 5, 12], 0)
    route2, _ = ga.optimize_route(e2, verbose=False)
    dist2 = ga.compute_total_distance(route2, 0)
    check(dist2 <= fcfs_distance, f"optimized dist {dist2} <= fcfs {fcfs_distance}")
    check(e2.stop_queue == route2, "elevator queue updated")

    # 5j
    e3 = Elevator(0, 20, 0)
    original = [15, 2, 8, 5, 12]
    e3.stop_queue = original[:]
    r_a, _ = ga.optimize_route(e3, verbose=False)
    fit_fcfs = ga.fitness(original, 0, DIR_IDLE)
    fit_a = ga.fitness(r_a, 0, DIR_IDLE)

    e4 = Elevator(0, 20, 0)
    e4.stop_queue = original[:]
    r_b, _ = ga.optimize_route(e4, verbose=False)
    fit_b = ga.fitness(r_b, 0, DIR_IDLE)

    check(fit_a >= fit_fcfs and fit_b >= fit_fcfs, "both runs >= FCFS fitness")

    print(f"BLOCK 5 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
