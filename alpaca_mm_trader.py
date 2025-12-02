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
        except Exception:
            self.position = 0

        # Notify strategy of current exposure
        self.strategy.update_context(self.position)

    def get_latest_bar(self):
        bars = self.api.get_bars(self.symbol, self.timeframe, limit=50).df

        # 有些情況 bars 會是 MultiIndex（含 symbol），先切出單一 ticker
        if isinstance(bars.index, pd.MultiIndex):
            # 通常 symbol 是 index 的其中一層
            if "symbol" in bars.index.names:
                bars = bars.xs(self.symbol, level="symbol")
            else:
                # 保守做法：取最後一層為 symbol
                bars = bars.xs(self.symbol, level=-1)

        # 把 alpaca 的小寫欄位補成策略常用的大寫欄位
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


    def cancel_open_orders(self):
        orders = self.api.list_orders(status="open")
        for o in orders:
            if o.symbol == self.symbol:
                self.api.cancel_order(o.id)

    def submit_quote(self, bid_price, bid_qty, ask_price, ask_qty, bid_active, ask_active):
        bid_id = None
        ask_id = None

        if bid_active:
            bid_id = self.api.submit_order(
                symbol=self.symbol,
                qty=bid_qty,
                side="buy",
                type="limit",
                limit_price=float(bid_price),
                time_in_force="gtc"
            ).id

        if ask_active:
            ask_id = self.api.submit_order(
                symbol=self.symbol,
                qty=ask_qty,
                side="sell",
                type="limit",
                limit_price=float(ask_price),
                time_in_force="gtc"
            ).id

        self.open_bid_id = bid_id
        self.open_ask_id = ask_id

    def run(self, poll_interval=60):
        print(f"[{self.symbol}] Starting MM strategy")

        while True:
            try:
                self.update_position()
                df = self.get_latest_bar()

                sig_df = self.strategy.run(df)
                latest = sig_df.iloc[-1]

                self.cancel_open_orders()

                self.submit_quote(
                    bid_price=latest["bid_price"],
                    bid_qty=int(latest["bid_qty"]),
                    ask_price=latest["ask_price"],
                    ask_qty=int(latest["ask_qty"]),
                    bid_active=bool(latest["bid_active"]),
                    ask_active=bool(latest["ask_active"]),
                )

                print(
                    f"[{self.symbol}] {datetime.now()} | Pos={self.position} "
                    f"Bid={latest['bid_price']} ({latest['bid_qty']}) "
                    f"Ask={latest['ask_price']} ({latest['ask_qty']}) "
                    f"Vol={latest['volatility']:.4f}"
                )

                time.sleep(poll_interval)

            except Exception as e:
                print(f"[{self.symbol}] Error:", e)
                time.sleep(5)


# ===============================
# MULTI-TICKER RUNNER
# ===============================

def start_market_maker(api_key, api_secret, symbol):
    strategy = PennyInPennyOutStrategy()
    mm = AlpacaMarketMaker(api_key, api_secret, symbol, strategy)
    mm.run()


if __name__ == "__main__":
    API_KEY = os.environ["ALPACA_API_KEY"]
    API_SECRET = os.environ["ALPACA_API_SECRET"]

    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

    threads = []

    for sym in symbols:
        t = threading.Thread(target=start_market_maker, args=(API_KEY, API_SECRET, sym), daemon=True)
        t.start()
        threads.append(t)
        print(f"Started thread for {sym}")

    # Keep main thread alive
    while True:
        time.sleep(10)
