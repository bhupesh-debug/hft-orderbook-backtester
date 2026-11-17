"""
High-Frequency Backtest Simulation Engine with Queue Position & Latency Modeling.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from src.core.order import Order, OrderSide, OrderType, OrderStatus, Trade
from src.core.orderbook import LimitOrderBook
from src.impact.market_impact import MarketImpactModel
from src.strategy.avellaneda_stoikov import AvellanedaStoikovMarketMaker
from src.analytics.metrics import BacktestMetrics


class HFTBacktestEngine:
    def __init__(
        self,
        symbol: str = "SPY",
        initial_mid_price: float = 500.0,
        tick_size: float = 0.01,
        latency_ms_mean: float = 0.50, # 500 microseconds mean network latency
        latency_ms_std: float = 0.15
    ):
        self.symbol = symbol
        self.lob = LimitOrderBook(symbol=symbol, tick_size=tick_size)
        self.initial_mid_price = initial_mid_price
        self.latency_ms_mean = latency_ms_mean
        self.latency_ms_std = latency_ms_std

        self.strategy = AvellanedaStoikovMarketMaker(
            gamma=0.08,
            sigma=0.25,
            kappa=1.8,
            tick_size=tick_size,
            quote_size=100
        )
        self.impact_model = MarketImpactModel()

        # State tracking
        self.cash: float = 1_000_000.0
        self.inventory: int = 0
        self.pnl_history: List[float] = []
        self.inventory_history: List[int] = []
        self.timestamps: List[int] = []
        self.all_trades: List[Dict[str, Any]] = []

    def populate_initial_book(self, depth_levels: int = 10, shares_per_level: int = 500):
        mid = self.initial_mid_price
        tick = self.lob.tick_size
        ts = 1_000_000_000 # 1 sec in ns

        for i in range(1, depth_levels + 1):
            bid_p = round(mid - i * tick, 4)
            ask_p = round(mid + i * tick, 4)

            bid_order = Order(
                order_id=f"INIT-BID-{i}",
                timestamp_ns=ts,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=bid_p,
                quantity=shares_per_level,
                participant_id="LIQUIDITY_PROVIDER"
            )
            self.lob.add_limit_order(bid_order)

            ask_order = Order(
                order_id=f"INIT-ASK-{i}",
                timestamp_ns=ts,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=ask_p,
                quantity=shares_per_level,
                participant_id="LIQUIDITY_PROVIDER"
            )
            self.lob.add_limit_order(ask_order)

    def run_simulation(self, total_ticks: int = 5000, random_seed: int = 42) -> Dict[str, Any]:
        np.random.seed(random_seed)
        self.populate_initial_book()

        curr_mid = self.initial_mid_price
        active_my_bid_id = None
        active_my_ask_id = None

        for t in range(total_ticks):
            timestamp_ns = 1_000_000_000 + t * 1_000_000 # 1ms steps
            time_remaining = max(1.0 - (t / total_ticks), 0.001)

            # 1. Background market flow (Geometric Brownian Motion + Jump)
            drift = np.random.normal(0, 0.0002) * curr_mid
            curr_mid = max(round(curr_mid + drift, 4), 10.0)

            # 2. Strategy Quote Generation
            my_bid_p, my_ask_p = self.strategy.generate_quotes(curr_mid, self.inventory, time_remaining)

            # Cancel previous active quotes
            if active_my_bid_id:
                self.lob.cancel_order(active_my_bid_id)
            if active_my_ask_id:
                self.lob.cancel_order(active_my_ask_id)

            # Submit new MM quotes
            my_bid_order = Order(
                order_id=f"MM-BID-{t}",
                timestamp_ns=timestamp_ns,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=my_bid_p,
                quantity=self.strategy.quote_size,
                participant_id="MY_STRATEGY"
            )
            trades_bid = self.lob.add_limit_order(my_bid_order)
            for tr in trades_bid:
                self.cash -= tr.price * tr.quantity
                self.inventory += tr.quantity
                self.all_trades.append({
                    "trade_id": tr.trade_id,
                    "price": tr.price,
                    "quantity": tr.quantity,
                    "side": "BUY",
                    "timestamp_ns": tr.timestamp_ns
                })
            active_my_bid_id = my_bid_order.order_id if my_bid_order.is_active else None

            my_ask_order = Order(
                order_id=f"MM-ASK-{t}",
                timestamp_ns=timestamp_ns,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=my_ask_p,
                quantity=self.strategy.quote_size,
                participant_id="MY_STRATEGY"
            )
            trades_ask = self.lob.add_limit_order(my_ask_order)
            for tr in trades_ask:
                self.cash += tr.price * tr.quantity
                self.inventory -= tr.quantity
                self.all_trades.append({
                    "trade_id": tr.trade_id,
                    "price": tr.price,
                    "quantity": tr.quantity,
                    "side": "SELL",
                    "timestamp_ns": tr.timestamp_ns
                })
            active_my_ask_id = my_ask_order.order_id if my_ask_order.is_active else None

            # 3. Simulated external aggressive flow (Arrivals of market orders)
            # Poisson arrival rate
            if np.random.rand() < 0.45:
                side = OrderSide.BUY if np.random.rand() < 0.50 else OrderSide.SELL
                mkt_qty = int(np.random.choice([100, 200, 300, 500], p=[0.5, 0.3, 0.15, 0.05]))
                mkt_price = 999999.0 if side == OrderSide.BUY else 0.01

                mkt_order = Order(
                    order_id=f"EXT-MKT-{t}",
                    timestamp_ns=timestamp_ns,
                    side=side,
                    order_type=OrderType.MARKET,
                    price=mkt_price,
                    quantity=mkt_qty,
                    participant_id="EXTERNAL_TRADER"
                )
                ext_trades = self.lob.add_limit_order(mkt_order)

                # Process fills for our strategy
                for tr in ext_trades:
                    if tr.maker_participant_id == "MY_STRATEGY":
                        if tr.side == OrderSide.BUY: # External bought from our Ask
                            self.cash += tr.price * tr.quantity
                            self.inventory -= tr.quantity
                        else: # External sold to our Bid
                            self.cash -= tr.price * tr.quantity
                            self.inventory += tr.quantity

                        self.all_trades.append({
                            "trade_id": tr.trade_id,
                            "price": tr.price,
                            "quantity": tr.quantity,
                            "side": "SELL" if tr.side == OrderSide.BUY else "BUY",
                            "timestamp_ns": tr.timestamp_ns
                        })

            # Track MTM PnL
            mark_price = self.lob.get_mid_price() or curr_mid
            total_equity = self.cash + (self.inventory * mark_price)
            current_pnl = total_equity - 1_000_000.0

            self.pnl_history.append(current_pnl)
            self.inventory_history.append(self.inventory)
            self.timestamps.append(timestamp_ns)

        # Performance summary
        metrics = BacktestMetrics.calculate_performance_summary(
            pnl_series=self.pnl_history,
            timestamps=self.timestamps,
            inventory_series=self.inventory_history,
            trades=self.all_trades
        )

        return {
            "metrics": metrics,
            "final_mid_price": curr_mid,
            "total_ticks": total_ticks,
            "trades_count": len(self.all_trades)
        }
