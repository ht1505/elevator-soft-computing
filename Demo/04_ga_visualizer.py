import random
import copy
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


BLUE = "#2196F3"
GREEN = "#4CAF50"
ORANGE = "#FF9800"
RED = "#F44336"
PURPLE = "#9C27B0"

POP_SIZE = 30
GENERATIONS = 75
CROSSOVER_RATE = 0.85
MUTATION_RATE = 0.12


def route_components(start_floor, route):
    current = start_floor
    distance = 0.0
    energy = 0.0
    comfort = 0.0
    prev_move = 0

    for stop in route:
        move = stop - current
        dist = abs(move)
        distance += dist

        if move > 0:
            energy += dist * 1.2
            curr_dir = 1
        elif move < 0:
            energy += dist * 0.7
            curr_dir = -1
        else:
            curr_dir = prev_move

        if prev_move != 0 and curr_dir != 0 and prev_move != curr_dir:
            comfort += 3.0

        prev_move = curr_dir if curr_dir != 0 else prev_move
        current = stop

    weighted = 0.40 * distance + 0.35 * energy + 0.25 * comfort
    return distance, energy, comfort, weighted


def fitness(start_floor, route):
    return -route_components(start_floor, route)[3]


def tournament_selection(population, start_floor, k=4):
    picks = random.sample(population, k)
    picks.sort(key=lambda r: fitness(start_floor, r), reverse=True)
    return copy.deepcopy(picks[0])


def ox1(parent1, parent2):
    n = len(parent1)
    i, j = sorted(random.sample(range(n), 2))
    child = [None] * n
    child[i : j + 1] = parent1[i : j + 1]

    fill_vals = [g for g in parent2 if g not in child]
    fill_idx = [idx for idx in range(n) if child[idx] is None]
    for idx, val in zip(fill_idx, fill_vals):
        child[idx] = val
    return child


def mutate(route):
    i, j = random.sample(range(len(route)), 2)
    route[i], route[j] = route[j], route[i]


def run_ga(start_floor, stops):
    population = [random.sample(stops, len(stops)) for _ in range(POP_SIZE)]
    best_curve = []
    avg_curve = []

    for _ in range(GENERATIONS):
        scored = sorted(population, key=lambda r: fitness(start_floor, r), reverse=True)
        best_curve.append(fitness(start_floor, scored[0]))
        avg_curve.append(np.mean([fitness(start_floor, r) for r in scored]))

        next_gen = [copy.deepcopy(scored[0]), copy.deepcopy(scored[1])]
        while len(next_gen) < POP_SIZE:
            p1 = tournament_selection(scored, start_floor)
            p2 = tournament_selection(scored, start_floor)

            if random.random() < CROSSOVER_RATE:
                child = ox1(p1, p2)
            else:
                child = copy.deepcopy(p1)

            if random.random() < MUTATION_RATE:
                mutate(child)
            next_gen.append(child)

        population = next_gen

    best = max(population, key=lambda r: fitness(start_floor, r))
    return best, np.array(best_curve), np.array(avg_curve)


def mean_random_components(start_floor, stops, samples=300):
    d_vals, e_vals, c_vals = [], [], []
    for _ in range(samples):
        route = random.sample(stops, len(stops))
        d, e, c, _ = route_components(start_floor, route)
        d_vals.append(d)
        e_vals.append(e)
        c_vals.append(c)
    return float(np.mean(d_vals)), float(np.mean(e_vals)), float(np.mean(c_vals))


def nearest_neighbor_route(start_floor, stops):
    rem = stops[:]
    route = []
    current = start_floor
    while rem:
        nxt = min(rem, key=lambda f: abs(f - current))
        route.append(nxt)
        rem.remove(nxt)
        current = nxt
    return route


def draw_building_paths(ax, x_base, start_floor, route, color, label):
    ax.plot([x_base, x_base], [1, 10], color="#9E9E9E", lw=5, alpha=0.6)
    ax.scatter([x_base], [start_floor], color=color, s=80, zorder=4)
    ax.text(x_base, 10.25, label, ha="center", fontsize=9, fontweight="bold")

    y_points = [start_floor] + route
    x_points = [x_base + ((-1) ** i) * 0.07 for i in range(len(y_points))]
    ax.plot(x_points, y_points, color=color, lw=2.2, marker="o", ms=5)

    for idx, stop in enumerate(route, start=1):
        ax.text(x_base + 0.13, stop, str(idx), fontsize=8, color=color, fontweight="bold")


def main():
    random.seed(42)
    np.random.seed(42)
    plt.style.use("seaborn-v0_8-whitegrid")

    # Scenario
    e1_start, e1_stops = 5, [2, 4, 7, 9]
    e2_start, e2_stops = 3, [1, 6, 8, 10]

    fcfs_e1 = sorted(e1_stops)
    fcfs_e2 = sorted(e2_stops)

    ga_e1, ga_curve_e1, ga_avg_e1 = run_ga(e1_start, e1_stops)
    ga_e2, ga_curve_e2, ga_avg_e2 = run_ga(e2_start, e2_stops)

    fcfs_dist = route_components(e1_start, fcfs_e1)[0] + route_components(e2_start, fcfs_e2)[0]
    ga_dist = route_components(e1_start, ga_e1)[0] + route_components(e2_start, ga_e2)[0]
    improve = (fcfs_dist - ga_dist) / fcfs_dist * 100

    fig, axes = plt.subplots(2, 2, figsize=(18, 11), facecolor="#FFFFFF")

    # Panel A: Route diagram
    ax = axes[0, 0]
    ax.set_title("A) Initial vs Optimized Routes", fontsize=14, fontweight="bold")
    ax.set_xlim(-0.4, 3.7)
    ax.set_ylim(0.8, 10.6)
    ax.set_ylabel("Floor", fontsize=11)
    ax.set_xticks([])

    for floor in range(1, 11):
        ax.axhline(floor, color="#EEEEEE", lw=0.8, zorder=0)

    draw_building_paths(ax, 0.6, e1_start, fcfs_e1, BLUE, "FCFS E1")
    draw_building_paths(ax, 1.4, e2_start, fcfs_e2, ORANGE, "FCFS E2")
    draw_building_paths(ax, 2.4, e1_start, ga_e1, BLUE, "GA E1")
    draw_building_paths(ax, 3.2, e2_start, ga_e2, ORANGE, "GA E2")

    ax.text(1.0, 10.4, f"Total Distance: {fcfs_dist:.0f} floors", ha="center", fontsize=10, color=RED, fontweight="bold")
    ax.text(2.8, 10.4, f"Optimized: {ga_dist:.0f} floors", ha="center", fontsize=10, color=GREEN, fontweight="bold")
    ax.text(2.05, 9.8, f"Improvement: {improve:.1f}%", ha="center", fontsize=10, color=PURPLE, fontweight="bold")

    # Panel B: Convergence curve from actual GA runs.
    ax = axes[0, 1]
    gens = np.arange(GENERATIONS)
    best_curve = ga_curve_e1 + ga_curve_e2
    avg_curve = ga_avg_e1 + ga_avg_e2

    ax.plot(gens, best_curve, color=BLUE, lw=2.2, label="Best Fitness")
    ax.plot(gens, avg_curve, color=ORANGE, lw=2.0, ls="--", label="Average Fitness")
    ax.set_title("B) GA Fitness Convergence (75 Generations)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Generation", fontsize=11)
    ax.set_ylabel("Fitness (higher is better)", fontsize=11)
    ax.legend(fontsize=10)

    for g, label in [(0, "Random start"), (15, "Rapid improvement"), (50, "Near convergence")]:
        ax.scatter([g], [best_curve[g]], color=PURPLE, s=50, zorder=4)
        ax.annotate(label, xy=(g, best_curve[g]), xytext=(g + 4, best_curve[g] + 3), arrowprops=dict(arrowstyle="->", lw=1), fontsize=9)

    # Panel C: Chromosome and OX1
    ax = axes[1, 0]
    ax.set_title("C) Order-1 (OX1) Crossover Operation", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    parent1 = [("E1", f) for f in random.sample(e1_stops, len(e1_stops))] + [("E2", f) for f in random.sample(e2_stops, len(e2_stops))]
    parent2 = [("E1", f) for f in random.sample(e1_stops, len(e1_stops))] + [("E2", f) for f in random.sample(e2_stops, len(e2_stops))]
    random.shuffle(parent1)
    random.shuffle(parent2)
    c1, c2 = 2, 5
    child = [None] * len(parent1)
    child[c1 : c2 + 1] = parent1[c1 : c2 + 1]
    fill = [g for g in parent2 if g not in child]
    idxs = [i for i, g in enumerate(child) if g is None]
    for i, g in zip(idxs, fill):
        child[i] = g

    rows = [("Parent 1", parent1, 3.0), ("Parent 2", parent2, 2.0), ("Child", child, 1.0)]
    for row_name, genes, y in rows:
        ax.text(0.1, y + 0.15, row_name, fontsize=10, fontweight="bold")
        for i, gene in enumerate(genes):
            x = 1 + i * 1.05
            g_color = BLUE if gene[0] == "E1" else ORANGE
            bg = "#E1F5FE" if (row_name == "Parent 1" and c1 <= i <= c2) else "white"
            rect = Rectangle((x, y - 0.2), 0.95, 0.5, fc=bg, ec="black", lw=0.8)
            ax.add_patch(rect)
            ax.text(x + 0.475, y + 0.03, f"{gene[0]}:{gene[1]}", ha="center", va="center", fontsize=8, color=g_color, fontweight="bold")

    ax.text(1.0, 0.35, f"Crossover segment in Parent 1: indices {c1} to {c2}", fontsize=9, color=PURPLE, fontweight="bold")

    # Panel D: Multi-objective breakdown
    ax = axes[1, 1]
    strategies = ["Random Order", "FCFS", "Greedy Nearest", "GA Optimized"]

    rd1, re1, rc1 = mean_random_components(e1_start, e1_stops)
    rd2, re2, rc2 = mean_random_components(e2_start, e2_stops)
    greedy_e1 = nearest_neighbor_route(e1_start, e1_stops)
    greedy_e2 = nearest_neighbor_route(e2_start, e2_stops)

    route_summaries = [
        (rd1 + rd2, re1 + re2, rc1 + rc2),
    ]
    for r1, r2 in [(fcfs_e1, fcfs_e2), (greedy_e1, greedy_e2), (ga_e1, ga_e2)]:
        d1, e1, c1v, _ = route_components(e1_start, r1)
        d2, e2, c2v, _ = route_components(e2_start, r2)
        route_summaries.append((d1 + d2, e1 + e2, c1v + c2v))

    dist_c = []
    en_c = []
    comf_c = []
    totals = []
    for d_raw, e_raw, c_raw in route_summaries:
        d = 0.40 * d_raw
        e = 0.35 * e_raw
        c = 0.25 * c_raw
        dist_c.append(d)
        en_c.append(e)
        comf_c.append(c)
        totals.append(d + e + c)

    x = np.arange(len(strategies))
    ax.bar(x, dist_c, color=BLUE, label="Distance (40%)")
    ax.bar(x, en_c, bottom=dist_c, color=ORANGE, label="Energy (35%)")
    ax.bar(x, comf_c, bottom=np.array(dist_c) + np.array(en_c), color=GREEN, label="Comfort (25%)")
    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=15)
    ax.set_ylabel("Weighted Cost (Lower is Better)", fontsize=11)
    ax.set_title("D) Multi-Objective Fitness Components", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)

    for i, t in enumerate(totals):
        ax.text(i, t + 0.5, f"{t:.1f}", ha="center", fontsize=9)

    imp_vs_fcfs = (totals[1] - totals[3]) / totals[1] * 100
    ax.text(1.55, max(totals) + 2.0, f"GA improves total cost vs FCFS by {imp_vs_fcfs:.1f}%", color=PURPLE, fontsize=10, fontweight="bold")

    fig.suptitle("Genetic Algorithm - Route Optimization", fontsize=16, fontweight="bold")
    fig.text(
        0.5,
        0.01,
        "Smart Elevator Management System - Soft Computing Project",
        ha="center",
        fontsize=9,
        color="#616161",
    )
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    filename = "04_ga.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved: {filename}")
    plt.show()


if __name__ == "__main__":
    main()
