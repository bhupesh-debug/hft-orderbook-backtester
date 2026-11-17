"""
Market Impact and Slippage Models:
- Kyle's Lambda (Permanent Impact)
- Almgren-Chriss (Transient & Permanent Market Impact)
"""

import numpy as np


class MarketImpactModel:
    def __init__(self, adv: float = 1_000_000, daily_volatility: float = 0.02, eta: float = 0.1, gamma: float = 0.05):
        """
        Parameters:
        - adv: Average Daily Volume (shares)
        - daily_volatility: Daily asset volatility (sigma)
        - eta: Temporary impact parameter
        - gamma: Permanent impact parameter (Kyle's lambda proxy)
        """
        self.adv = adv
        self.daily_volatility = daily_volatility
        self.eta = eta
        self.gamma = gamma

    def kyle_permanent_impact(self, order_qty: int, side_multiplier: int) -> float:
        """
        Delta P_perm = gamma * sigma * (Q / ADV) * P_mid
        """
        return side_multiplier * self.gamma * self.daily_volatility * (order_qty / self.adv)

    def almgren_chriss_temporary_impact(self, order_qty: int, duration_sec: float = 1.0) -> float:
        """
        Temporary price dislocation:
        Slippage = eta * sigma * (order_qty / (adv * (duration_sec / 23400)))^0.5
        """
        trading_day_sec = 23400.0 # 6.5 trading hours
        time_fraction = max(duration_sec / trading_day_sec, 1e-6)
        normalized_rate = order_qty / (self.adv * time_fraction)
        return self.eta * self.daily_volatility * np.sqrt(max(normalized_rate, 0.0))

    def calculate_effective_execution_price(self, nominal_price: float, order_qty: int, side: str, duration_sec: float = 1.0) -> float:
        multiplier = 1 if side.upper() == "BUY" else -1
        perm_drift = self.kyle_permanent_impact(order_qty, multiplier) * nominal_price
        temp_slip = self.almgren_chriss_temporary_impact(order_qty, duration_sec) * nominal_price
        effective_price = nominal_price + perm_drift + (multiplier * temp_slip)
        return max(effective_price, 0.01)
