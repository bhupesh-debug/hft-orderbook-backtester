"""
Monte Carlo Simulation Engine for High-Frequency Order Book Execution & Market Making.
Performs 10,000+ stochastic iterations across volatility, queue latency, and order arrival intensity.
"""

from typing import Dict, Any
import numpy as np


class OrderBookMonteCarloSimulator:
    def __init__(self, iterations: int = 10000, random_seed: int = 42):
        self.iterations = iterations
        self.random_seed = random_seed

    def run_simulation(
        self,
        base_daily_trades: int = 450,
        base_half_spread_bps: float = 2.5,
        base_inventory_std: float = 350.0,
        daily_volatility_range: tuple = (0.015, 0.045),
        target_pnl_usd: float = 5000.0
    ) -> Dict[str, Any]:
        np.random.seed(self.random_seed)

        # 1. Stochastic variables
        # Daily volatility sampled from beta/triangular distribution
        volatilities = np.random.uniform(daily_volatility_range[0], daily_volatility_range[1], self.iterations)
        
        # Trade count: Poisson/log-normal variation around daily trades
        trade_counts = np.random.poisson(base_daily_trades, self.iterations)
        
        # Realized capture spread (bps) under adverse selection
        # Higher volatility widens spread but increases adverse selection
        adverse_selection_loss = np.random.gamma(shape=2.0, scale=0.6, size=self.iterations)
        effective_spread_bps = np.maximum(base_half_spread_bps * 2.0 - adverse_selection_loss, 0.2)
        
        # Execution fee rebate / cost (e.g. maker rebate of 0.2 bps)
        maker_rebate_bps = 0.20
        
        # Gross Spread PnL = trade_counts * avg_order_size ($100 * 100 shares = $10,000 notional) * spread_bps
        notional_per_trade = 100.0 * 100 # $10,000 notional
        gross_spread_pnl = trade_counts * notional_per_trade * ((effective_spread_bps + maker_rebate_bps) / 10000.0)
        
        # Inventory Holding Risk (Mark-to-market overnight / intraday drift)
        intraday_inventory_shocks = np.random.normal(0, base_inventory_std, self.iterations)
        inventory_drift_pnl = intraday_inventory_shocks * 100.0 * (volatilities * np.random.normal(0, 1, self.iterations))
        
        # Net Daily PnL
        simulated_net_pnls = gross_spread_pnl + inventory_drift_pnl

        # Statistical Metrics
        mean_pnl = float(np.mean(simulated_net_pnls))
        median_pnl = float(np.median(simulated_net_pnls))
        std_pnl = float(np.std(simulated_net_pnls))
        p5 = float(np.percentile(simulated_net_pnls, 5))
        p25 = float(np.percentile(simulated_net_pnls, 25))
        p75 = float(np.percentile(simulated_net_pnls, 75))
        p95 = float(np.percentile(simulated_net_pnls, 95))

        prob_target = float(np.mean(simulated_net_pnls >= target_pnl_usd)) * 100.0
        prob_failure = float(np.mean(simulated_net_pnls < 0)) * 100.0 # unprofitable day
        
        downside_outcomes = simulated_net_pnls[simulated_net_pnls < 0]
        expected_downside = float(np.mean(downside_outcomes)) if len(downside_outcomes) > 0 else 0.0

        return {
            "iterations": self.iterations,
            "target_pnl_usd": target_pnl_usd,
            "mean_pnl_usd": round(mean_pnl, 2),
            "median_pnl_usd": round(median_pnl, 2),
            "std_pnl_usd": round(std_pnl, 2),
            "percentile_5th_usd": round(p5, 2),
            "percentile_25th_usd": round(p25, 2),
            "percentile_75th_usd": round(p75, 2),
            "percentile_95th_usd": round(p95, 2),
            "probability_achieving_target_pct": round(prob_target, 2),
            "probability_failure_loss_pct": round(prob_failure, 2),
            "expected_downside_usd": round(expected_downside, 2)
        }
