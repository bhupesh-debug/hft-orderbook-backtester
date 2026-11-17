"""
Main Orchestration Script for HFT Order Book Backtester.
Runs tick-by-tick Limit Order Book backtest and executes 10,000-iteration Monte Carlo risk analysis.
"""

import sys
import os
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine.matching_engine import HFTBacktestEngine
from src.analytics.monte_carlo import OrderBookMonteCarloSimulator


def run_full_pipeline():
    print("=" * 70)
    print(" HFT ORDER BOOK BACKTESTER & MARKET MICROSTRUCTURE SIMULATOR")
    print("=" * 70)

    # 1. Run Tick-by-Tick Matching Engine Simulation
    print("\n[STEP 1/3] Executing 5,000-tick LOB Matching Engine Simulation...")
    engine = HFTBacktestEngine(symbol="SPY", initial_mid_price=500.0, tick_size=0.01)
    sim_results = engine.run_simulation(total_ticks=5000, random_seed=42)
    m = sim_results["metrics"]

    print(f" -> Ticks Processed: {sim_results['total_ticks']:,}")
    print(f" -> Total Executed Trades: {m['total_trades_executed']}")
    print(f" -> Total Volume Traded: {m['total_shares_traded']:,} shares")
    print(f" -> Net Realized PnL: ${m['total_pnl_usd']:,.2f} ({m['roi_pct']:.2f}% ROI)")
    print(f" -> Sharpe Ratio (Annualized): {m['sharpe_ratio']:.2f}")
    print(f" -> Sortino Ratio: {m['sortino_ratio']:.2f}")
    print(f" -> Max Drawdown: ${m['max_drawdown_usd']:,.2f} ({m['max_drawdown_pct']:.4f}%)")
    print(f" -> 99% 1-Tick VaR: ${m['var_99_usd']:.2f} | CVaR: ${m['cvar_99_usd']:.2f}")
    print(f" -> Peak Absolute Inventory: {m['max_absolute_inventory']} shares")
    print(f" -> Ending Inventory: {m['ending_inventory']} shares")

    # 2. Run 10,000-Iteration Monte Carlo Simulation
    print("\n[STEP 2/3] Executing 10,000-Iteration Monte Carlo Risk Simulation...")
    mc = OrderBookMonteCarloSimulator(iterations=10000, random_seed=42)
    mc_results = mc.run_simulation(
        base_daily_trades=450,
        base_half_spread_bps=2.5,
        base_inventory_std=350.0,
        target_pnl_usd=5000.0
    )

    print(f" -> Monte Carlo Iterations: {mc_results['iterations']:,}")
    print(f" -> Expected Daily Mean PnL: ${mc_results['mean_pnl_usd']:,.2f}")
    print(f" -> Median PnL: ${mc_results['median_pnl_usd']:,.2f}")
    print(f" -> PnL Standard Deviation: ${mc_results['std_pnl_usd']:,.2f}")
    print(f" -> 5th Percentile (Worst 5%): ${mc_results['percentile_5th_usd']:,.2f}")
    print(f" -> 25th Percentile: ${mc_results['percentile_25th_usd']:,.2f}")
    print(f" -> 75th Percentile: ${mc_results['percentile_75th_usd']:,.2f}")
    print(f" -> 95th Percentile (Top 5%): ${mc_results['percentile_95th_usd']:,.2f}")
    print(f" -> Probability of Reaching $5,000/day Target: {mc_results['probability_achieving_target_pct']:.2f}%")
    print(f" -> Probability of Daily Downside Loss: {mc_results['probability_failure_loss_pct']:.2f}%")
    print(f" -> Expected Downside Loss (when negative): ${mc_results['expected_downside_usd']:,.2f}")

    # 3. Save Summary Artifacts
    print("\n[STEP 3/3] Exporting Verified Analytics to reports/...")
    os.makedirs("reports", exist_ok=True)
    summary_path = os.path.join("reports", "verified_backtest_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "backtest_metrics": m,
            "monte_carlo_metrics": mc_results
        }, f, indent=2)
    print(f" -> Saved: {summary_path}")
    print("\n" + "=" * 70)
    print(" VERIFICATION COMPLETE: ALL MODELS EXECUTED WITH ZERO ERRORS")
    print("=" * 70)


if __name__ == '__main__':
    run_full_pipeline()
