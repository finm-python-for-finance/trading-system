# alpaca_mm_trader.py
import time
import threading
from datetime import datetime
import os

import pandas as pd
from alpaca_trade_api import REST

from strategy_base import PennyInPennyOutStrategy


class AlpacaMarketMaker:
    def __init__(self, api_key, api_secret, symbol, strategy, timeframe="1Min"):
        self.api = REST(api_key, api_secret, base_url="https://paper-api.alpaca.markets")
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = strategy

        self.open_bid_id = None
        self.open_ask_id = None
        self.position = 0

    def update_position(self):
        try:
            pos = self.api.get_position(self.symbol)
            self.position = int(pos.qty)
        except Exception as e:
            # Position doesn't exist (no position) or API error
            # This is normal - just means we have no position
            self.position = 0
            # Only log if it's not a "position not found" type error
            error_msg = str(e)
            if "404" not in error_msg and "not found" not in error_msg.lower():
                print(f"[{self.symbol}] Note: Could not get position: {e}")

        # Notify strategy of current exposure
        self.strategy.update_context(self.position)

    def get_latest_bar(self):
        try:
            bars = self.api.get_bars(self.symbol, self.timeframe, limit=50).df

            if isinstance(bars.index, pd.MultiIndex):
                if "symbol" in bars.index.names:
                    bars = bars.xs(self.symbol, level="symbol")
                else:
                    bars = bars.xs(self.symbol, level=-1)

            col_map = {
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
            for lc, uc in col_map.items():
                if uc not in bars.columns and lc in bars.columns:
                    bars[uc] = bars[lc]

            return bars
        except Exception as e:
            print(f"[{self.symbol}] Error fetching bars: {e}")
            raise  


    def cancel_open_orders(self):
        """Cancel all open orders for this symbol and wait for cancellation to complete."""
        try:
            orders = self.api.list_orders(status="open")
            canceled_count = 0
            for o in orders:
                if o.symbol == self.symbol:
                    try:
                        self.api.cancel_order(o.id)
                        canceled_count += 1
                    except Exception as e:
                        print(f"[{self.symbol}] Error canceling order {o.id}: {e}")
            
            # Process cancellations
            if canceled_count > 0:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"[{self.symbol}] Error listing/canceling orders: {e}")

    def submit_quote(self, bid_price, bid_qty, ask_price, ask_qty, bid_active, ask_active):
        bid_id = None
        ask_id = None

        if bid_active:
            try:
                order = self.api.submit_order(
                    symbol=self.symbol,
                    qty=int(bid_qty),
                    side="buy",
                    type="limit",
                    limit_price=round(float(bid_price), 2),
                    time_in_force="gtc"
                )
                bid_id = order.id
                time.sleep(0.2)  # Small delay before submitting ask
            except Exception as e:
                print(f"[{self.symbol}] Error submitting bid: {e}")

        if ask_active:
            try:
                order = self.api.submit_order(
                    symbol=self.symbol,
                    qty=int(ask_qty),
                    side="sell",
                    type="limit",
                    limit_price=round(float(ask_price), 2),
                    time_in_force="gtc"
                )
                ask_id = order.id
            except Exception as e:
                error_msg = str(e)
                # Handle the specific Alpaca restriction error
                if "short sell" in error_msg.lower() and "long buy" in error_msg.lower():
                    print(f"[{self.symbol}]  Cannot submit ask - Alpaca restriction: cannot have both buy/sell orders without position")
                else:
                    print(f"[{self.symbol}] Error submitting ask: {e}")

        self.open_bid_id = bid_id
        self.open_ask_id = ask_id

    def run(self, poll_interval=60):
        print(f"[{self.symbol}] Starting MM strategy with improved parameters")
        print(f"[{self.symbol}] Edge: $0.05, Base Qty: 3, Inventory Limit: 50")

        while True:
            try:
                self.update_position()
                df = self.get_latest_bar()

                sig_df = self.strategy.run(df)
                latest = sig_df.iloc[-1]

                # Validate strategy outputs
                bid_price = latest.get("bid_price")
                ask_price = latest.get("ask_price")
                bid_qty = latest.get("bid_qty", 0)
                ask_qty = latest.get("ask_qty", 0)
                bid_active = bool(latest.get("bid_active", False))
                ask_active = bool(latest.get("ask_active", False))
                
                # Check for invalid prices (NaN, None, or invalid values)
                if pd.isna(bid_price) or bid_price <= 0:
                    bid_active = False
                    print(f"[{self.symbol}] Invalid bid_price: {bid_price}")
                if pd.isna(ask_price) or ask_price <= 0:
                    ask_active = False
                    print(f"[{self.symbol}] Invalid ask_price: {ask_price}")
                
                # Check for invalid quantities
                if pd.isna(bid_qty) or bid_qty <= 0:
                    bid_active = False
                if pd.isna(ask_qty) or ask_qty <= 0:
                    ask_active = False
                
                # Check spread is reasonable (ask > bid)
                if bid_active and ask_active and ask_price <= bid_price:
                    print(f"[{self.symbol}] ⚠️  Invalid spread: bid={bid_price}, ask={ask_price}")
                    ask_active = False  # Disable ask if spread is invalid

                # Additional risk check: don't quote if position is too large
                max_position_risk = 100  # Hard limit
                if abs(self.position) > max_position_risk:
                    print(f"[{self.symbol}] ⚠️  Position too large ({self.position}), pausing quotes")
                    self.cancel_open_orders()
                    time.sleep(poll_interval)
                    continue

                self.cancel_open_orders()

                # Only submit if we have valid quotes
                if bid_active or ask_active:
                    self.submit_quote(
                        bid_price=bid_price,
                        bid_qty=int(bid_qty) if not pd.isna(bid_qty) else 0,
                        ask_price=ask_price,
                        ask_qty=int(ask_qty) if not pd.isna(ask_qty) else 0,
                        bid_active=bid_active,
                        ask_active=ask_active,
                    )

                # Calculate spread
                spread = latest["ask_price"] - latest["bid_price"]
                spread_pct = (spread / latest["Close"]) * 100 if latest["Close"] > 0 else 0

                print(
                    f"[{self.symbol}] {datetime.now()} | "
                    f"Pos={self.position:4d} | "
                    f"Bid=${latest['bid_price']:.2f} ({latest['bid_qty']}) | "
                    f"Ask=${latest['ask_price']:.2f} ({latest['ask_qty']}) | "
                    f"Spread=${spread:.2f} ({spread_pct:.2f}%) | "
                    f"Vol={latest['volatility']:.4f} | "
                    f"Fair=${latest.get('fair_price', latest['Close']):.2f}"
                )

                time.sleep(poll_interval)

            except Exception as e:
                print(f"[{self.symbol}] Error:", e)
                import traceback
                traceback.print_exc()
                time.sleep(5)


# ===============================
# MULTI-TICKER RUNNER
# ===============================

def start_market_maker(api_key, api_secret, symbol):
    strategy = PennyInPennyOutStrategy(
        tick_size=0.01,
        base_edge=0.05,              # Increased from 0.01 to account for costs
        edge_range=0.10,             # Increased range for volatility adjustments
        edge_sensitivity=2.0,         # Moderate sensitivity
        fair_ema_span=20,
        fair_median_window=30,
        vol_lookback=30,
        spread_vol_multiplier=0.7,
        min_spread=0.02,
        max_spread=0.50,
        fade_strength=0.04,           # Increased from 0.02 for better inventory management
        inventory_soft_limit=50,      # Reduced from 200 to limit risk
        base_qty=3,                    # Reduced from 5 to limit exposure
        max_quote_offset=0.30,
        vol_halt=0.08,                # Lower threshold - stop quoting in high vol
    )
    mm = AlpacaMarketMaker(api_key, api_secret, symbol, strategy)
    mm.run()


if __name__ == "__main__":
    API_KEY = os.environ["ALPACA_API_KEY"]
    API_SECRET = os.environ["ALPACA_API_SECRET"]

    symbols = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

    threads = []

    for sym in symbols:
        t = threading.Thread(target=start_market_maker, args=(API_KEY, API_SECRET, sym), daemon=True)
        t.start()
        threads.append(t)
        print(f"Started thread for {sym}")

    # Keep main thread alive
    while True:
        time.sleep(10)
