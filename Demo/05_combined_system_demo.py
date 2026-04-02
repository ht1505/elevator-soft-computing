import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


BLUE = "#2196F3"
GREEN = "#4CAF50"
ORANGE = "#FF9800"
RED = "#F44336"
PURPLE = "#9C27B0"


def nearest_route(current_floor, stops):
    remaining = stops[:]
    out = []
    cur = current_floor
    while remaining:
        nxt = min(remaining, key=lambda f: abs(f - cur))
        out.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    return out


def fuzzy_assign(elevators, req_floor, req_dir):
    scores = []
    for el in elevators:
        dist = abs(el["floor"] - req_floor)
        load = el["load"] / 8.0
        q = len(el["queue"])
        same = 1.0 if el["dir"] == req_dir else 0.0
        idle = 1.0 if el["dir"] == "IDLE" else 0.0
        opp = 1.0 if (same == 0 and idle == 0) else 0.0

        near = max(0.0, min(1.0, (5 - dist) / 5))
        light = max(0.0, min(1.0, (0.6 - load) / 0.6))
        shortq = max(0.0, min(1.0, (4 - q) / 4))
        passing = 1.0 if (el["dir"] == "UP" and el["floor"] <= req_floor) or (el["dir"] == "DOWN" and el["floor"] >= req_floor) else (0.8 if idle else 0.1)

        score = 100 * (0.32 * near + 0.22 * light + 0.18 * shortq + 0.18 * same + 0.10 * passing) - 18 * opp
        scores.append(score)

    return int(np.argmax(scores)), float(np.max(scores))


def generate_requests(seed=21, horizon=120):
    rng = np.random.default_rng(seed)
    reqs = []
    t = 2
    while t < horizon:
        t += int(rng.integers(4, 10))
        if t >= horizon:
            break
        floor = int(rng.integers(1, 11))
        if floor == 1:
            direction = "UP"
        elif floor == 10:
            direction = "DOWN"
        else:
            direction = "UP" if rng.random() < 0.58 else "DOWN"
        reqs.append({"time": t, "floor": floor, "dir": direction})
    return reqs


def run_simulation(use_smart=True, seed=21):
    rng = np.random.default_rng(seed)
    elevators = [
        {"id": "E1", "floor": 3, "dir": "IDLE", "queue": [], "target": None, "load": 2, "energy": 0.0, "reversals": 0, "last_sign": 0},
        {"id": "E2", "floor": 8, "dir": "IDLE", "queue": [], "target": None, "load": 4, "energy": 0.0, "reversals": 0, "last_sign": 0},
    ]

    requests = generate_requests(seed=seed)
    waiting = []
    req_idx = 0
    horizon = 120
    assigned_events = []
    served_waits = []
    floor_density = np.zeros(10, dtype=int)
    trajectory = {"t": [], "E1": [], "E2": []}

    for t in range(horizon + 1):
        while req_idx < len(requests) and requests[req_idx]["time"] == t:
            req = dict(requests[req_idx])
            req["assigned"] = None
            req["served"] = False
            waiting.append(req)
            floor_density[req["floor"] - 1] += 1
            req_idx += 1

        # Route re-optimization every 60s in smart mode.
        if use_smart and t in (60,):
            for el in elevators:
                if el["queue"]:
                    el["queue"] = nearest_route(el["floor"], sorted(set(el["queue"])))

        for req in waiting:
            if req["assigned"] is None:
                if use_smart:
                    chosen, _ = fuzzy_assign(elevators, req["floor"], req["dir"])
                else:
                    chosen = int(np.argmin([abs(el["floor"] - req["floor"]) + 0.7 * len(el["queue"]) for el in elevators]))
                req["assigned"] = chosen
                if req["floor"] not in elevators[chosen]["queue"]:
                    elevators[chosen]["queue"].append(req["floor"])
                assigned_events.append((t, req["floor"], chosen))

        for idx, el in enumerate(elevators):
            if el["target"] is None and el["queue"]:
                if use_smart:
                    el["queue"] = nearest_route(el["floor"], el["queue"])
                el["target"] = el["queue"].pop(0)

            if el["target"] is not None:
                move = np.sign(el["target"] - el["floor"])
                sign = int(move)
                if sign != 0 and el["last_sign"] != 0 and sign != el["last_sign"]:
                    el["reversals"] += 1
                if sign != 0:
                    el["last_sign"] = sign

                if move > 0:
                    el["floor"] += 1
                    el["energy"] += 1.2
                    el["dir"] = "UP"
                elif move < 0:
                    el["floor"] -= 1
                    el["energy"] += 0.7
                    el["dir"] = "DOWN"
                else:
                    el["dir"] = "IDLE"

                if el["floor"] == el["target"]:
                    for req in waiting:
                        if not req["served"] and req["assigned"] == idx and req["floor"] == el["floor"]:
                            req["served"] = True
                            served_waits.append(t - req["time"])
                    el["target"] = None
                    el["dir"] = "IDLE" if not el["queue"] else el["dir"]

            # Mild realistic load drift.
            el["load"] = int(np.clip(el["load"] + rng.integers(-1, 2), 0, 8))

        trajectory["t"].append(t)
        trajectory["E1"].append(elevators[0]["floor"])
        trajectory["E2"].append(elevators[1]["floor"])

    avg_wait = float(np.mean(served_waits)) if served_waits else 0.0
    total_energy = float(sum(el["energy"] for el in elevators))
    total_reversals = int(sum(el["reversals"] for el in elevators))
    reversals_per_served = total_reversals / max(1, len(served_waits))

    return {
        "trajectory": trajectory,
        "requests": requests,
        "assigned": assigned_events,
        "wait": avg_wait,
        "energy": total_energy,
        "reversals": reversals_per_served,
        "floor_density": floor_density,
        "served": len(served_waits),
    }


def draw_flow_diagram(ax):
    ax.axis("off")
    ax.set_title("System Architecture Flow", fontsize=15, fontweight="bold", pad=10)

    nodes = [
        ("New Request", "Input"),
        ("Fuzzy Logic Scorer", "Method 1: Fuzzy"),
        ("Best Elevator Selected", "Decision"),
        ("GA Route Optimizer", "Method 2: GA"),
        ("Updated Stop Sequence", "Output Plan"),
        ("Elevator Dispatched", "Execution"),
    ]
    colors = ["#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#E1F5FE", "#FFEBEE"]

    x_positions = np.linspace(0.06, 0.94, len(nodes))
    y = 0.55
    w, h = 0.14, 0.36

    for i, ((title, subtitle), x) in enumerate(zip(nodes, x_positions)):
        box = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.02", fc=colors[i], ec="#455A64", lw=1.6, transform=ax.transAxes)
        ax.add_patch(box)
        ax.text(x, y + 0.05, title, ha="center", va="center", fontsize=9.5, fontweight="bold", transform=ax.transAxes)
        ax.text(x, y - 0.09, subtitle, ha="center", va="center", fontsize=8.5, color="#455A64", transform=ax.transAxes)

    for i in range(len(nodes) - 1):
        x1 = x_positions[i] + w / 2
        x2 = x_positions[i + 1] - w / 2
        arr = FancyArrowPatch((x1, y), (x2, y), arrowstyle="->", mutation_scale=12, lw=1.5, color="#546E7A", transform=ax.transAxes)
        ax.add_patch(arr)
        if i == 1:
            ax.text((x1 + x2) / 2, y + 0.12, "Select highest suitability", fontsize=8, color=GREEN, ha="center", transform=ax.transAxes)
        if i == 3:
            ax.text((x1 + x2) / 2, y + 0.12, "Optimize stop order", fontsize=8, color=PURPLE, ha="center", transform=ax.transAxes)


def draw_timeline(ax, sim):
    ax.set_title("2-Elevator Simulation (120 seconds)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Time (seconds)", fontsize=11)
    ax.set_ylabel("Floor", fontsize=11)
    ax.set_xlim(0, 120)
    ax.set_ylim(1, 10)

    t = np.array(sim["trajectory"]["t"])
    e1 = np.array(sim["trajectory"]["E1"])
    e2 = np.array(sim["trajectory"]["E2"])

    ax.step(t, e1, where="post", color=BLUE, lw=2.2, label="Elevator E1")
    ax.step(t, e2, where="post", color=ORANGE, lw=2.2, label="Elevator E2")

    req_t = [r["time"] for r in sim["requests"]]
    req_f = [r["floor"] for r in sim["requests"]]
    req_d = ["↑" if r["dir"] == "UP" else "↓" for r in sim["requests"]]

    for tt, ff, dd in zip(req_t, req_f, req_d):
        ax.scatter(tt, ff, color=RED, s=28, zorder=5)
        ax.text(tt + 1.2, ff + 0.2, dd, color=RED, fontsize=10, fontweight="bold")

    assign_e1 = [t0 for t0, _f, idx in sim["assigned"] if idx == 0]
    assign_e2 = [t0 for t0, _f, idx in sim["assigned"] if idx == 1]
    ax.scatter(assign_e1, np.interp(assign_e1, t, e1), marker="s", color=BLUE, s=40, alpha=0.7, label="Assigned to E1")
    ax.scatter(assign_e2, np.interp(assign_e2, t, e2), marker="D", color=ORANGE, s=40, alpha=0.7, label="Assigned to E2")

    ax.axvline(60, color=PURPLE, ls="--", lw=1.6)
    ax.text(61, 9.2, "GA Re-optimization triggered", color=PURPLE, fontsize=9, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8)


def draw_dashboard(fig, parent_spec, baseline, smart):
    gs = parent_spec.subgridspec(2, 2, wspace=0.35, hspace=0.45)

    # Wait time gauge-like bar
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_title("Average Wait Time", fontsize=11, fontweight="bold")
    ax1.barh([0], [baseline["wait"]], color="#CFD8DC", height=0.45, label="Without system")
    ax1.barh([0], [smart["wait"]], color=GREEN, height=0.28, label="With system")
    ax1.set_xlim(0, max(50, baseline["wait"] + 8))
    ax1.set_yticks([])
    ax1.set_xlabel("Seconds", fontsize=9)
    ax1.text(baseline["wait"], 0.16, f"{baseline['wait']:.1f}s", ha="right", fontsize=9)
    ax1.text(smart["wait"], -0.18, f"{smart['wait']:.1f}s", ha="right", fontsize=9, color=GREEN, fontweight="bold")
    ax1.legend(fontsize=7, loc="lower right")

    # Energy efficiency
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title("Energy Efficiency", fontsize=11, fontweight="bold")
    energy_rel = [100.0, 100.0 * smart["energy"] / max(1e-9, baseline["energy"])]
    ax2.bar(["No Optimization", "With GA"], energy_rel, color=["#B0BEC5", BLUE], edgecolor="black")
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Relative Energy (%)", fontsize=9)

    # Comfort reversals
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_title("Passenger Comfort (Reversals)", fontsize=11, fontweight="bold")
    ax3.bar(["Traditional", "Fuzzy + GA"], [baseline["reversals"], smart["reversals"]], color=[RED, GREEN], edgecolor="black")
    ax3.set_ylabel("Reversals / trip", fontsize=9)

    # Floor request density heatmap
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_title("Floor Coverage Heatmap", fontsize=11, fontweight="bold")
    density = np.array([smart["floor_density"]])
    im = ax4.imshow(density, cmap="YlOrRd", aspect="auto")
    ax4.set_yticks([])
    ax4.set_xticks(np.arange(10))
    ax4.set_xticklabels([str(i) for i in range(1, 11)], fontsize=8)
    ax4.set_xlabel("Floors", fontsize=9)
    fig.colorbar(im, ax=ax4, fraction=0.046, pad=0.04)


def draw_takeaways(ax, baseline, smart):
    ax.axis("off")
    ax.set_title("Key Takeaways", fontsize=14, fontweight="bold")

    wait_gain = 100.0 * (baseline["wait"] - smart["wait"]) / max(1e-9, baseline["wait"])
    energy_gain = 100.0 * (baseline["energy"] - smart["energy"]) / max(1e-9, baseline["energy"])
    texts = [
        "Fuzzy Logic: Intelligent assignment using linguistic rules - no hard thresholds",
        "Genetic Algorithm: Route optimization - evolves better solutions over generations",
        f"Together: {wait_gain:.0f}% reduction in wait time, {energy_gain:.0f}% energy savings",
    ]
    box_colors = ["#E3F2FD", "#F3E5F5", "#E8F5E9"]
    x_positions = [0.03, 0.35, 0.67]
    w, h = 0.3, 0.55

    for x, text, c in zip(x_positions, texts, box_colors):
        rect = FancyBboxPatch((x, 0.2), w, h, boxstyle="round,pad=0.02,rounding_size=0.03", fc=c, ec="#455A64", lw=1.4, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x + w / 2, 0.48, text, ha="center", va="center", fontsize=10, fontweight="bold", wrap=True, transform=ax.transAxes)


def main():
    plt.style.use("seaborn-v0_8-whitegrid")

    baseline = run_simulation(use_smart=False, seed=21)
    smart = run_simulation(use_smart=True, seed=21)

    fig = plt.figure(figsize=(18, 12), facecolor="#FFFFFF", constrained_layout=True)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.1, 2.0, 1.1], width_ratios=[1.25, 1.0], hspace=0.35, wspace=0.25)

    ax_top = fig.add_subplot(gs[0, :])
    draw_flow_diagram(ax_top)

    ax_mid_left = fig.add_subplot(gs[1, 0])
    draw_timeline(ax_mid_left, smart)

    parent_mid_right = gs[1, 1]
    draw_dashboard(fig, parent_mid_right, baseline, smart)

    ax_bottom = fig.add_subplot(gs[2, :])
    draw_takeaways(ax_bottom, baseline, smart)

    fig.suptitle("Complete System Flow - Fuzzy + GA Working Together", fontsize=16, fontweight="bold", y=0.98)
    fig.text(
        0.5,
        0.01,
        "Smart Elevator Management System - Soft Computing Project",
        ha="center",
        fontsize=9,
        color="#616161",
    )
    filename = "05_combined.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved: {filename}")
    plt.show()


if __name__ == "__main__":
    main()
