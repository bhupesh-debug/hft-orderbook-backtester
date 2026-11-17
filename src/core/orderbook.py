"""
Limit Order Book (LOB) Implementation supporting L2/L3 market data feeds and FIFO matching.
"""

from collections import deque
from typing import Dict, List, Optional, Tuple
from bisect import bisect_left, insort_right
from src.core.order import Order, OrderSide, OrderStatus, Trade, OrderType


class LimitOrderBook:
    def __init__(self, symbol: str = "TICKER", tick_size: float = 0.01):
        self.symbol = symbol
        self.tick_size = tick_size

        # price -> deque of Order
        self.bids: Dict[float, deque] = {}
        self.asks: Dict[float, deque] = {}

        # Sorted unique price levels
        # bids_prices in descending order (highest bid first)
        # asks_prices in ascending order (lowest ask first)
        self.bid_prices: List[float] = []
        self.ask_prices: List[float] = []

        # order_id -> (Order, price, side)
        self.orders: Dict[str, Tuple[Order, float, OrderSide]] = {}

        self.last_trade_price: Optional[float] = None
        self.trade_counter: int = 0

    def round_price(self, price: float) -> float:
        return round(round(price / self.tick_size) * self.tick_size, 6)

    def add_limit_order(self, order: Order) -> List[Trade]:
        """
        Inserts limit order into the order book, executing crossing trades if market is crossed.
        """
        trades: List[Trade] = []
        order.price = self.round_price(order.price)

        if order.side == OrderSide.BUY:
            # Check for crossing asks
            while self.ask_prices and self.ask_prices[0] <= order.price and not order.is_filled:
                best_ask_price = self.ask_prices[0]
                queue = self.asks[best_ask_price]

                while queue and not order.is_filled:
                    maker = queue[0]
                    fill_qty = min(order.remaining_quantity, maker.remaining_quantity)

                    maker.filled_quantity += fill_qty
                    order.filled_quantity += fill_qty
                    self.last_trade_price = best_ask_price
                    self.trade_counter += 1

                    trade = Trade(
                        trade_id=f"TRD-{self.trade_counter:08d}",
                        timestamp_ns=order.timestamp_ns,
                        maker_order_id=maker.order_id,
                        taker_order_id=order.order_id,
                        side=OrderSide.BUY,
                        price=best_ask_price,
                        quantity=fill_qty,
                        maker_participant_id=maker.participant_id,
                        taker_participant_id=order.participant_id
                    )
                    trades.append(trade)

                    if maker.is_filled:
                        maker.status = OrderStatus.FILLED
                        queue.popleft()
                        self.orders.pop(maker.order_id, None)
                    else:
                        maker.status = OrderStatus.PARTIALLY_FILLED

                if not queue:
                    del self.asks[best_ask_price]
                    self.ask_prices.pop(0)

            # If order still has remaining qty, add to bids ONLY IF it is a LIMIT order
            if not order.is_filled:
                if order.order_type == OrderType.LIMIT:
                    order.status = OrderStatus.ACCEPTED if order.filled_quantity == 0 else OrderStatus.PARTIALLY_FILLED
                    if order.price not in self.bids:
                        self.bids[order.price] = deque()
                        self._insert_bid_price(order.price)
                    self.bids[order.price].append(order)
                    self.orders[order.order_id] = (order, order.price, OrderSide.BUY)
                else:
                    # MARKET or IOC order remainder is canceled
                    order.status = OrderStatus.FILLED if order.filled_quantity > 0 else OrderStatus.CANCELED
            else:
                order.status = OrderStatus.FILLED

        else: # OrderSide.SELL
            # Check for crossing bids
            while self.bid_prices and self.bid_prices[0] >= order.price and not order.is_filled:
                best_bid_price = self.bid_prices[0]
                queue = self.bids[best_bid_price]

                while queue and not order.is_filled:
                    maker = queue[0]
                    fill_qty = min(order.remaining_quantity, maker.remaining_quantity)

                    maker.filled_quantity += fill_qty
                    order.filled_quantity += fill_qty
                    self.last_trade_price = best_bid_price
                    self.trade_counter += 1

                    trade = Trade(
                        trade_id=f"TRD-{self.trade_counter:08d}",
                        timestamp_ns=order.timestamp_ns,
                        maker_order_id=maker.order_id,
                        taker_order_id=order.order_id,
                        side=OrderSide.SELL,
                        price=best_bid_price,
                        quantity=fill_qty,
                        maker_participant_id=maker.participant_id,
                        taker_participant_id=order.participant_id
                    )
                    trades.append(trade)

                    if maker.is_filled:
                        maker.status = OrderStatus.FILLED
                        queue.popleft()
                        self.orders.pop(maker.order_id, None)
                    else:
                        maker.status = OrderStatus.PARTIALLY_FILLED

                if not queue:
                    del self.bids[best_bid_price]
                    self.bid_prices.pop(0)

            # If order still has remaining qty, add to asks ONLY IF it is a LIMIT order
            if not order.is_filled:
                if order.order_type == OrderType.LIMIT:
                    order.status = OrderStatus.ACCEPTED if order.filled_quantity == 0 else OrderStatus.PARTIALLY_FILLED
                    if order.price not in self.asks:
                        self.asks[order.price] = deque()
                        self._insert_ask_price(order.price)
                    self.asks[order.price].append(order)
                    self.orders[order.order_id] = (order, order.price, OrderSide.SELL)
                else:
                    # MARKET or IOC order remainder is canceled
                    order.status = OrderStatus.FILLED if order.filled_quantity > 0 else OrderStatus.CANCELED
            else:
                order.status = OrderStatus.FILLED

        return trades

    def _insert_bid_price(self, price: float):
        # descending order
        for i, p in enumerate(self.bid_prices):
            if price > p:
                self.bid_prices.insert(i, price)
                return
        self.bid_prices.append(price)

    def _insert_ask_price(self, price: float):
        # ascending order
        for i, p in enumerate(self.ask_prices):
            if price < p:
                self.ask_prices.insert(i, price)
                return
        self.ask_prices.append(price)

    def cancel_order(self, order_id: str) -> bool:
        if order_id not in self.orders:
            return False
        order, price, side = self.orders[order_id]
        order.status = OrderStatus.CANCELED

        if side == OrderSide.BUY:
            if price in self.bids:
                try:
                    self.bids[price].remove(order)
                    if not self.bids[price]:
                        del self.bids[price]
                        self.bid_prices.remove(price)
                except ValueError:
                    pass
        else:
            if price in self.asks:
                try:
                    self.asks[price].remove(order)
                    if not self.asks[price]:
                        del self.asks[price]
                        self.ask_prices.remove(price)
                except ValueError:
                    pass

        del self.orders[order_id]
        return True

    def get_best_bid(self) -> Optional[float]:
        return self.bid_prices[0] if self.bid_prices else None

    def get_best_ask(self) -> Optional[float]:
        return self.ask_prices[0] if self.ask_prices else None

    def get_bbo(self) -> Tuple[Optional[float], Optional[float]]:
        return self.get_best_bid(), self.get_best_ask()

    def get_mid_price(self) -> Optional[float]:
        bid, ask = self.get_bbo()
        if bid is not None and ask is not None:
            return (bid + ask) / 2.0
        return bid if bid is not None else ask

    def get_spread(self) -> Optional[float]:
        bid, ask = self.get_bbo()
        if bid is not None and ask is not None:
            return ask - bid
        return None

    def get_depth(self, levels: int = 5) -> Tuple[List[Tuple[float, int]], List[Tuple[float, int]]]:
        bids_depth = []
        for p in self.bid_prices[:levels]:
            vol = sum(o.remaining_quantity for o in self.bids[p])
            bids_depth.append((p, vol))

        asks_depth = []
        for p in self.ask_prices[:levels]:
            vol = sum(o.remaining_quantity for o in self.asks[p])
            asks_depth.append((p, vol))

        return bids_depth, asks_depth

    def get_microprice(self) -> Optional[float]:
        """
        Volume-weighted microprice based on top of book:
        P_micro = (P_ask * Q_bid + P_bid * Q_ask) / (Q_bid + Q_ask)
        """
        b, a = self.get_bbo()
        if b is None or a is None:
            return self.get_mid_price()
        q_bid = sum(o.remaining_quantity for o in self.bids[b])
        q_ask = sum(o.remaining_quantity for o in self.asks[a])
        if q_bid + q_ask == 0:
            return (b + a) / 2.0
        return (a * q_bid + b * q_ask) / (q_bid + q_ask)

    def get_order_flow_imbalance(self) -> float:
        """
        OFI = (Q_bid - Q_ask) / (Q_bid + Q_ask)
        """
        b, a = self.get_bbo()
        if b is None or a is None:
            return 0.0
        q_bid = sum(o.remaining_quantity for o in self.bids[b])
        q_ask = sum(o.remaining_quantity for o in self.asks[a])
        if q_bid + q_ask == 0:
            return 0.0
        return (q_bid - q_ask) / (q_bid + q_ask)
