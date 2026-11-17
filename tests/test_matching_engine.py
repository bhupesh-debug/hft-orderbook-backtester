"""
Unit & Integration tests for HFT matching engine execution and state persistence.
"""

import unittest
from src.engine.matching_engine import HFTBacktestEngine


class TestMatchingEngine(unittest.TestCase):
    def test_engine_initialization_and_pre_fill(self):
        engine = HFTBacktestEngine(symbol="MSFT", initial_mid_price=400.0, tick_size=0.01)
        engine.populate_initial_book(depth_levels=5, shares_per_level=100)
        b, a = engine.lob.get_bbo()
        self.assertAlmostEqual(b, 399.99, places=4)
        self.assertAlmostEqual(a, 400.01, places=4)

    def test_short_simulation_run(self):
        engine = HFTBacktestEngine(symbol="TSLA", initial_mid_price=250.0, tick_size=0.01)
        res = engine.run_simulation(total_ticks=500, random_seed=42)
        m = res["metrics"]
        self.assertIn("total_pnl_usd", m)
        self.assertIn("sharpe_ratio", m)
        self.assertGreater(res["total_ticks"], 0)


if __name__ == '__main__':
    unittest.main()
