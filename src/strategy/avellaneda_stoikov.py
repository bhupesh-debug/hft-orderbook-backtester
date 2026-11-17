"""
Avellaneda-Stoikov Optimal High-Frequency Market Making Model.
Calculates dynamic reservation prices and asymmetric bid/ask quotes based on inventory risk aversion.
"""

import numpy as np
from typing import Tuple


class AvellanedaStoikovMarketMaker:
    def __init__(
        self,
        gamma: float = 0.1,        # Risk aversion parameter
        sigma: float = 0.30,       # Asset annualized volatility
        kappa: float = 1.5,        # Order book liquidity density / intensity parameter
        time_horizon: float = 1.0, # Normalized trading horizon (e.g. 1 day = 1.0)
        tick_size: float = 0.01,
        quote_size: int = 100
    ):
        self.gamma = gamma
        self.sigma = sigma
        self.kappa = kappa
        self.time_horizon = time_horizon
        self.tick_size = tick_size
        self.quote_size = quote_size

    def calculate_reservation_price(self, mid_price: float, inventory: int, time_remaining: float) -> float:
        """
        Reservation Price r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
        """
        inventory_penalty = inventory * self.gamma * (self.sigma ** 2) * max(time_remaining, 1e-4)
        return mid_price - inventory_penalty

    def calculate_optimal_spread(self, time_remaining: float) -> float:
        """
        Total optimal spread:
        s(t) = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / kappa)
        """
        t_rem = max(time_remaining, 1e-4)
        spread = self.gamma * (self.sigma ** 2) * t_rem + (2.0 / self.gamma) * np.log(1.0 + self.gamma / self.kappa)
        return max(spread, self.tick_size)

    def generate_quotes(self, mid_price: float, inventory: int, time_remaining: float) -> Tuple[float, float]:
        """
        Returns (optimal_bid, optimal_ask)
        """
        res_price = self.calculate_reservation_price(mid_price, inventory, time_remaining)
        half_spread = self.calculate_optimal_spread(time_remaining) / 2.0

        bid = np.floor((res_price - half_spread) / self.tick_size) * self.tick_size
        ask = np.ceil((res_price + half_spread) / self.tick_size) * self.tick_size

        # Guarantee at least 1 tick spread
        if ask <= bid:
            ask = bid + self.tick_size

        return round(bid, 4), round(ask, 4)
