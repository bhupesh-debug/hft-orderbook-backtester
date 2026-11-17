"""
Quantitative Performance & Risk Metrics for Order Book Backtesting.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd


class BacktestMetrics:
    @staticmethod
    def calculate_performance_summary(
        pnl_series: List[float],
        timestamps: List[int],
        inventory_series: List[int],
        trades: List[Dict[str, Any]],
        initial_capital: float = 1_000_000.0,
        risk_free_rate: float = 0.04
    ) -> Dict[str, Any]:
        if not pnl_series:
            return {}

        pnl_arr = np.array(pnl_series)
        diffs = np.diff(pnl_arr)

        total_pnl = pnl_arr[-1]
        roi_pct = (total_pnl / initial_capital) * 100.0

        # Drawdown calculation
        peak = np.maximum.accumulate(pnl_arr)
        drawdown = peak - pnl_arr
        max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0
        max_drawdown_pct = (max_drawdown / initial_capital) * 100.0

        # Sharpe & Sortino (assuming 1-sec ticks upscaled to annual)
        # 252 days * 6.5 hours * 3600 sec = 5,896,800 steps/yr
        steps_per_year = 252 * 6.5 * 3600
        mean_ret = np.mean(diffs) if len(diffs) > 0 else 0.0
        std_ret = np.std(diffs) if len(diffs) > 0 else 1e-6

        sharpe = (mean_ret * np.sqrt(steps_per_year)) / (std_ret if std_ret > 0 else 1.0)

        downside_diffs = diffs[diffs < 0]
        downside_std = np.std(downside_diffs) if len(downside_diffs) > 0 else 1e-6
        sortino = (mean_ret * np.sqrt(steps_per_year)) / (downside_std if downside_std > 0 else 1.0)

        # VaR & CVaR (99% confidence level on step returns)
        var_99 = float(np.percentile(diffs, 1)) if len(diffs) > 0 else 0.0
        cvar_99 = float(np.mean(diffs[diffs <= var_99])) if len(diffs) > 0 and len(diffs[diffs <= var_99]) > 0 else var_99

        # Trade metrics
        total_trades = len(trades)
        total_volume = sum(t['quantity'] for t in trades) if trades else 0
        max_inventory = int(np.max(np.abs(inventory_series))) if inventory_series else 0
        ending_inventory = inventory_series[-1] if inventory_series else 0

        return {
            "initial_capital": initial_capital,
            "total_pnl_usd": round(total_pnl, 2),
            "roi_pct": round(roi_pct, 4),
            "sharpe_ratio": round(float(sharpe), 2),
            "sortino_ratio": round(float(sortino), 2),
            "max_drawdown_usd": round(max_drawdown, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 4),
            "var_99_usd": round(var_99, 2),
            "cvar_99_usd": round(cvar_99, 2),
            "total_trades_executed": total_trades,
            "total_shares_traded": total_volume,
            "max_absolute_inventory": max_inventory,
            "ending_inventory": ending_inventory
        }
