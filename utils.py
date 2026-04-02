"""
utils.py — Shared Pure Utilities for the Smart Elevator Management System.

This module provides self-contained helper functions that are shared
between the legacy root-level track and the research/ package track.
No cross-imports between the two tracks are required beyond this file.

Functions:
    triangular_mf   — Triangular membership function (used by fuzzy logic)
    poisson_sample  — Knuth Poisson integer sampler (used by simulation)
    percentile      — Empirical percentile (used by metrics reporting)
    fmt_box_header  — Console box-drawing title header
    fmt_table_row   — Fixed-width table row formatter
    fmt_separator   — Horizontal separator line
"""

from __future__ import annotations

import math
import random
from typing import List, Sequence


# ═══════════════════════════════════════════════════════════════
#  FUZZY LOGIC — Membership Function
# ═══════════════════════════════════════════════════════════════

def triangular_mf(x: float, a: float, b: float, c: float) -> float:
    """
    Evaluate a symmetric triangular membership function at x.

    The function rises linearly from 0 at a to 1 at b,
    then falls linearly from 1 at b to 0 at c.

    Args:
        x: Input value to evaluate.
        a: Left foot (MF is 0 at and below this value).
        b: Peak (MF is 1.0 at this value).
        c: Right foot (MF is 0 at and above this value).

    Returns:
        Membership degree in [0.0, 1.0].

    Examples:
        >>> triangular_mf(5.0, 0.0, 5.0, 10.0)
        1.0
        >>> triangular_mf(0.0, 0.0, 5.0, 10.0)
        0.0
        >>> triangular_mf(2.5, 0.0, 5.0, 10.0)
        0.5
    """
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        denom = b - a
        return (x - a) / denom if denom > 1e-9 else 1.0
    # x > b
    denom = c - b
    return (c - x) / denom if denom > 1e-9 else 1.0


# ═══════════════════════════════════════════════════════════════
#  SIMULATION — Poisson Sampler
# ═══════════════════════════════════════════════════════════════

def poisson_sample(lam: float, rng: random.Random) -> int:
    """
    Sample an integer from a Poisson distribution with mean lam.

    Uses the Knuth algorithm, which works correctly with the
    standard library's random.Random (which has no .poisson method).

    Args:
        lam: Expected number of arrivals (mean of Poisson). Must be >= 0.
        rng:  A random.Random instance for reproducibility.

    Returns:
        Non-negative integer drawn from Poisson(lam).
    """
    if lam <= 0.0:
        return 0
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


# ═══════════════════════════════════════════════════════════════
#  METRICS — Percentile
# ═══════════════════════════════════════════════════════════════

def percentile(values: List[float], p: int) -> float:
    """
    Compute the p-th empirical percentile of a list of values.

    Uses nearest-rank method with index clamping.

    Args:
        values: List of numeric values. May be empty.
        p:      Percentile to compute, integer in [0, 100].

    Returns:
        The p-th percentile value, or 0.0 if values is empty.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(round((p / 100.0) * (len(sorted_vals) - 1)))
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return sorted_vals[idx]


# ═══════════════════════════════════════════════════════════════
#  CONSOLE FORMATTING — Box Drawing & Tables
# ═══════════════════════════════════════════════════════════════

def fmt_box_header(title: str, width: int = 60) -> str:
    """
    Build a unicode box-drawing header line.

    Example output (width=44):
        ╔════════════════════════════════════════════╗
        ║          REQUEST LOG SUMMARY               ║
        ╚════════════════════════════════════════════╝

    Args:
        title: Text to display inside the box.
        width: Total inner width (excluding border characters).

    Returns:
        Multi-line string with top border, title, and bottom border.
    """
    inner = width - 2
    top    = "  ╔" + "═" * inner + "╗"
    middle = "  ║" + title.center(inner) + "║"
    bottom = "  ╚" + "═" * inner + "╝"
    return "\n".join([top, middle, bottom])


def fmt_separator(width: int = 60, double: bool = False) -> str:
    """
    Build a horizontal separator line for console tables.

    Args:
        width:  Total width of the separator.
        double: Use double-line (═) if True, single-line (─) if False.

    Returns:
        A string like '  ──────────────────────────────────────────────'
    """
    char = "═" if double else "─"
    return "  " + char * width


def fmt_table_row(values: Sequence[str], widths: Sequence[int], sep: str = "│") -> str:
    """
    Build a fixed-width table row from cell values and column widths.

    Numeric strings are right-justified; all others are left-justified.
    Each cell is padded or truncated to exactly its specified width.

    Args:
        values: Cell contents (will be converted to str if not already).
        widths: Column widths in characters (one per value).
        sep:    Column separator character (default '│').

    Returns:
        A string like '  │ col1   │   42 │ some text │'

    Example:
        >>> fmt_table_row(["Name", "42", "OK"], [10, 6, 8])
        '  │ Name       │    42 │ OK       │'
    """
    parts = []
    for val, w in zip(values, widths):
        s = str(val)
        # Truncate if too long
        if len(s) > w:
            s = s[: w - 1] + "…"
        # Right-justify numbers, left-justify text
        try:
            float(s.replace("%", "").replace("s", "").strip())
            cell = s.rjust(w)
        except ValueError:
            cell = s.ljust(w)
        parts.append(cell)
    return "  " + sep + (" " + sep + " ").join(" " + p for p in parts) + " " + sep
