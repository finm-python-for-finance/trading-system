"""
Compare backtest results with and without realistic market modeling.
This demonstrates why the strategy might be losing money.
"""

from pathlib import Path
from Strategy_Backtesting import (
    Backtester,
    PerformanceAnalyzer,
    run_sample_backtest,
)
from gateway import MarketDataGateway
from matching_engine import MatchingEngine
from order_book import OrderBook
from order_manager import OrderLoggingGateway, OrderManager
from strategy_base import PennyInPennyOutStrategy


def compare_backtests(csv_path: str):
    """Compare backtest with and without realistic costs."""
    
    print("=" * 70)
    print("BACKTEST COMPARISON: Unrealistic vs Realistic Market Modeling")
    print("=" * 70)
    
    # Strategy configuration
    strategy_config = {
        "tick_size": 0.01,
        "base_edge": 0.01,
        "edge_range": 0.05,
        "edge_sensitivity": 1.5,
        "fair_ema_span": 15,
        "fair_median_window": 25,
        "vol_lookback": 30,
        "spread_vol_multiplier": 0.7,
        "fade_strength": 0.02,
        "inventory_soft_limit": 150,
        "base_qty": 5,
        "max_quote_offset": 0.30,
        "vol_halt": 0.12,
    }
    
    # ========================================================================
    # BACKTEST 1: Unrealistic (old behavior)
    # ========================================================================
    print("\n" + "─" * 70)
    print("BACKTEST 1: UNREALISTIC (No Costs, No Spreads)")
    print("─" * 70)
    
    gateway1 = MarketDataGateway(csv_path)
    strategy1 = PennyInPennyOutStrategy(**strategy_config)
    order_book1 = OrderBook()
    order_manager1 = OrderManager(
        capital=50_000,
        max_long_position=1_000,
        max_short_position=1_000,
        commission_per_share=0.0,  # No commissions
        commission_pct=0.0,  # No commissions
    )
    matching_engine1 = MatchingEngine()
    
    backtester1 = Backtester(
        data_gateway=gateway1,
        strategy=strategy1,
        order_manager=order_manager1,
        order_book=order_book1,
        matching_engine=matching_engine1,
        logger=None,
        model_real_spreads=False,  # No spread costs
        model_adverse_selection=False,  # No adverse selection
    )
    
    equity_df1 = backtester1.run()
    analyzer1 = PerformanceAnalyzer(equity_df1["equity"].tolist(), backtester1.trades)
    
    print(f"PnL: ${analyzer1.pnl():.2f}")
    print(f"Sharpe Ratio: {analyzer1.sharpe():.2f}")
    print(f"Max Drawdown: {analyzer1.max_drawdown():.2%}")
    print(f"Win Rate: {analyzer1.win_rate():.2%}")
    print(f"Total Trades: {len([t for t in backtester1.trades if t.qty > 0])}")
    print(f"Total Commissions Paid: ${order_manager1.total_commissions:.2f}")
    print(f"Final Equity: ${equity_df1.iloc[-1]['equity']:.2f}")
    
    # ========================================================================
    # BACKTEST 2: Realistic (with costs)
    # ========================================================================
    print("\n" + "─" * 70)
    print("BACKTEST 2: REALISTIC (With Costs, Spreads, Adverse Selection)")
    print("─" * 70)
    
    gateway2 = MarketDataGateway(csv_path)
    strategy2 = PennyInPennyOutStrategy(**strategy_config)
    order_book2 = OrderBook()
    order_manager2 = OrderManager(
        capital=50_000,
        max_long_position=1_000,
        max_short_position=1_000,
        commission_per_share=0.005,  # $0.005 per share
        commission_pct=0.001,  # 0.1% of notional
    )
    matching_engine2 = MatchingEngine()
    
    backtester2 = Backtester(
        data_gateway=gateway2,
        strategy=strategy2,
        order_manager=order_manager2,
        order_book=order_book2,
        matching_engine=matching_engine2,
        logger=None,
        model_real_spreads=True,  # Model real spreads
        model_adverse_selection=True,  # Model adverse selection
        spread_bps=2.0,  # 2 basis points spread
    )
    
    equity_df2 = backtester2.run()
    analyzer2 = PerformanceAnalyzer(equity_df2["equity"].tolist(), backtester2.trades)
    
    print(f"PnL: ${analyzer2.pnl():.2f}")
    print(f"Sharpe Ratio: {analyzer2.sharpe():.2f}")
    print(f"Max Drawdown: {analyzer2.max_drawdown():.2%}")
    print(f"Win Rate: {analyzer2.win_rate():.2%}")
    print(f"Total Trades: {len([t for t in backtester2.trades if t.qty > 0])}")
    print(f"Total Commissions Paid: ${order_manager2.total_commissions:.2f}")
    print(f"Final Equity: ${equity_df2.iloc[-1]['equity']:.2f}")
    
    # ========================================================================
    # COMPARISON
    # ========================================================================
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    
    pnl_diff = analyzer2.pnl() - analyzer1.pnl()
    commissions = order_manager2.total_commissions
    
    print(f"PnL Difference: ${pnl_diff:.2f}")
    print(f"  (Realistic is ${abs(pnl_diff):.2f} {'worse' if pnl_diff < 0 else 'better'})")
    print(f"\nCommissions Paid: ${commissions:.2f}")
    print(f"  (This is money lost to transaction costs)")
    
    if pnl_diff < 0:
        print(f"\n⚠️  The strategy loses ${abs(pnl_diff):.2f} more when accounting for:")
        print(f"   - Transaction costs: ${commissions:.2f}")
        print(f"   - Spread costs: ~${abs(pnl_diff) - commissions:.2f} (estimated)")
        print(f"   - Adverse selection: included in spread costs")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Increase base_edge to at least ${strategy_config['base_edge'] * 3:.2f}")
        print(f"   2. Reduce base_qty to reduce risk exposure")
        print(f"   3. Tighten inventory_soft_limit to reduce inventory risk")
        print(f"   4. Consider only quoting when edge > costs + risk premium")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Try to find sample data
    sample_csv = Path("clean_data_stock") / "sample_system_test_data.csv"
    if not sample_csv.exists():
        sample_csv = Path("sample_system_test_data.csv")
    
    if sample_csv.exists():
        compare_backtests(str(sample_csv))
    else:
        print("❌ Sample data not found. Please run a backtest first to generate data.")
        print("   Or update the path in this script to point to your data file.")



