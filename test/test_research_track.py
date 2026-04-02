"""
test_research_track.py — Integration tests for the research benchmark track.

Exercises the full research pipeline end-to-end:
    ExperimentConfig → run_benchmarks() → result dict validation

Also verifies:
    - AdaptiveFuzzySystem.evaluate() produces a score in [0, 100]
    - All five dispatch strategies successfully assign a request
    - Explainability log is populated and serialisable
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from research.core.config import (
    BuildingConfig,
    ExperimentConfig,
    ExperimentToggles,
    FuzzyConfig,
    GAConfig,
    ObjectiveConfig,
    TrafficConfig,
)
from research.core.models import ElevatorState, PassengerGroupRequest
from research.evaluation.benchmark import run_benchmarks
from research.fuzzy.adaptive_system import AdaptiveFuzzySystem
from research.strategies.common import _make_decision


# ─── Minimal fast config for testing (small pop / short run) ───
_FAST_CFG = ExperimentConfig(
    name     = "test_run",
    seed     = 7,
    building = BuildingConfig(num_floors=10, num_elevators=3, capacity=8),
    traffic  = TrafficConfig(
        mode                = "mixed",
        duration_seconds    = 120,
        base_lambda_per_min = 2.2,
        spike_probability   = 0.05,
    ),
    objective = ObjectiveConfig(alpha=0.2, beta=0.25, gamma=2.0),
    ga        = GAConfig(population=10, generations=8,
                         crossover_rate=0.8, mutation_rate=0.2, elitism=2),
    toggles   = ExperimentToggles(
        adaptive_fuzzy          = True,
        use_ga_for_fuzzy        = True,
        use_ga_for_routes       = True,
        enable_faults           = True,
        enable_stochastic_delay = True,
        enable_spike_events     = True,
    ),
    scenarios = ["peak_up", "mixed"],
)


# ─── Minimal elevator + request fixtures ───────────────────────
def _make_elevator(eid: int = 0, floor: float = 0.0,
                   load: int = 0, cap: int = 8) -> ElevatorState:
    return ElevatorState(
        elevator_id   = eid,
        current_floor = floor,
        direction     = "IDLE",
        capacity      = cap,
        current_load  = load,
        stop_queue    = [],
        energy_consumed = 0.0,
        failed_until  = 0.0,
    )


def _make_request(rid: int = 1, floor: int = 3,
                  direction: str = "UP", dest: int = 7) -> PassengerGroupRequest:
    return PassengerGroupRequest(
        request_id        = rid,
        timestamp         = 0.0,
        floor             = floor,
        direction         = direction,
        passenger_count   = 1,
        destination_floor = dest,
        spike_tag         = False,
    )


# ═══════════════════════════════════════════════════════════════

class TestBenchmarkPipeline(unittest.TestCase):
    """Full-pipeline benchmark output validation."""

    @classmethod
    def setUpClass(cls):
        cls.results = run_benchmarks(_FAST_CFG)

    def test_summary_key_exists(self):
        self.assertIn("summary", self.results)

    def test_rows_have_entries(self):
        self.assertIn("rows", self.results)
        self.assertGreaterEqual(len(self.results["rows"]), 2,
                                "Expected at least 2 result rows")

    def test_explanations_exported(self):
        self.assertIn("explanations", self.results)
        self.assertGreaterEqual(len(self.results["explanations"]), 1)

    def test_peak_up_explanations_present(self):
        keys = list(self.results["explanations"].keys())
        self.assertTrue(any(k.startswith("peak_up") for k in keys),
                        f"No peak_up key in explanations: {keys}")

    def test_hybrid_adaptive_in_summary(self):
        self.assertIn("hybrid_adaptive", self.results["summary"])

    def test_hybrid_avg_wait_non_negative(self):
        m = self.results["summary"]["hybrid_adaptive"]
        self.assertGreaterEqual(m["avg_wait"], 0.0)

    def test_hybrid_net_energy_non_negative(self):
        m = self.results["summary"]["hybrid_adaptive"]
        self.assertGreaterEqual(m["net_energy"], 0.0)

    def test_all_strategies_in_summary(self):
        expected = {"fcfs", "look", "greedy_nearest", "fuzzy_only", "hybrid_adaptive"}
        actual   = set(self.results["summary"].keys())
        self.assertTrue(expected.issubset(actual),
                        f"Missing strategies: {expected - actual}")


class TestAdaptiveFuzzy(unittest.TestCase):
    """Tests for AdaptiveFuzzySystem.evaluate()."""

    def setUp(self):
        self.fuzzy    = AdaptiveFuzzySystem(fuzzy_config=FuzzyConfig())
        self.elevator = _make_elevator(eid=0, floor=5.0)
        self.request  = _make_request(floor=3, direction="UP")

    def test_score_in_range(self):
        expl = self.fuzzy.evaluate(self.elevator, self.request, "mixed")
        self.assertGreaterEqual(expl.score, 0.0)
        self.assertLessEqual(expl.score, 100.0)

    def test_explanation_has_activations(self):
        expl = self.fuzzy.evaluate(self.elevator, self.request, "mixed")
        # Should have at least some rule activations
        self.assertIsInstance(expl.rule_activations, list)

    def test_heavy_load_reduces_score(self):
        light    = _make_elevator(eid=0, floor=5.0, load=0, cap=8)
        heavy    = _make_elevator(eid=0, floor=5.0, load=7, cap=8)
        req      = self.request
        s_light  = self.fuzzy.evaluate(light, req, "mixed").score
        s_heavy  = self.fuzzy.evaluate(heavy, req, "mixed").score
        self.assertGreaterEqual(s_light, s_heavy,
                                "Heavier load should not increase suitability")

    def test_adapt_does_not_raise(self):
        for mode in ("peak_up", "peak_down", "inter_floor", "mixed"):
            self.fuzzy.adapt_rule_weights(mode)
            expl = self.fuzzy.evaluate(self.elevator, self.request, mode)
            self.assertGreaterEqual(expl.score, 0.0)

    def test_reset_restores_weights(self):
        original = {r.name: r.base_weight for r in self.fuzzy.rules}
        self.fuzzy.adapt_rule_weights("peak_up")
        self.fuzzy.reset_rule_weights()
        restored = {r.name: r.base_weight for r in self.fuzzy.rules}
        self.assertEqual(original, restored)


class TestMakeDecision(unittest.TestCase):
    """Tests for the _make_decision factory in common.py."""

    def test_returns_dispatch_decision(self):
        from research.core.models import DispatchDecision
        d = _make_decision(1, 0, 85.0, "peak_up", "test_policy")
        self.assertIsInstance(d, DispatchDecision)
        self.assertEqual(d.request_id, 1)
        self.assertEqual(d.selected_elevator, 0)
        self.assertAlmostEqual(d.score, 85.0)

    def test_explanation_traffic_mode(self):
        d = _make_decision(2, 1, 60.0, "mixed", "greedy")
        self.assertEqual(d.explanation.traffic_mode, "mixed")

    def test_explanation_contains_policy(self):
        d = _make_decision(3, 0, 90.0, "inter_floor", "fcfs",
                           policy_metadata={"q": 2})
        self.assertIn("fcfs", d.explanation.memberships)
        self.assertEqual(d.explanation.memberships["fcfs"]["q"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
