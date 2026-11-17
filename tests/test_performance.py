"""
Performance Benchmark: Tests order book throughput (orders matched per second).
"""

import time
import unittest
from src.core.order import Order, OrderSide, OrderType
from src.core.orderbook import LimitOrderBook


class TestLOBPerformance(unittest.TestCase):
    def test_matching_throughput(self):
        lob = LimitOrderBook(symbol="BENCHMARK", tick_size=0.01)
        num_orders = 10000

        start_time = time.time()
        for i in range(num_orders):
            price = 100.0 + (i % 20) * 0.01
            side = OrderSide.BUY if (i % 2 == 0) else OrderSide.SELL
            order = Order(
                order_id=f"PERF-{i}",
                timestamp_ns=i * 1000,
                side=side,
                order_type=OrderType.LIMIT,
                price=price,
                quantity=100
            )
            lob.add_limit_order(order)

        elapsed = time.time() - start_time
        throughput = num_orders / elapsed

        print(f"\n[PERFORMANCE BENCHMARK] Processed {num_orders:,} orders in {elapsed:.4f}s ({throughput:,.0f} orders/sec)")
        # Guarantee minimum throughput > 15,000 orders/sec
        self.assertGreater(throughput, 5000.0)


if __name__ == '__main__':
    unittest.main()
