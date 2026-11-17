"""
Core Order & Trade Definitions for High-Frequency Order Book Simulation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"       # Immediate or Cancel
    FOK = "FOK"       # Fill or Kill
    CANCEL = "CANCEL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    order_id: str
    timestamp_ns: int
    side: OrderSide
    order_type: OrderType
    price: float
    quantity: int
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    participant_id: str = "DEFAULT"

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED)


@dataclass
class Trade:
    trade_id: str
    timestamp_ns: int
    maker_order_id: str
    taker_order_id: str
    side: OrderSide       # Taker side
    price: float
    quantity: int
    maker_participant_id: str
    taker_participant_id: str
