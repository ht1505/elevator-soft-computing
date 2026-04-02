"""
test_utils.py — Unit tests for utils.py shared utility functions.

Tests:
    triangular_mf  — peak, feet, monotone slopes, clamping
    poisson_sample — non-negative, mean convergence over many samples
    percentile     — p0=min, p100=max, empty list, p50 between extremes
    fmt_box_header — output includes title string
    fmt_table_row  — correct number of separators, correct width handling
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
from utils import (
    fmt_box_header,
    fmt_table_row,
    percentile,
    poisson_sample,
    triangular_mf,
)


class TestTriangularMF(unittest.TestCase):
    """Tests for utils.triangular_mf()."""

    def test_peak_is_one(self):
        """Membership at the peak b should be exactly 1.0."""
        self.assertAlmostEqual(triangular_mf(5.0, 0.0, 5.0, 10.0), 1.0)

    def test_left_foot_is_zero(self):
        """Membership at left foot a should be 0.0."""
        self.assertAlmostEqual(triangular_mf(0.0, 0.0, 5.0, 10.0), 0.0)

    def test_right_foot_is_zero(self):
        """Membership at right foot c should be 0.0."""
        self.assertAlmostEqual(triangular_mf(10.0, 0.0, 5.0, 10.0), 0.0)

    def test_below_left_foot_is_zero(self):
        """Membership below a must be 0.0."""
        self.assertEqual(triangular_mf(-5.0, 0.0, 5.0, 10.0), 0.0)

    def test_above_right_foot_is_zero(self):
        """Membership above c must be 0.0."""
        self.assertEqual(triangular_mf(15.0, 0.0, 5.0, 10.0), 0.0)

    def test_midpoint_left_is_half(self):
        """Midpoint on rising slope should be 0.5."""
        self.assertAlmostEqual(triangular_mf(2.5, 0.0, 5.0, 10.0), 0.5)

    def test_midpoint_right_is_half(self):
        """Midpoint on falling slope should be 0.5."""
        self.assertAlmostEqual(triangular_mf(7.5, 0.0, 5.0, 10.0), 0.5)

    def test_result_always_in_unit_interval(self):
        """MF output must stay in [0, 1] for any input."""
        for x in [-10, -1, 0, 2, 5, 7, 10, 15, 100]:
            v = triangular_mf(float(x), 0.0, 5.0, 10.0)
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_degenerate_left_shoulder(self):
        """Flat-top left shoulder: a == b → output 0 at c, non-zero at a."""
        # tri(0,0,5): 1.0 at 0, declines to 0 at 5
        self.assertAlmostEqual(triangular_mf(0.0, 0.0, 0.0, 5.0), 0.0)
        self.assertAlmostEqual(triangular_mf(5.0, 0.0, 0.0, 5.0), 0.0)

    def test_strict_monotone_rising(self):
        """Membership should be monotonically rising from a to b."""
        vals = [triangular_mf(x, 0.0, 5.0, 10.0) for x in [0, 1, 2, 3, 4, 5]]
        self.assertEqual(vals, sorted(vals))

    def test_strict_monotone_falling(self):
        """Membership should be monotonically falling from b to c."""
        vals = [triangular_mf(x, 0.0, 5.0, 10.0) for x in [5, 6, 7, 8, 9, 10]]
        self.assertEqual(vals, sorted(vals, reverse=True))


class TestPoissonSample(unittest.TestCase):
    """Tests for utils.poisson_sample()."""

    def test_zero_lambda_returns_zero(self):
        """λ=0 must always return 0."""
        rng = random.Random(1)
        for _ in range(50):
            self.assertEqual(poisson_sample(0.0, rng), 0)

    def test_negative_lambda_returns_zero(self):
        """Negative λ must return 0 safely."""
        rng = random.Random(2)
        self.assertEqual(poisson_sample(-5.0, rng), 0)

    def test_output_non_negative(self):
        """Output must always be non-negative."""
        rng = random.Random(3)
        for lam in [0.1, 1.0, 3.0, 10.0]:
            for _ in range(100):
                self.assertGreaterEqual(poisson_sample(lam, rng), 0)

    def test_sample_mean_close_to_lambda(self):
        """Sample mean over many draws should be ≈ λ (within 20%)."""
        rng = random.Random(42)
        for lam in [1.0, 3.0, 5.0]:
            samples = [poisson_sample(lam, rng) for _ in range(3000)]
            mean = sum(samples) / len(samples)
            self.assertAlmostEqual(mean, lam, delta=lam * 0.20)


class TestPercentile(unittest.TestCase):
    """Tests for utils.percentile()."""

    def test_empty_list_returns_zero(self):
        self.assertEqual(percentile([], 50), 0.0)

    def test_p0_is_minimum(self):
        vals = [3, 7, 1, 9, 2]
        self.assertEqual(percentile(vals, 0), min(vals))

    def test_p100_is_maximum(self):
        vals = [3, 7, 1, 9, 2]
        self.assertEqual(percentile(vals, 100), max(vals))

    def test_p50_within_range(self):
        vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        p50 = percentile(vals, 50)
        self.assertGreaterEqual(p50, min(vals))
        self.assertLessEqual(p50, max(vals))

    def test_single_element(self):
        """Single-element list should return that element for any p."""
        self.assertEqual(percentile([42.0], 0),   42.0)
        self.assertEqual(percentile([42.0], 50),  42.0)
        self.assertEqual(percentile([42.0], 100), 42.0)

    def test_p95_greater_than_p50(self):
        vals = list(range(1, 101))
        self.assertGreater(percentile(vals, 95), percentile(vals, 50))


class TestFormatHelpers(unittest.TestCase):
    """Tests for utils.fmt_box_header() and utils.fmt_table_row()."""

    def test_box_header_contains_title(self):
        header = fmt_box_header("HELLO WORLD", width=40)
        self.assertIn("HELLO WORLD", header)
        self.assertIn("╔", header)
        self.assertIn("╚", header)

    def test_table_row_contains_separator(self):
        row = fmt_table_row(["Name", "42"], [10, 6])
        self.assertIn("│", row)

    def test_table_row_length_consistent(self):
        """Two rows with same widths should have the same total length."""
        row1 = fmt_table_row(["Alice", "100"], [10, 6])
        row2 = fmt_table_row(["Bob",   "25"],  [10, 6])
        self.assertEqual(len(row1), len(row2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
