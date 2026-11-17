"""
Unit tests for Limit Order Book (LOB) data structure and order management.
"""

import unittest
from src.core.order import Order, OrderSide, OrderType, OrderStatus
from src.core.orderbook import LimitOrderBook


class TestLimitOrderBook(unittest.TestCase):
    def setUp(self):
        self.lob = LimitOrderBook(symbol="AAPL", tick_size=0.01)

    def test_add_bid_order(self):
        order = Order("B1", 1000, OrderSide.BUY, OrderType.LIMIT, 150.00, 100)
        trades = self.lob.add_limit_order(order)
        self.assertEqual(len(trades), 0)
        self.assertEqual(self.lob.get_best_bid(), 150.00)
        self.assertIsNone(self.lob.get_best_ask())

    def test_add_ask_order(self):
        order = Order("A1", 1000, OrderSide.SELL, OrderType.LIMIT, 150.05, 100)
        trades = self.lob.add_limit_order(order)
        self.assertEqual(len(trades), 0)
        self.assertEqual(self.lob.get_best_ask(), 150.05)

    def test_bbo_and_spread(self):
        self.lob.add_limit_order(Order("B1", 1000, OrderSide.BUY, OrderType.LIMIT, 150.00, 100))
        self.lob.add_limit_order(Order("A1", 1000, OrderSide.SELL, OrderType.LIMIT, 150.02, 100))
        self.assertEqual(self.lob.get_bbo(), (150.00, 150.02))
        self.assertAlmostEqual(self.lob.get_spread(), 0.02, places=4)
        self.assertAlmostEqual(self.lob.get_mid_price(), 150.01, places=4)

    def test_price_time_priority(self):
        # Two buy orders at the same price: B1 arrives first, then B2
        self.lob.add_limit_order(Order("B1", 1000, OrderSide.BUY, OrderType.LIMIT, 150.00, 100))
        self.lob.add_limit_order(Order("B2", 2000, OrderSide.BUY, OrderType.LIMIT, 150.00, 100))

        # A sell order crosses the bid
        sell = Order("S1", 3000, OrderSide.SELL, OrderType.LIMIT, 150.00, 150)
        trades = self.lob.add_limit_order(sell)

        self.assertEqual(len(trades), 2)
        # First trade must match B1
        self.assertEqual(trades[0].maker_order_id, "B1")
        self.assertEqual(trades[0].quantity, 100)
        # Second trade matches B2 partially
        self.assertEqual(trades[1].maker_order_id, "B2")
        self.assertEqual(trades[1].quantity, 50)

    def test_cancel_order(self):
        self.lob.add_limit_order(Order("B1", 1000, OrderSide.BUY, OrderType.LIMIT, 150.00, 100))
        self.assertTrue(self.lob.cancel_order("B1"))
        self.assertIsNone(self.lob.get_best_bid())
        # Canceling non-existent order returns False
        self.assertFalse(self.lob.cancel_order("NON_EXISTENT"))

    def test_microprice_and_ofi(self):
        self.lob.add_limit_order(Order("B1", 1000, OrderSide.BUY, OrderType.LIMIT, 100.00, 300))
        self.lob.add_limit_order(Order("A1", 1000, OrderSide.SELL, OrderType.LIMIT, 100.10, 100))
        micro = self.lob.get_microprice()
        # micro = (100.10 * 300 + 100.00 * 100) / 400 = (30030 + 10000)/400 = 40030/400 = 100.075
        self.assertAlmostEqual(micro, 100.075, places=4)
        ofi = self.lob.get_order_flow_imbalance()
        # OFI = (300 - 100) / 400 = 0.50
        self.assertAlmostEqual(ofi, 0.50, places=4)


if __name__ == '__main__':
    unittest.main()
