import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


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
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    y = np.where((x >= a) & (x < b), (x - a) / (b - a + 1e-9), y)
    y = np.where(np.isclose(x, b), 1.0, y)
    y = np.where((x > b) & (x <= c), (c - x) / (c - b + 1e-9), y)
    return np.clip(y, 0, 1)


def trapmf(x, a, b, c, d):
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    y = np.where((x >= a) & (x < b), (x - a) / (b - a + 1e-9), y)
    y = np.where((x >= b) & (x <= c), 1.0, y)
    y = np.where((x > c) & (x <= d), (d - x) / (d - c + 1e-9), y)
    return np.clip(y, 0, 1)


def compute_scenario_memberships():
    distance = 2
    load_ratio = 2 / 8
    queue = 3
    same_dir = 1.0
    idle = 0.0
    opposite = 0.0
    passing = 1.0

    d_near = trapmf([distance], 0, 0, 2, 5)[0]
    d_med = trimf([distance], 2, 5, 9)[0]
    d_far = trapmf([distance], 6, 10, 15, 15)[0]

    l_light = trapmf([load_ratio], 0, 0, 0.3, 0.5)[0]
    l_mod = trimf([load_ratio], 0.2, 0.5, 0.8)[0]
    l_heavy = trapmf([load_ratio], 0.6, 0.8, 1.0, 1.0)[0]

    q_short = trapmf([queue], 0, 0, 2, 4)[0]
    q_med = trimf([queue], 2, 4, 6)[0]
    q_long = trapmf([queue], 5, 7, 10, 10)[0]

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
        "same": same_dir,
        "idle": idle,
        "opp": opposite,
        "pass": passing,
    }


def build_rule_firing(m):
    rules = [
        ("R1: Near & Light & Same", min(m["d_near"], m["l_light"], m["same"]), "VERY_HIGH"),
        ("R2: Near & ShortQ & Same", min(m["d_near"], m["q_short"], m["same"]), "VERY_HIGH"),
        ("R3: Near & Idle & Light", min(m["d_near"], m["idle"], m["l_light"]), "HIGH"),
        ("R4: Med & Light & Same", min(m["d_med"], m["l_light"], m["same"]), "HIGH"),
        ("R5: Med & Mod & Same", min(m["d_med"], m["l_mod"], m["same"]), "HIGH"),
        ("R6: Far & Any", m["d_far"], "LOW"),
        ("R7: Opposite Dir", m["opp"], "VERY_LOW"),
        ("R8: Heavy & Opposite", min(m["l_heavy"], m["opp"]), "VERY_LOW"),
        ("R9: Heavy & LongQ", min(m["l_heavy"], m["q_long"]), "LOW"),
        ("R10: Near & Mod & Same", min(m["d_near"], m["l_mod"], m["same"]), "HIGH"),
        ("R11: Near & Light & Pass", min(m["d_near"], m["l_light"], m["pass"]), "VERY_HIGH"),
        ("R12: Med & Idle", min(m["d_med"], m["idle"]), "MEDIUM"),
        ("R13: Near & MedQ", min(m["d_near"], m["q_med"]), "HIGH"),
        ("R14: Far & Heavy", min(m["d_far"], m["l_heavy"]), "VERY_LOW"),
        ("R15: ShortQ & Pass", min(m["q_short"], m["pass"]), "HIGH"),
        ("R16: ModQ & Same", min(m["q_med"], m["same"]), "MEDIUM"),
        ("R17: Near & Same", min(m["d_near"], m["same"]), "HIGH"),
    ]
    return rules


def defuzzify(rules):
    level_map = {
        "VERY_LOW": FUZZY_VERY_LOW,
        "LOW": FUZZY_LOW,
        "MEDIUM": FUZZY_MEDIUM,
        "HIGH": FUZZY_HIGH,
        "VERY_HIGH": FUZZY_VERY_HIGH,
    }
    strengths = np.array([r[1] for r in rules])
    outputs = np.array([level_map[r[2]] for r in rules])
    if strengths.sum() < 1e-9:
        return 0.0
    return float(np.sum(strengths * outputs) / np.sum(strengths))


def label_from_score(score):
    if score < (FUZZY_VERY_LOW + FUZZY_LOW) / 2:
        return "VERY_LOW"
    if score < (FUZZY_LOW + FUZZY_MEDIUM) / 2:
        return "LOW"
    if score < (FUZZY_MEDIUM + FUZZY_HIGH) / 2:
        return "MEDIUM"
    if score < (FUZZY_HIGH + FUZZY_VERY_HIGH) / 2:
        return "HIGH"
    return "VERY_HIGH"


def main():
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(18, 10), facecolor="#FFFFFF")
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1, 1, 1], height_ratios=[1, 1.1])

    # Distance membership functions
    ax1 = fig.add_subplot(gs[0, 0])
    x_d = np.linspace(0, 15, 400)
    near = trapmf(x_d, 0, 0, 2, 5)
    medium = trimf(x_d, 2, 5, 9)
    far = trapmf(x_d, 6, 10, 15, 15)
    ax1.plot(x_d, near, color=BLUE, lw=2, label="Near")
    ax1.plot(x_d, medium, color=GREEN, lw=2, label="Medium")
    ax1.plot(x_d, far, color=ORANGE, lw=2, label="Far")
    ax1.fill_between(x_d, near, color=BLUE, alpha=0.25)
    ax1.fill_between(x_d, medium, color=GREEN, alpha=0.25)
    ax1.fill_between(x_d, far, color=ORANGE, alpha=0.25)
    ax1.set_title("Distance Membership Functions", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Distance (floors)", fontsize=11)
    ax1.set_ylabel("Membership", fontsize=11)
    ax1.set_ylim(0, 1.05)
    ax1.legend(fontsize=9)

    # Load membership functions
    ax2 = fig.add_subplot(gs[0, 1])
    x_l = np.linspace(0, 1.0, 400)
    light = trapmf(x_l, 0, 0, 0.3, 0.5)
    moderate = trimf(x_l, 0.2, 0.5, 0.8)
    heavy = trapmf(x_l, 0.6, 0.8, 1.0, 1.0)
    ax2.plot(x_l, light, color=BLUE, lw=2, label="Light")
    ax2.plot(x_l, moderate, color=GREEN, lw=2, label="Moderate")
    ax2.plot(x_l, heavy, color=ORANGE, lw=2, label="Heavy")
    ax2.fill_between(x_l, light, color=BLUE, alpha=0.25)
    ax2.fill_between(x_l, moderate, color=GREEN, alpha=0.25)
    ax2.fill_between(x_l, heavy, color=ORANGE, alpha=0.25)
    ax2.set_title("Load Membership Functions", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Load Ratio", fontsize=11)
    ax2.set_ylabel("Membership", fontsize=11)
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=9)

    sec = ax2.secondary_xaxis("top", functions=(lambda x: x * 8, lambda x: x / 8))
    sec.set_xlabel("Passengers (0 to 8)", fontsize=10)
    sec.set_xticks([0, 2, 4, 6, 8])

    # Queue membership functions
    ax3 = fig.add_subplot(gs[0, 2])
    x_q = np.linspace(0, 10, 400)
    short = trapmf(x_q, 0, 0, 2, 4)
    q_med = trimf(x_q, 2, 4, 6)
    q_long = trapmf(x_q, 5, 7, 10, 10)
    ax3.plot(x_q, short, color=BLUE, lw=2, label="Short")
    ax3.plot(x_q, q_med, color=GREEN, lw=2, label="Medium")
    ax3.plot(x_q, q_long, color=ORANGE, lw=2, label="Long")
    ax3.fill_between(x_q, short, color=BLUE, alpha=0.25)
    ax3.fill_between(x_q, q_med, color=GREEN, alpha=0.25)
    ax3.fill_between(x_q, q_long, color=ORANGE, alpha=0.25)
    ax3.set_title("Queue Length Membership Functions", fontsize=14, fontweight="bold")
    ax3.set_xlabel("Pending Stops", fontsize=11)
    ax3.set_ylabel("Membership", fontsize=11)
    ax3.set_ylim(0, 1.05)
    ax3.legend(fontsize=9)

    # Rule firing visualization
    ax4 = fig.add_subplot(gs[1, :2])
    memberships = compute_scenario_memberships()
    rules = build_rule_firing(memberships)
    labels = [r[0] for r in rules]
    strengths = np.array([r[1] for r in rules])
    outputs = [r[2] for r in rules]
    color_map = {
        "VERY_HIGH": "#1B5E20",
        "HIGH": "#66BB6A",
        "MEDIUM": "#FDD835",
        "LOW": "#FB8C00",
        "VERY_LOW": "#D32F2F",
    }
    colors = [color_map[o] for o in outputs]

    y = np.arange(len(labels))
    bars = ax4.barh(y, strengths, color=colors, edgecolor="black", lw=0.6)
    ax4.set_yticks(y)
    ax4.set_yticklabels(labels, fontsize=8)
    ax4.set_xlim(0, 1.0)
    ax4.set_xlabel("Firing Strength", fontsize=11)
    ax4.set_title("Rule Firing for: E1 at Floor 3 -> Request at Floor 5 (UP)", fontsize=14, fontweight="bold")

    top3 = np.argsort(strengths)[-3:][::-1]
    for idx in top3:
        ax4.text(strengths[idx] + 0.02, idx, "Top Rule", va="center", fontsize=9, color=PURPLE, fontweight="bold")

    # Defuzzification output
    ax5 = fig.add_subplot(gs[1, 2])
    centroid = defuzzify(rules)
    ax5.set_title("Centroid Defuzzification", fontsize=14, fontweight="bold")
    ax5.set_xlim(0, 100)
    ax5.set_ylim(0, 1)
    ax5.set_yticks([])
    ax5.set_xlabel("Suitability Score (0-100)", fontsize=11)

    marks = [FUZZY_VERY_LOW, FUZZY_LOW, FUZZY_MEDIUM, FUZZY_HIGH, FUZZY_VERY_HIGH]
    mark_names = ["VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    for m, n in zip(marks, mark_names):
        ax5.axvline(m, color="#9E9E9E", ls=":", lw=1.2)
        ax5.text(m, 0.05, n, rotation=90, ha="center", va="bottom", fontsize=8)

    ax5.hlines(0.5, 0, 100, color="#757575", lw=2)
    ax5.scatter([centroid], [0.5], color=PURPLE, s=130, zorder=5)
    suit_label = label_from_score(centroid)
    ax5.annotate(
        f"Centroid = {centroid:.1f} -> {suit_label} suitability",
        xy=(centroid, 0.5),
        xytext=(centroid - 35, 0.78),
        arrowprops=dict(arrowstyle="->", lw=1.2, color=PURPLE),
        fontsize=10,
        color=PURPLE,
        fontweight="bold",
    )

    fig.suptitle("Fuzzy Logic - Elevator Assignment Engine", fontsize=16, fontweight="bold", y=0.98)
    fig.text(
        0.5,
        0.01,
        "Smart Elevator Management System - Soft Computing Project",
        ha="center",
        fontsize=9,
        color="#616161",
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    filename = "02_fuzzy.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved: {filename}")
    plt.show()


if __name__ == "__main__":
    main()
