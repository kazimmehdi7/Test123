"""
Unit Tests for the Autonomous Margin Sentinel & Saturation Radar Engine.
"""
from __future__ import annotations

import unittest
from app.engine.sentinel import calculate_saturation_index, analyze_sentinel_health


class TestSentinelEngine(unittest.TestCase):

    def setUp(self):
        self.sample_inputs = {
            "sell": 34.99,
            "supplier": 8.50,
            "ship": 4.00,
            "duty_rate": 0.075,
            "flat_duty": 0.0,
            "broker": 4.00,
            "channel": "shopify",
            "ad_pct": 0.20,
            "return_rate": 0.03,
            "buffer_pct": 0.05,
            "target_pct": 0.15,
        }

    def test_saturation_index_calculation(self):
        # Untapped niche
        sat_low = calculate_saturation_index(competitor_count=2, active_ads_count=1)
        self.assertLess(sat_low["score"], 30.0)
        self.assertEqual(sat_low["stage"], "UNTAPPED")

        # Heavily saturated niche
        sat_high = calculate_saturation_index(competitor_count=25, active_ads_count=30)
        self.assertGreater(sat_high["score"], 75.0)
        self.assertIn(sat_high["stage"], ("COMPETITIVE", "SATURATED"))

    def test_sentinel_health_and_headroom_analysis(self):
        sat = calculate_saturation_index(competitor_count=5, active_ads_count=8)
        health = analyze_sentinel_health(self.sample_inputs, sat)

        self.assertIn(health["threat_level"], ("STABLE", "THRIVING", "WARNING", "CRITICAL"))
        self.assertGreater(health["max_allowable_cpa"], 0)
        self.assertGreater(len(health["recommendations"]), 0)
        self.assertGreater(len(health["reasons"]), 0)

    def test_critical_threat_when_cpa_exceeds_max(self):
        sat = calculate_saturation_index(competitor_count=20, active_ads_count=25)
        # Forced high CPA ($22.00) that exceeds max allowable CPA (~$8.00)
        health = analyze_sentinel_health(self.sample_inputs, sat, current_estimated_cpa=22.00)

        self.assertEqual(health["threat_level"], "CRITICAL")
        self.assertLess(health["cpa_headroom"], 0)
        self.assertTrue(any("exceeds" in r.lower() for r in health["reasons"]))


if __name__ == "__main__":
    unittest.main()
