import math
import numpy as np
import matplotlib.pyplot as plt


BLUE = "#2196F3"
GREEN = "#4CAF50"
ORANGE = "#FF9800"
RED = "#F44336"
PURPLE = "#9C27B0"

FUZZY_VERY_LOW = 10
FUZZY_LOW = 30
FUZZY_MEDIUM = 50
FUZZY_HIGH = 75
FUZZY_VERY_HIGH = 95


def trimf(x, a, b, c):
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a + 1e-9)
    return (c - x) / (c - b + 1e-9)


def trapmf(x, a, b, c, d):
    if x < a or x > d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a + 1e-9)
    return (d - x) / (d - c + 1e-9)


def fuzzify(elevator, request_floor=5, request_dir="UP"):
    distance = abs(elevator["floor"] - request_floor)
    load_ratio = elevator["load"] / 8.0
    queue_len = elevator["queue"]

    d_near = trapmf(distance, 0, 0, 2, 5)
    d_med = trimf(distance, 2, 5, 9)
    d_far = trapmf(distance, 6, 10, 15, 15)

    l_light = trapmf(load_ratio, 0, 0, 0.3, 0.5)
    l_mod = trimf(load_ratio, 0.2, 0.5, 0.8)
    l_heavy = trapmf(load_ratio, 0.6, 0.8, 1.0, 1.0)

    q_short = trapmf(queue_len, 0, 0, 2, 4)
    q_med = trimf(queue_len, 2, 4, 6)
    q_long = trapmf(queue_len, 5, 7, 10, 10)

    same = 1.0 if elevator["direction"] == request_dir else 0.0
    idle = 1.0 if elevator["direction"] == "IDLE" else 0.0
    opposite = 1.0 if (same == 0 and idle == 0) else 0.0

    passing = 0.0
    if same == 1.0:
        if request_dir == "UP" and elevator["floor"] <= request_floor:
            passing = 1.0
        elif request_dir == "DOWN" and elevator["floor"] >= request_floor:
            passing = 1.0
        else:
            passing = 0.4
    elif idle == 1.0:
        passing = 0.8
    else:
        passing = 0.1

    return {
        "d_near": d_near,
        "d_med": d_med,
        "d_far": d_far,
        "l_light": l_light,
        "l_mod": l_mod,
        "l_heavy": l_heavy,
        "q_short": q_short,
        "q_med": q_med,
        "q_long": q_long,
        "same": same,
        "idle": idle,
        "opp": opposite,
        "pass": passing,
        "distance": distance,
    }


def infer_score(m):
    rules = [
        ("Near+Light+Same", min(m["d_near"], m["l_light"], m["same"]), "VERY_HIGH"),
        ("Near+ShortQ+Pass", min(m["d_near"], m["q_short"], m["pass"]), "VERY_HIGH"),
        ("Near+Same", min(m["d_near"], m["same"]), "HIGH"),
        ("Med+Light+Same", min(m["d_med"], m["l_light"], m["same"]), "HIGH"),
        ("Med+Idle", min(m["d_med"], m["idle"]), "MEDIUM"),
        ("Far", m["d_far"], "LOW"),
        ("Opposite", m["opp"], "VERY_LOW"),
        ("Heavy+Opposite", min(m["l_heavy"], m["opp"]), "VERY_LOW"),
        ("Heavy+LongQ", min(m["l_heavy"], m["q_long"]), "LOW"),
        ("ShortQ+Idle", min(m["q_short"], m["idle"]), "HIGH"),
    ]

    levels = {
        "VERY_LOW": FUZZY_VERY_LOW,
        "LOW": FUZZY_LOW,
        "MEDIUM": FUZZY_MEDIUM,
        "HIGH": FUZZY_HIGH,
        "VERY_HIGH": FUZZY_VERY_HIGH,
    }

    strengths = np.array([r[1] for r in rules])
    values = np.array([levels[r[2]] for r in rules])
    score = float(np.sum(strengths * values) / (np.sum(strengths) + 1e-9))
    top_rule = max(rules, key=lambda r: r[1])[0]
    return score, top_rule


def component_scores(m):
    dist_score = 100 * (m["d_near"] + 0.5 * m["d_med"])
    load_score = 100 * (m["l_light"] + 0.5 * m["l_mod"])
    queue_score = 100 * (m["q_short"] + 0.5 * m["q_med"])
    direction_score = 100 * (1.0 * m["same"] + 0.7 * m["idle"] + 0.2 * m["opp"])
    passing_score = 100 * m["pass"]
    return [dist_score, load_score, queue_score, direction_score, passing_score]


def radar_plot(ax, labels, series, series_labels, colors):
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate([angles, [angles[0]]])

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 100)

    for values, label, color in zip(series, series_labels, colors):
        data = np.array(values + [values[0]])
        ax.plot(angles, data, color=color, lw=2, label=label)
        ax.fill(angles, data, color=color, alpha=0.2)


def main():
    plt.style.use("seaborn-v0_8-whitegrid")

    elevators = {
        "E1": {"floor": 3, "load": 2, "queue": 3, "direction": "UP"},
        "E2": {"floor": 8, "load": 6, "queue": 1, "direction": "DOWN"},
        "E3": {"floor": 1, "load": 0, "queue": 0, "direction": "IDLE"},
    }

    colors = {"E1": BLUE, "E2": RED, "E3": GREEN}
    fuzzy_data = {}
    final_scores = {}
    top_rules = {}
    radar_data = {}

    for name, e in elevators.items():
        m = fuzzify(e)
        score, rule = infer_score(m)
        fuzzy_data[name] = m
        final_scores[name] = score
        top_rules[name] = rule
        radar_data[name] = component_scores(m)

    fig = plt.figure(figsize=(16, 7), facecolor="#FFFFFF")

    ax1 = fig.add_subplot(1, 2, 1, projection="polar")
    labels = ["Distance Score", "Load Score", "Queue Score", "Direction Score", "Passing-By Score"]
    radar_plot(
        ax1,
        labels,
        [radar_data["E1"], radar_data["E2"], radar_data["E3"]],
        ["E1", "E2", "E3"],
        [colors["E1"], colors["E2"], colors["E3"]],
    )
    ax1.set_title("Component Dominance (Radar View)", fontsize=14, fontweight="bold", pad=16)
    ax1.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15), fontsize=10)

    ax2 = fig.add_subplot(1, 2, 2)
    names = ["E1", "E2", "E3"]
    y = np.arange(len(names))
    vals = [final_scores[n] for n in names]
    bars = ax2.barh(y, vals, color=[colors[n] for n in names], edgecolor="black")
    ax2.set_yticks(y)
    ax2.set_yticklabels(names, fontsize=11)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("Fuzzy Suitability Score", fontsize=11)
    ax2.set_title("Final Fuzzy Score Comparison", fontsize=14, fontweight="bold")

    winner = names[int(np.argmax(vals))]
    for i, n in enumerate(names):
        ax2.text(vals[i] + 1.2, i, f"{vals[i]:.1f} | Top rule: {top_rules[n]}", va="center", fontsize=9)

    win_idx = names.index(winner)
    ax2.annotate(
        "WINNER",
        xy=(vals[win_idx], win_idx),
        xytext=(vals[win_idx] + 18, win_idx + 0.45),
        arrowprops=dict(arrowstyle="->", lw=1.4, color=PURPLE),
        fontsize=11,
        color=PURPLE,
        fontweight="bold",
    )

    fig.suptitle("Fuzzy Scoring - All Elevators Compared", fontsize=16, fontweight="bold")
    fig.text(
        0.5,
        0.015,
        "Smart Elevator Management System - Soft Computing Project",
        ha="center",
        fontsize=9,
        color="#616161",
    )
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    filename = "03_fuzzy_compare.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved: {filename}")
    plt.show()


if __name__ == "__main__":
    main()
