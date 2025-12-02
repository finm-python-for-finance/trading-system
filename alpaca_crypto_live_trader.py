# alpaca_crypto_live_trader.py
# Purpose: 24/7 Crypto Live Paper Trading Test (NO BARS API)
# Symbol: BTC/USD
# Order Type: MARKET

import time
import os
from datetime import datetime
from alpaca_trade_api import REST

# =========================
# CONFIG
# =========================

API_KEY = os.environ.get("ALPACA_API_KEY")
API_SECRET = os.environ.get("ALPACA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"

SYMBOL = "BTC/USD"
QTY = 0.001
POLL_INTERVAL = 60

if API_KEY is None or API_SECRET is None:
    raise ValueError("❌ ALPACA_API_KEY or ALPACA_API_SECRET not set.")

api = REST(API_KEY, API_SECRET, BASE_URL)

# =========================
# HELPER FUNCTIONS
# =========================

def get_position_qty():
    try:
        pos = api.get_position(SYMBOL)
        return float(pos.qty)
    except:
        return 0.0

def get_equity():
    acct = api.get_account()
    return float(acct.equity)

def submit_market_order(side, qty):
    order = api.submit_order(
        symbol=SYMBOL,
        qty=round(float(qty), 4),
        side=side,
        type="market",
        time_in_force="gtc"
    )
    print(f"✅ ORDER SENT | {side.upper()} {qty} {SYMBOL} | id={order.id}")

# =========================
# MAIN LIVE LOOP
# =========================

print("===================================")
print("🚀 Alpaca Crypto Live Paper Trader")
print("Symbol:", SYMBOL)
print("===================================")

last_side = None

while True:
    try:
        pos_qty = get_position_qty()
        equity = get_equity()

        print(
            f"[{datetime.now()}] "
            f"Position={pos_qty:.4f} | "
            f"Equity={equity}"
        )

        # 強制交替買賣，用來驗證 PnL 一定會動
        if pos_qty == 0:
            submit_market_order("buy", QTY)
            last_side = "buy"

        elif last_side == "buy":
            submit_market_order("sell", QTY)
            last_side = "sell"

        elif last_side == "sell":
            submit_market_order("buy", QTY)
            last_side = "buy"

        time.sleep(POLL_INTERVAL)

    except Exception as e:
        print("⚠️ ERROR:", e)
        time.sleep(10)
