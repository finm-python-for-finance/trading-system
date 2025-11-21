
# test_system.py
import pandas as pd
import numpy as np
import traceback

from gateway import MarketDataGateway
from strategy_base import MovingAverageStrategy
from order_book import OrderBook, Order
from order_manager import OrderManager
from matching_engine import MatchingEngine
from Strategy_Backtesting import Backtester

print("="*60)
print("🚀 Running Full System Test for Trading Framework...")
print("="*60)

try:
    # ---------------------------------------------
    # 1. Create sample data for testing
    # ---------------------------------------------
    df = pd.DataFrame({
        "Datetime": pd.date_range(start="2024-01-01 09:30", periods=50, freq="T"),
        "Open": np.random.uniform(100, 105, 50),
        "High": np.random.uniform(105, 110, 50),
        "Low": np.random.uniform(95, 100, 50),
        "Close": np.random.uniform(100, 110, 50),
        "Volume": np.random.randint(1000, 5000, 50)
    })
    df.to_csv("sample_system_test_data.csv", index=False)
    print("✔ Sample data generated.")

    # ---------------------------------------------
    # 2. Initialize components
    # ---------------------------------------------
    gateway = MarketDataGateway("sample_system_test_data.csv")
    strategy = MovingAverageStrategy(short_window=5, long_window=10)
    order_book = OrderBook()
    order_manager = OrderManager(capital=50000, max_position=200)
    matching_engine = MatchingEngine()

    print("✔ Components initialized successfully.")

    # ---------------------------------------------
    # 3. Run Backtester
    # ---------------------------------------------
    backtester = Backtester(
        data_gateway=gateway,
        strategy=strategy,
        order_manager=order_manager,
        order_book=order_book,
        matching_engine=matching_engine,
        logger=None
    )

    equity = backtester.run()

    # ---------------------------------------------
    # 4. Validate results
    # ---------------------------------------------
    print("\n=== Backtest Summary ===")
    print("Total Equity Points:", len(equity))

    if len(backtester.trades) == 0:
        print("⚠ WARNING: No trades executed. Possible issues with signals or order validation.")
    else:
        print("✔ Trades executed:", len(backtester.trades))
        print("Sample trade:", backtester.trades[0])

    print("Final Portfolio Value:", equity.iloc[-1, 0])
    print("\nSystem test completed successfully.")

except Exception as e:
    print("❌ ERROR during system test:")
    print(str(e))
    traceback.print_exc()
