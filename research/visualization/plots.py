"""
research/visualization/plots.py — Benchmark Result Visualisation (Research Track).

Generates four publication-quality plots from benchmark results:
    1. GA convergence curve        (ga_convergence.png)
    2. Average wait time by strategy  (wait_comparison.png)
    3. Fairness variance by strategy  (fairness_comparison.png)
    4. Traffic heatmap — wait time     (traffic_heatmap_wait.png)

Gracefully skips all plot generation if matplotlib is not installed.
All figures are written to research/results/, which is created if absent.
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List

from research.core.config import VisualizationConfig

# ── Optional dependency guard ──────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")   # non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    _MATPLOTLIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MATPLOTLIB_AVAILABLE = False


# ── Default results directory ──────────────────────────────────
_RESULTS_DIR = pathlib.Path(__file__).parent.parent / "results"


# ═══════════════════════════════════════════════════════════════
#  SHARED STYLE HELPERS
# ═══════════════════════════════════════════════════════════════

def _apply_style() -> None:
    """Apply a clean, formal matplotlib style with graceful fallback."""
    for style in ("seaborn-v0_8-whitegrid", "seaborn-whitegrid", "default"):
        try:
            plt.style.use(style)
            break
        except OSError:
            continue


def _ensure_results_dir(cfg: VisualizationConfig) -> pathlib.Path:
    """Create the results directory if it does not exist, return its Path."""
    out = _RESULTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def _annotate_bars(ax: Any, fmt: str = "{:.2f}") -> None:
    """Add value labels on top of each bar in a bar chart."""
    for rect in ax.patches:
        height = rect.get_height()
        ax.text(
            rect.get_x() + rect.get_width() / 2.0,
            height + 0.01 * max(1, height),
            fmt.format(height),
            ha="center", va="bottom",
            fontsize=8, fontweight="bold",
        )


def _finish(fig: Any, path: pathlib.Path, cfg: VisualizationConfig) -> None:
    """Apply tight_layout, save at configured DPI, and close the figure."""
    fig.tight_layout(pad=1.8)
    fig.savefig(path, dpi=cfg.dpi, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
#  INDIVIDUAL PLOT FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def plot_ga_convergence(
    ga_history:    List[float],
    cfg:           VisualizationConfig,
    results_dir:   pathlib.Path,
) -> None:
    """
    Plot GA fitness convergence over generations.

    Args:
        ga_history:  List of best fitness values, one per generation.
        cfg:         Visualisation configuration.
        results_dir: Output directory.
    """
    fig, ax = plt.subplots(figsize=(7, 4))

    generations = list(range(1, len(ga_history) + 1))
    ax.plot(generations, ga_history,
            color=cfg.convergence_color, linewidth=2.0, marker="o",
            markersize=4, markevery=max(1, len(generations) // 15),
            label="Best fitness")

    # Annotate final value
    if ga_history:
        ax.annotate(
            f"  Final: {ga_history[-1]:.3f}",
            xy=(len(ga_history), ga_history[-1]),
            fontsize=8, color=cfg.convergence_color,
        )

    ax.set_title("GA Fuzzy Parameter Optimisation — Convergence",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Generation", fontsize=10)
    ax.set_ylabel("Best Fitness (lower = better)", fontsize=10)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(fontsize=9)

    _finish(fig, results_dir / "ga_convergence.png", cfg)


def plot_wait_comparison(
    summary:     Dict[str, Dict[str, float]],
    cfg:         VisualizationConfig,
    results_dir: pathlib.Path,
) -> None:
    """
    Bar chart comparing average wait time across dispatch strategies.

    Args:
        summary:     Strategy → {avg_wait, net_energy, ...} dict.
        cfg:         Visualisation configuration.
        results_dir: Output directory.
    """
    strategies = list(summary.keys())
    values     = [summary[s].get("avg_wait", 0.0) for s in strategies]
    labels     = [s.replace("_", "\n") for s in strategies]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=cfg.wait_bar_color, edgecolor="white",
                  linewidth=0.8, zorder=3)
    _annotate_bars(ax)

    ax.set_title("Average Passenger Wait Time by Dispatch Strategy",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Strategy", fontsize=10)
    ax.set_ylabel("Average Wait Time (s)", fontsize=10)
    ax.tick_params(axis="x", labelrotation=cfg.label_rotation)
    ax.set_ylim(0, max(values) * 1.25 if values else 10)
    ax.grid(axis="y", linestyle="--", alpha=0.6, zorder=0)

    _finish(fig, results_dir / "wait_comparison.png", cfg)


def plot_fairness_comparison(
    summary:     Dict[str, Dict[str, float]],
    cfg:         VisualizationConfig,
    results_dir: pathlib.Path,
) -> None:
    """
    Bar chart comparing fairness variance across dispatch strategies.

    Lower variance = more equitable wait times across all passengers.

    Args:
        summary:     Strategy → metric dict.
        cfg:         Visualisation configuration.
        results_dir: Output directory.
    """
    strategies = list(summary.keys())
    values     = [summary[s].get("fairness_variance", 0.0) for s in strategies]
    labels     = [s.replace("_", "\n") for s in strategies]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color=cfg.fairness_bar_color, edgecolor="white",
           linewidth=0.8, zorder=3)
    _annotate_bars(ax)

    ax.set_title("Wait-Time Fairness Variance by Dispatch Strategy\n"
                 "(Lower = More Equitable)",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Strategy", fontsize=10)
    ax.set_ylabel("Variance of Wait Times (s²)", fontsize=10)
    ax.tick_params(axis="x", labelrotation=cfg.label_rotation)
    ax.set_ylim(0, max(values) * 1.25 if values else 10)
    ax.grid(axis="y", linestyle="--", alpha=0.6, zorder=0)

    _finish(fig, results_dir / "fairness_comparison.png", cfg)


def plot_traffic_heatmap(
    rows:        List[Dict[str, Any]],
    cfg:         VisualizationConfig,
    results_dir: pathlib.Path,
) -> None:
    """
    Heatmap of average wait time indexed by traffic scenario × strategy.

    Args:
        rows:        List of result row dicts (each has "scenario", "strategy",
                     "avg_wait" keys).
        cfg:         Visualisation configuration.
        results_dir: Output directory.
    """
    # Build 2-D matrix: rows = scenarios, cols = strategies
    scenarios  = sorted({r["scenario"]  for r in rows})
    strategies = sorted({r["strategy"]  for r in rows})

    matrix = []
    for scenario in scenarios:
        row_vals = []
        for strategy in strategies:
            matching = [r["avg_wait"] for r in rows
                        if r["scenario"] == scenario and r["strategy"] == strategy]
            row_vals.append(matching[0] if matching else 0.0)
        matrix.append(row_vals)

    if not matrix:
        return

    fig, ax = plt.subplots(figsize=(max(6, len(strategies) * 1.5), max(4, len(scenarios))))

    im = ax.imshow(matrix, cmap=cfg.heatmap_cmap, aspect="auto")

    # Color bar
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("Avg Wait Time (s)", fontsize=9)

    # Axis labels
    ax.set_xticks(range(len(strategies)))
    ax.set_yticks(range(len(scenarios)))
    ax.set_xticklabels([s.replace("_", "\n") for s in strategies],
                       fontsize=9, rotation=cfg.label_rotation)
    ax.set_yticklabels(scenarios, fontsize=9)

    # Cell annotations
    for i, row_vals in enumerate(matrix):
        for j, val in enumerate(row_vals):
            ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                    fontsize=8, fontweight="bold",
                    color="white" if val > max(v for rv in matrix for v in rv) * 0.6
                    else "black")

    ax.set_title("Benchmark Heatmap — Avg Wait Time (s)\nScenario × Strategy",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Dispatch Strategy", fontsize=10)
    ax.set_ylabel("Traffic Scenario",  fontsize=10)

    _finish(fig, results_dir / "traffic_heatmap_wait.png", cfg)


# ═══════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def generate_all_plots(results: Dict[str, Any],
                       cfg: VisualizationConfig | None = None) -> None:
    """
    Generate all four benchmark plots from the benchmark runner output dict.

    Safe to call even if matplotlib is not installed — a warning is printed
    and the function returns without error.

    Args:
        results: Output dict from research.evaluation.benchmark.run_benchmarks().
        cfg:     Visualisation configuration (uses defaults if None).
    """
    if not _MATPLOTLIB_AVAILABLE:
        print("  [Plots] matplotlib not installed — skipping visualisation output.")
        return

    _apply_style()
    cfg = cfg or VisualizationConfig()
    out = _ensure_results_dir(cfg)

    ga_history = results.get("ga_history", [])
    summary    = results.get("summary", {})
    rows       = results.get("rows", [])

    if ga_history:
        plot_ga_convergence(ga_history, cfg, out)
        print(f"  [Plots] ga_convergence.png  → {out}")

    if summary:
        plot_wait_comparison(summary, cfg, out)
        print(f"  [Plots] wait_comparison.png → {out}")
        plot_fairness_comparison(summary, cfg, out)
        print(f"  [Plots] fairness_comparison.png → {out}")

    if rows:
        plot_traffic_heatmap(rows, cfg, out)
        print(f"  [Plots] traffic_heatmap_wait.png → {out}")
