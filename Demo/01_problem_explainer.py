import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Circle


BLUE = "#2196F3"
GREEN = "#4CAF50"
ORANGE = "#FF9800"
RED = "#F44336"
PURPLE = "#9C27B0"


def fuzzy_score(distance, load, queue_len, direction, req_dir="UP"):
    # Lightweight deterministic score model for strategy simulation.
    direction_bonus = 20 if direction == req_dir else (10 if direction == "IDLE" else -20)
    return 100 - 8 * distance - 4 * load - 5 * queue_len + direction_bonus


def simulate_wait_times(seed=17, n_requests=220):
    rng = np.random.default_rng(seed)

    def make_elevators():
        return [
            {"floor": 3, "queue": 3, "load": 2, "dir": "UP"},
            {"floor": 7, "queue": 1, "load": 6, "dir": "DOWN"},
            {"floor": 1, "queue": 0, "load": 0, "dir": "IDLE"},
        ]

    def update_state(state, req_floor, req_dir, chosen_idx):
        for i, el in enumerate(state):
            if i == chosen_idx:
                travel = abs(el["floor"] - req_floor)
                el["floor"] = req_floor
                el["queue"] = min(10, max(0, el["queue"] + rng.integers(0, 2)))
                el["load"] = int(np.clip(el["load"] + rng.integers(-1, 2), 0, 8))
                el["dir"] = req_dir
            else:
                drift = rng.choice([-1, 0, 1], p=[0.2, 0.6, 0.2])
                el["floor"] = int(np.clip(el["floor"] + drift, 1, 10))
                el["queue"] = max(0, el["queue"] - rng.integers(0, 2))
                el["load"] = int(np.clip(el["load"] + rng.integers(-1, 2), 0, 8))
                if el["queue"] == 0:
                    el["dir"] = "IDLE"

    def run(strategy):
        state = make_elevators()
        wait_times = []
        rr = 0
        for _ in range(n_requests):
            req_floor = int(rng.integers(1, 11))
            req_dir = "UP" if req_floor < 10 and (req_floor == 1 or rng.random() > 0.35) else "DOWN"

            if strategy == "nearest":
                chosen = int(np.argmin([abs(el["floor"] - req_floor) for el in state]))
            elif strategy == "fcfs":
                chosen = rr % 3
                rr += 1
            else:
                vals = []
                for el in state:
                    d = abs(el["floor"] - req_floor)
                    vals.append(fuzzy_score(d, el["load"], el["queue"], el["dir"], req_dir))
                chosen = int(np.argmax(vals))

            e = state[chosen]
            travel = abs(e["floor"] - req_floor)
            # 2s per floor + queue service overhead.
            wait = 2.0 * travel + 4.0 * e["queue"] + rng.normal(2.0, 0.8)
            wait_times.append(max(3.0, wait))
            update_state(state, req_floor, req_dir, chosen)

        return float(np.mean(wait_times))

    nearest = run("nearest")
    fcfs = run("fcfs")
    smart = run("smart")
    return [nearest, fcfs, smart]


def main():
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor="#FFFFFF")

    # Panel A: Building overview
    ax = axes[0]
    ax.set_title("A) Building Overview", fontsize=15, fontweight="bold")
    ax.set_xlim(-1.5, 4.5)
    ax.set_ylim(0.5, 10.8)
    ax.set_xlabel("Elevator Shafts", fontsize=11)
    ax.set_ylabel("Floor", fontsize=11)

    building = Rectangle((-0.2, 1), 3.6, 9, fill=False, lw=2.0, ec="black")
    ax.add_patch(building)

    for floor in range(1, 11):
        ax.plot([-0.2, 3.4], [floor, floor], color="#D9D9D9", lw=0.8)
        ax.text(-0.45, floor, str(floor), va="center", fontsize=9)

    shaft_x = [0.4, 1.6, 2.8]
    labels = ["E1", "E2", "E3"]
    colors = [BLUE, GREEN, ORANGE]
    current_floors = [3, 7, 1]

    for x, label, color, floor in zip(shaft_x, labels, colors, current_floors):
        ax.plot([x, x], [1, 10], color="#9E9E9E", lw=4, alpha=0.6)
        cab = Rectangle((x - 0.22, floor - 0.35), 0.44, 0.7, fc=color, ec="black", lw=1.2)
        ax.add_patch(cab)
        ax.text(x, 10.35, label, ha="center", fontsize=10, fontweight="bold")
        ax.text(x, floor, f"{label}\nF{floor}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    request_floor = 5
    passenger = Circle((3.9, request_floor), 0.12, color=RED)
    ax.add_patch(passenger)
    ax.plot([3.9, 3.9], [request_floor - 0.35, request_floor - 0.12], color=RED, lw=2)
    ax.arrow(4.1, request_floor - 0.15, 0, 0.4, width=0.02, head_width=0.12, head_length=0.12, color=RED)
    ax.text(4.12, request_floor + 0.4, "UP request", fontsize=9, color=RED, fontweight="bold")

    for x, floor, label in zip(shaft_x, current_floors, labels):
        dist = abs(request_floor - floor)
        ax.annotate(
            f"d={dist}",
            xy=(x + 0.25, floor),
            xytext=(3.55, request_floor),
            arrowprops=dict(arrowstyle="->", lw=1.2, color="#616161"),
            fontsize=9,
            color="#424242",
        )

    ax.set_xticks([])

    # Panel B: Decision matrix
    ax = axes[1]
    ax.set_title("B) Which Elevator Should Serve Floor 5 (UP Request)?", fontsize=14, fontweight="bold")
    ax.axis("off")

    row_labels = ["E1", "E2", "E3"]
    col_labels = ["Distance to F5", "Load (out of 8)", "Queue Length", "Direction"]
    values = [
        ["2 (Near)", "2", "3", "UP"],
        ["2 (Near)", "6", "1", "DOWN"],
        ["4 (Medium)", "0", "0", "IDLE"],
    ]

    def factor_color(distance, load, queue, direction):
        out = []
        out.append("#C8E6C9" if distance <= 2 else ("#FFF9C4" if distance <= 4 else "#FFCDD2"))
        out.append("#C8E6C9" if load <= 2 else ("#FFF9C4" if load <= 4 else "#FFCDD2"))
        out.append("#C8E6C9" if queue <= 1 else ("#FFF9C4" if queue <= 3 else "#FFCDD2"))
        out.append("#C8E6C9" if direction == "UP" else ("#FFF9C4" if direction == "IDLE" else "#FFCDD2"))
        return out

    cell_colors = [
        factor_color(2, 2, 3, "UP"),
        factor_color(2, 6, 1, "DOWN"),
        factor_color(4, 0, 0, "IDLE"),
    ]

    table = ax.table(
        cellText=values,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        colColours=["#ECEFF1"] * len(col_labels),
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2.2)

    for i in range(3):
        for j in range(4):
            table[(i + 1, j)].set_facecolor(cell_colors[i][j])

    ax.text(0.0, 0.08, "Green = Favorable   Yellow = Neutral   Red = Unfavorable", transform=ax.transAxes, fontsize=10)

    # Panel C: Strategy comparison
    ax = axes[2]
    ax.set_title("C) Why Naive Methods Fail", fontsize=15, fontweight="bold")
    strategies = ["Nearest Only", "FCFS", "Smart System"]
    wait_times = simulate_wait_times()
    bar_colors = [ORANGE, PURPLE, GREEN]
    bars = ax.bar(strategies, wait_times, color=bar_colors, edgecolor="black", lw=1)
    ax.set_ylabel("Average Wait Time (seconds)", fontsize=11)
    ax.set_ylim(0, max(wait_times) + 12)

    for bar, value in zip(bars, wait_times):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.8, f"{value:.1f}s", ha="center", fontsize=10, fontweight="bold")

    reduction = (wait_times[1] - wait_times[2]) / wait_times[1] * 100
    ax.text(0.5, max(wait_times) + 7.5, f"Soft computing reduces wait time by ~{reduction:.0f}%", fontsize=10, color=RED, fontweight="bold")

    fig.suptitle("The Elevator Dispatching Problem", fontsize=16, fontweight="bold", y=1.02)
    fig.text(
        0.5,
        0.01,
        "Smart Elevator Management System - Soft Computing Project",
        ha="center",
        fontsize=9,
        color="#616161",
    )
    plt.tight_layout()

    filename = "01_problem.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved: {filename}")
    plt.show()


if __name__ == "__main__":
    main()
