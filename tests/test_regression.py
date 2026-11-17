"""
Regression Test Suite (Level 5 Testing)
Guarantees fixed defects never re-occur.
"""

import unittest
from src.core.order import Order, OrderSide, OrderType, OrderStatus
from src.core.orderbook import LimitOrderBook


class TestRegressionBugs(unittest.TestCase):
    def test_regression_bug_001_unfilled_market_order_resting_in_book(self):
        """
        Bug 001: When an aggressive market order had remaining unfilled quantity,
        it was mistakenly rested into the book at a dummy sweep price ($999,999.00),
        dislocating the best bid and causing artificial mark-to-market drawdown spikes.

        Fix: Non-limit orders (MARKET, IOC) must never be added to resting queues.
        """
        lob = LimitOrderBook(symbol="REGRESS", tick_size=0.01)
        # Seed 100 shares at ask 100.00
        lob.add_limit_order(Order("A1", 1000, OrderSide.SELL, OrderType.LIMIT, 100.00, 100))

        # Market order arrives for 300 shares (only 100 can be filled)
        mkt_order = Order("M1", 2000, OrderSide.BUY, OrderType.MARKET, 999999.0, 300)
        trades = lob.add_limit_order(mkt_order)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 100)
        self.assertEqual(mkt_order.filled_quantity, 100)

        # Crucial check: Remaining 200 shares must NOT be in the bids book!
        self.assertIsNone(lob.get_best_bid(), "Unfilled market order must NOT rest in the LOB bids!")
        self.assertNotEqual(lob.get_mid_price(), 999999.0)


if __name__ == '__main__':
    unittest.main()
