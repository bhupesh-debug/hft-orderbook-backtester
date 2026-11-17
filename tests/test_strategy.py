"""
Tests for Avellaneda-Stoikov high-frequency market making equations and inventory skewing.
"""

import unittest
from src.strategy.avellaneda_stoikov import AvellanedaStoikovMarketMaker


class TestAvellanedaStoikov(unittest.TestCase):
    def setUp(self):
        self.mm = AvellanedaStoikovMarketMaker(gamma=0.1, sigma=0.20, kappa=1.5, tick_size=0.01)

    def test_reservation_price_inventory_symmetry(self):
        mid = 100.0
        # Zero inventory -> reservation price = mid price
        r0 = self.mm.calculate_reservation_price(mid, inventory=0, time_remaining=1.0)
        self.assertEqual(r0, mid)

        # Long inventory -> reservation price drops below mid to attract selling
        r_long = self.mm.calculate_reservation_price(mid, inventory=500, time_remaining=1.0)
        self.assertLess(r_long, mid)

        # Short inventory -> reservation price rises above mid to attract buying
        r_short = self.mm.calculate_reservation_price(mid, inventory=-500, time_remaining=1.0)
        self.assertGreater(r_short, mid)

    def test_quote_generation_spread(self):
        bid, ask = self.mm.generate_quotes(mid_price=100.0, inventory=0, time_remaining=1.0)
        self.assertLess(bid, ask)
        self.assertGreaterEqual(ask - bid, self.mm.tick_size)


if __name__ == '__main__':
    unittest.main()
