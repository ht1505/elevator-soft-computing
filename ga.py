"""
ga.py — Global Genetic Algorithm Engine for Multi-Elevator Route Optimization.

Uses one chromosome for all cars jointly:
    - Chromosome gene: (elevator_id, floor)
    - Order-1 Crossover (OX1) on the flat tuple list
    - Repair pass to preserve each car's own stop ownership/count
    - Same-car swap mutation
    - Tournament selection + elitism

Fitness is explicitly multi-objective:
    - Distance
    - Energy (with regenerative descent credit)
    - Passenger comfort (loaded reversals)
"""

import random
from collections import Counter
from config import (
        GA_POPULATION, GA_GENERATIONS, GA_CROSSOVER_RATE,
        GA_MUTATION_RATE, GA_TOURNAMENT_SIZE, GA_ELITISM_COUNT,
        GA_WEIGHT_DISTANCE, GA_WEIGHT_ENERGY, GA_WEIGHT_COMFORT,
        GA_REGEN_FACTOR_DESCENT, GA_ACCEL_PENALTY,
        ENERGY_PER_FLOOR, ENERGY_LOAD_FACTOR, ENERGY_REGEN_FACTOR,
        DIR_UP, DIR_DOWN, DIR_IDLE
)


def fitness(chromosome, start_floor=0, direction=DIR_IDLE):
    """Legacy single-route fitness: lower distance/reversals => higher fitness."""
    if not chromosome:
        return 0

    current = start_floor
    total_distance = 0
    reversals = 0
    prev_dir = direction if direction in (DIR_UP, DIR_DOWN) else None

    for stop in chromosome:
        delta = stop - current
        total_distance += abs(delta)
        if delta > 0:
            leg_dir = DIR_UP
        elif delta < 0:
            leg_dir = DIR_DOWN
        else:
            leg_dir = prev_dir

        if prev_dir in (DIR_UP, DIR_DOWN) and leg_dir in (DIR_UP, DIR_DOWN) and leg_dir != prev_dir:
            reversals += 1

        prev_dir = leg_dir
        current = stop

    penalty = reversals * GA_ACCEL_PENALTY
    return -(total_distance + penalty)


def generate_initial_population(stops, population_size):
    """Legacy helper: returns permutations with FCFS chromosome first."""
    stops = list(stops)
    if not stops:
        return [[] for _ in range(population_size)]

    population = [stops[:]]
    for _ in range(max(0, population_size - 1)):
        candidate = stops[:]
        random.shuffle(candidate)
        population.append(candidate)
    return population


def order_one_crossover(parent1, parent2):
    """Legacy OX1 crossover for simple floor chromosomes."""
    size = len(parent1)
    if size <= 1:
        return list(parent1)

    cut1, cut2 = sorted(random.sample(range(size), 2))
    child = [None] * size
    child[cut1:cut2 + 1] = parent1[cut1:cut2 + 1]

    present = Counter(child[cut1:cut2 + 1])
    fill = []
    for gene in parent2:
        if present[gene] > 0:
            present[gene] -= 1
        else:
            fill.append(gene)

    fi = 0
    for i in range(size):
        if child[i] is None:
            child[i] = fill[fi]
            fi += 1

    return child


def _compute_route_metrics(elevator, route):
    """
    Compute distance, energy, and comfort metrics for one elevator route.

    Energy model:
      - Upward: +ENERGY_PER_FLOOR * (1 + ENERGY_LOAD_FACTOR * load)
      - Downward: -ENERGY_REGEN_FACTOR * GA_REGEN_FACTOR_DESCENT
      - Reversal: +GA_ACCEL_PENALTY

    Comfort model:
      - Add elevator load for every direction reversal
    """
    current = int(round(elevator.current_floor))
    load = float(getattr(elevator, "current_load", 0))
    prev_dir = elevator.direction if elevator.direction in (DIR_UP, DIR_DOWN) else None

    distance = 0.0
    energy = 0.0
    comfort = 0.0

    for stop in route:
        step = int(stop) - current
        leg = abs(step)
        distance += leg

        if step > 0:
            leg_dir = DIR_UP
            energy += leg * ENERGY_PER_FLOOR * (1.0 + ENERGY_LOAD_FACTOR * load)
        elif step < 0:
            leg_dir = DIR_DOWN
            energy -= leg * ENERGY_REGEN_FACTOR * GA_REGEN_FACTOR_DESCENT
        else:
            leg_dir = None

        if leg_dir is not None and prev_dir in (DIR_UP, DIR_DOWN) and leg_dir != prev_dir:
            energy += GA_ACCEL_PENALTY
            comfort += load

        if leg_dir is not None:
            prev_dir = leg_dir

        current = int(stop)

    return distance, energy, comfort


def multi_fitness(assignment, elevators):
    """
    Joint multi-objective fitness over all elevator routes.

    Args:
        assignment (dict): dict[elevator_id -> list_of_floors]
        elevators (list): List of Elevator objects.

    Returns:
        float: Negative weighted objective (higher is better).
    """
    elev_by_id = {e.id: e for e in elevators}

    dist_total = 0.0
    energy_total = 0.0
    comfort_total = 0.0

    for eid, route in assignment.items():
        elev = elev_by_id.get(eid)
        if elev is None:
            continue
        dist, energy, comfort = _compute_route_metrics(elev, route)
        dist_total += dist
        energy_total += energy
        comfort_total += comfort

    weighted = (
        GA_WEIGHT_DISTANCE * dist_total
        + GA_WEIGHT_ENERGY * energy_total
        + GA_WEIGHT_COMFORT * comfort_total
    )
    return -weighted


def compute_total_distance(chromosome, start_floor):
    """
    Compute total travel distance for a route (for reporting).

    Args:
        chromosome (list): Ordered floor stops.
        start_floor (int): Starting floor.

    Returns:
        int: Total distance in floors.
    """
    if not chromosome:
        return 0
    total = 0
    current = start_floor
    for floor in chromosome:
        total += abs(floor - current)
        current = floor
    return total


def _encode_assignment(assignment, ordered_ids=None):
    if ordered_ids is None:
        ordered_ids = sorted(assignment.keys())
    chromosome = []
    for eid in ordered_ids:
        for floor in assignment.get(eid, []):
            chromosome.append((eid, int(floor)))
    return chromosome


def encode_chromosome(elevators):
    """Flatten all elevator queues into [(elevator_id, floor), ...]."""
    ordered = sorted(elevators, key=lambda e: e.id)
    assignment = {e.id: list(e.stop_queue) for e in ordered}
    return _encode_assignment(assignment, [e.id for e in ordered])


def decode_chromosome(chromosome, num_elevators):
    """Reconstruct dict[elevator_id -> route] from a flat chromosome."""
    assignment = {eid: [] for eid in range(max(0, num_elevators))}
    for eid, floor in chromosome:
        assignment.setdefault(eid, []).append(int(floor))
    return assignment


def _generate_initial_population(elevators, pop_size):
    ordered = sorted(elevators, key=lambda e: e.id)
    base_assignment = {e.id: list(e.stop_queue) for e in ordered}
    population = [_encode_assignment(base_assignment, [e.id for e in ordered])]

    for _ in range(pop_size - 1):
        candidate = {eid: list(route) for eid, route in base_assignment.items()}
        for eid in candidate:
            random.shuffle(candidate[eid])
        population.append(_encode_assignment(candidate, [e.id for e in ordered]))

    return population


def tournament_selection(population, fitnesses, tournament_size):
    """
    Select a parent using tournament selection.

    Randomly pick tournament_size chromosomes and return the fittest.

    Args:
        population (list): List of chromosomes.
        fitnesses (list): Corresponding fitness values.
        tournament_size (int): Number of contenders.

    Returns:
        list: Selected chromosome (copy).
    """
    # Pick random indices for the tournament
    indices = random.sample(range(len(population)), min(tournament_size, len(population)))

    # Find the best among the contenders
    best_idx = max(indices, key=lambda i: fitnesses[i])
    return list(population[best_idx])  # return a copy


def _repair(child, template):
    """Repair child so tuple multiset matches template exactly."""
    over = Counter(child) - Counter(template)
    under = Counter(template) - Counter(child)

    missing = []
    for gene, count in under.items():
        missing.extend([gene] * count)

    if not missing:
        return child

    missing_idx = 0
    for i, gene in enumerate(child):
        if missing_idx >= len(missing):
            break
        if over[gene] > 0:
            child[i] = missing[missing_idx]
            missing_idx += 1
            over[gene] -= 1

    return child


def global_crossover(parent_a, parent_b, num_elevators):
    """
    OX1 crossover on flat tuple chromosome + repair for per-car ownership.

    Swapping is allowed at flat level, but repair guarantees each car keeps
    exactly its own stops/counts from the template chromosome.
    """
    size = len(parent_a)
    if size <= 2:
        return list(parent_a)

    cut1, cut2 = sorted(random.sample(range(size), 2))
    child = [None] * size
    child[cut1:cut2 + 1] = parent_a[cut1:cut2 + 1]

    segment_counter = Counter(child[cut1:cut2 + 1])
    fill_values = []
    for gene in parent_b:
        if segment_counter[gene] > 0:
            segment_counter[gene] -= 1
        else:
            fill_values.append(gene)

    fill_idx = 0
    for i in range(size):
        if child[i] is None:
            child[i] = fill_values[fill_idx]
            fill_idx += 1

    return _repair(child, parent_a)


def swap_mutation(chromosome, mutation_rate):
    """Swap mutation constrained to same-elevator genes."""
    if random.random() >= mutation_rate or len(chromosome) < 2:
        return chromosome

    # Legacy scalar chromosome support: [floor, floor, ...]
    if not isinstance(chromosome[0], tuple):
        i, j = random.sample(range(len(chromosome)), 2)
        chromosome[i], chromosome[j] = chromosome[j], chromosome[i]
        return chromosome

    positions_by_eid = {}
    for idx, (eid, _floor) in enumerate(chromosome):
        positions_by_eid.setdefault(eid, []).append(idx)

    eligible = [eid for eid, pos in positions_by_eid.items() if len(pos) >= 2]
    if not eligible:
        return chromosome

    chosen = random.choice(eligible)
    i, j = random.sample(positions_by_eid[chosen], 2)
    chromosome[i], chromosome[j] = chromosome[j], chromosome[i]
    return chromosome


def _metrics_for_assignment(assignment, elevators):
    elev_by_id = {e.id: e for e in elevators}
    per_car = {}
    total_distance = 0.0
    total_energy = 0.0
    total_comfort = 0.0

    for eid, route in assignment.items():
        elev = elev_by_id.get(eid)
        if elev is None:
            continue
        dist, energy, comfort = _compute_route_metrics(elev, route)
        per_car[eid] = {"distance": dist, "energy": energy, "comfort": comfort}
        total_distance += dist
        total_energy += energy
        total_comfort += comfort

    return {
        "distance": total_distance,
        "energy": total_energy,
        "comfort": total_comfort,
        "per_car": per_car,
    }


def optimize_all_routes(elevators, verbose=True):
    """
    Optimize all elevator routes jointly in one GA run.

    Returns:
        tuple: (best_assignment, improvement_pct)
    """
    if not elevators:
        return {}, 0.0

    ordered = sorted(elevators, key=lambda e: e.id)
    num_elevators = len(ordered)

    base_assignment = {e.id: list(e.stop_queue) for e in ordered}
    total_stops = sum(len(route) for route in base_assignment.values())

    if total_stops <= 1:
        if verbose:
            print("  Global GA: trivial route set (<=1 total stop) — skipped.")
        return base_assignment, 0.0

    baseline = _metrics_for_assignment(base_assignment, ordered)
    population = _generate_initial_population(ordered, GA_POPULATION)

    best_ever = None
    best_ever_fitness = float("-inf")

    if verbose:
        print("\n  Global GA optimizing all elevator routes...")

    for gen in range(GA_GENERATIONS):
        decoded = [decode_chromosome(ch, num_elevators) for ch in population]
        fitnesses = [multi_fitness(assign, ordered) for assign in decoded]

        gen_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        gen_best_fitness = fitnesses[gen_best_idx]

        if gen_best_fitness > best_ever_fitness:
            best_ever_fitness = gen_best_fitness
            best_ever = list(population[gen_best_idx])

        if verbose and gen in (0, GA_GENERATIONS // 3, 2 * GA_GENERATIONS // 3):
            print(f"    Gen {gen:<4} Best fitness: {gen_best_fitness:.3f}")

        new_population = []
        sorted_indices = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)
        for i in range(min(GA_ELITISM_COUNT, len(sorted_indices))):
            new_population.append(list(population[sorted_indices[i]]))

        while len(new_population) < GA_POPULATION:
            parent_a = tournament_selection(population, fitnesses, GA_TOURNAMENT_SIZE)
            parent_b = tournament_selection(population, fitnesses, GA_TOURNAMENT_SIZE)

            if random.random() < GA_CROSSOVER_RATE:
                child = global_crossover(parent_a, parent_b, num_elevators)
            else:
                child = list(parent_a)

            child = swap_mutation(child, GA_MUTATION_RATE)
            child = _repair(child, population[0])
            new_population.append(child)

        population = new_population

    final_decoded = [decode_chromosome(ch, num_elevators) for ch in population]
    final_fitnesses = [multi_fitness(assign, ordered) for assign in final_decoded]
    final_best_idx = max(range(len(final_fitnesses)), key=lambda i: final_fitnesses[i])
    final_best = population[final_best_idx]

    if multi_fitness(decode_chromosome(final_best, num_elevators), ordered) > best_ever_fitness:
        best_ever = final_best

    best_assignment = decode_chromosome(best_ever, num_elevators)

    for elev in ordered:
        elev.set_route(best_assignment.get(elev.id, []))

    optimized = _metrics_for_assignment(best_assignment, ordered)
    if baseline["distance"] > 0:
        improvement = ((baseline["distance"] - optimized["distance"]) / baseline["distance"]) * 100.0
    else:
        improvement = 0.0

    if verbose:
        print("    Per-car global GA breakdown (vs FCFS):")
        for elev in ordered:
            eid = elev.id
            base_car = baseline["per_car"].get(eid, {"distance": 0.0, "energy": 0.0})
            opt_car = optimized["per_car"].get(eid, {"distance": 0.0, "energy": 0.0})
            dist_saved = base_car["distance"] - opt_car["distance"]
            energy_delta = opt_car["energy"] - base_car["energy"]
            print(
                f"      E{eid}: route {best_assignment.get(eid, [])} | "
                f"distance Δ {dist_saved:+.1f} floors | energy Δ {energy_delta:+.2f}"
            )

        print(
            f"    Fleet totals: distance {baseline['distance']:.1f} -> {optimized['distance']:.1f} "
            f"({improvement:+.1f}%)"
        )
        print(
            f"    Fleet energy: {baseline['energy']:.2f} -> {optimized['energy']:.2f} "
            f"(Δ {optimized['energy'] - baseline['energy']:+.2f})"
        )

    return best_assignment, improvement


def optimize_route(elevator, verbose=True):
    """Legacy compatibility wrapper around global optimizer for one car."""
    best_assignment, improvement = optimize_all_routes([elevator], verbose=verbose)
    return best_assignment.get(elevator.id, []), improvement
