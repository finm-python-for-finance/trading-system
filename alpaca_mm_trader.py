# alpaca_mm_trader.py
import time
import pandas as pd
from alpaca_trade_api import REST
from datetime import datetime

class AlpacaMarketMaker:
    def __init__(self, api_key, api_secret, symbol, strategy, timeframe="1Min"):
        self.api = REST(api_key, api_secret, "https://paper-api.alpaca.markets")
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = strategy

        self.open_bid_id = None
        self.open_ask_id = None
        self.position = 0

    def update_position(self):
        pos = self.api.get_position(self.symbol)
        self.position = int(pos.qty) if pos else 0
        self.strategy.update_context(self.position)

    def get_latest_bar(self):
        bars = self.api.get_bars(self.symbol, self.timeframe, limit=50).df
        return bars

    def cancel_open_orders(self):
        orders = self.api.list_orders(status="open")
        for o in orders:
            if o.symbol == self.symbol:
                self.api.cancel_order(o.id)

    def submit_quote(self, bid_price, bid_qty, ask_price, ask_qty, bid_active, ask_active):
        # place bid
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
        print(f"Starting MM strategy on {self.symbol}")

        while True:
            try:
                # Update current position from Alpaca
                self.update_position()

                # Pull last 50 bars (needed for indicators)
                df = self.get_latest_bar()

                # Pass to strategy to compute bid/ask/etc.
                sig_df = self.strategy.run(df)
                latest = sig_df.iloc[-1]

                # Cancel old quotes
                self.cancel_open_orders()

                # Submit new ones
                self.submit_quote(
                    bid_price=latest["bid_price"],
                    bid_qty=int(latest["bid_qty"]),
                    ask_price=latest["ask_price"],
                    ask_qty=int(latest["ask_qty"]),
                    bid_active=bool(latest["bid_active"]),
                    ask_active=bool(latest["ask_active"]),
                )

                print(
                    f"{datetime.now()} — Position={self.position}, "
                    f"Bid={latest['bid_price']} ({latest['bid_qty']}), "
                    f"Ask={latest['ask_price']} ({latest['ask_qty']}), "
                    f"Vol={latest['volatility']:.4f}"
                )

                time.sleep(poll_interval)

            except Exception as e:
                print("Error:", e)
                time.sleep(5)

# RUN THE STRATEGY

from strategy_base import PennyInPennyOutStrategy

API_KEY = "PKXIA7CKD6OBEBWILMDF75XFX3"
API_SECRET = "4K5jgstrV21WemrKQwkYdhkKPTppsvtsJZ1WPvx2biyF"

strategy = PennyInPennyOutStrategy()

mm = AlpacaMarketMaker(
    api_key=API_KEY,
    api_secret=API_SECRET,
    symbol="AAPL",
    strategy=strategy
)

mm.run()
