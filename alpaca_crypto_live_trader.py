# alpaca_crypto_live_trader.py
# Purpose: 24/7 Crypto Live Paper Trading with PennyInPennyOut Strategy
# Symbol: BTC/USD
# Strategy: Market-making with limit orders

import time
import os
from datetime import datetime
import pandas as pd
from alpaca_trade_api import REST

from strategy_base import PennyInPennyOutStrategy

# =========================
# CONFIG
# =========================

API_KEY = os.environ.get("ALPACA_API_KEY")
API_SECRET = os.environ.get("ALPACA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"

SYMBOL = "BTC/USD"
TIMEFRAME = "1Min"
POLL_INTERVAL = 60

# Strategy parameters tuned for BTC/USD
# Strategy uses integer quantities, so we scale: 1 unit = 0.001 BTC (1 milliBTC)
BTC_UNIT_SCALE = 1000  # Convert BTC to units: multiply by this

STRATEGY_CONFIG = {
    "tick_size": 0.01,           # $0.01 minimum price increment
    "base_edge": 15.0,           # Increased from 5.0 to account for crypto volatility and costs
    "edge_range": 20.0,          # Increased range for volatility adjustments
    "edge_sensitivity": 2.5,     # Higher sensitivity for crypto volatility
    "base_qty": 1,               # Base quantity in units (1 unit = 0.001 BTC) - keep small
    "inventory_soft_limit": 5,    # Reduced from 10 - crypto is very volatile, limit exposure
    "fair_ema_span": 20,
    "fair_median_window": 30,
    "vol_lookback": 30,
    "spread_vol_multiplier": 0.8,  # Increased to account for wider crypto spreads
    "min_spread": 0.05,          # Increased minimum spread for crypto
    "max_spread": 1.00,          # Increased max spread for crypto volatility
    "fade_strength": 0.05,       # Increased from 0.02 - stronger fade for volatile assets
    "max_quote_offset": 0.50,
    "vol_halt": 0.08,            # Lower threshold - be more conservative in high vol
}

if API_KEY is None or API_SECRET is None:
    raise ValueError("❌ ALPACA_API_KEY or ALPACA_API_SECRET not set.")

api = REST(API_KEY, API_SECRET, BASE_URL)
strategy = PennyInPennyOutStrategy(**STRATEGY_CONFIG)

# =========================
# HELPER FUNCTIONS
# =========================

def get_position_qty():
    """Get current BTC position quantity"""
    try:
        pos = api.get_position(SYMBOL)
        return float(pos.qty)
    except:
        return 0.0

def get_equity():
    """Get current account equity"""
    acct = api.get_account()
    return float(acct.equity)

def get_latest_bars():
    """Fetch latest bars from Alpaca and format for strategy"""
    bars = api.get_crypto_bars(SYMBOL, TIMEFRAME, limit=50).df
    
    # Handle MultiIndex if present (Alpaca sometimes returns MultiIndex)
    if isinstance(bars.index, pd.MultiIndex):
        if "symbol" in bars.index.names:
            bars = bars.xs(SYMBOL, level="symbol")
        else:
            bars = bars.xs(SYMBOL, level=-1)
    
    # Map Alpaca lowercase columns to strategy uppercase columns
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

def cancel_open_orders():
    """Cancel all open orders for the symbol"""
    try:
        orders = api.list_orders(status="open")
        for order in orders:
            if order.symbol == SYMBOL:
                api.cancel_order(order.id)
                print(f"Cancelled order: {order.id}")
    except Exception as e:
        print(f"Error canceling orders: {e}")

def submit_quote(bid_price, bid_qty_btc, ask_price, ask_qty_btc, bid_active, ask_active):
    """Submit bid/ask limit orders based on strategy signals"""
    if bid_active and pd.notna(bid_price) and bid_qty_btc > 0:
        try:
            order = api.submit_order(
                symbol=SYMBOL,
                qty=round(float(bid_qty_btc), 6),
                side="buy",
                type="limit",
                limit_price=round(float(bid_price), 2),
                time_in_force="gtc"
            )
            print(f"BID ORDER | Buy {bid_qty_btc:.6f} BTC @ ${bid_price:.2f} | id={order.id}")
        except Exception as e:
            print(f"Error submitting bid: {e}")
    
    if ask_active and pd.notna(ask_price) and ask_qty_btc > 0:
        try:
            order = api.submit_order(
                symbol=SYMBOL,
                qty=round(float(ask_qty_btc), 6),
                side="sell",
                type="limit",
                limit_price=round(float(ask_price), 2),
                time_in_force="gtc"
            )
            print(f"ASK ORDER | Sell {ask_qty_btc:.6f} BTC @ ${ask_price:.2f} | id={order.id}")
        except Exception as e:
            print(f"Error submitting ask: {e}")

# =========================
# MAIN LOOP
# =========================
while True:
    try:
        # Update position and strategy context
        pos_qty_btc = get_position_qty()
        pos_units = int(pos_qty_btc * BTC_UNIT_SCALE)  # Convert BTC to units for strategy
        strategy.update_context(pos_units)  # Tell strategy about current position
        
        equity = get_equity()
        
        # Get market data and run strategy
        df = get_latest_bars()
        sig_df = strategy.run(df)  # Strategy calculates indicators and bid/ask prices
        latest = sig_df.iloc[-1]   # Get latest row with all signals
        
        # Cancel old orders before submitting new ones
        cancel_open_orders()
        
        # Extract strategy signals (bid/ask prices and quantities)
        bid_price = latest["bid_price"]
        ask_price = latest["ask_price"]
        bid_qty_units = int(latest["bid_qty"])  # Strategy returns integer units
        ask_qty_units = int(latest["ask_qty"])  # Strategy returns integer units
        bid_active = bool(latest["bid_active"])
        ask_active = bool(latest["ask_active"])
        
        # Convert strategy quantities back to BTC (units -> BTC)
        bid_qty_btc = bid_qty_units / BTC_UNIT_SCALE
        ask_qty_btc = ask_qty_units / BTC_UNIT_SCALE
        
        # Submit new quotes based on strategy signals
        submit_quote(
            bid_price=bid_price,
            bid_qty_btc=bid_qty_btc,
            ask_price=ask_price,
            ask_qty_btc=ask_qty_btc,
            bid_active=bid_active,
            ask_active=ask_active,
        )
        
        # Calculate spread and risk metrics
        spread = ask_price - bid_price
        spread_pct = (spread / latest['Close']) * 100 if latest['Close'] > 0 else 0
        position_value = pos_qty_btc * latest['Close']
        position_pct = (position_value / equity) * 100 if equity > 0 else 0
        
        # Status print with enhanced metrics
        print(
            f"[{datetime.now()}] "
            f"Pos={pos_qty_btc:.6f} BTC ({pos_units} units, ${position_value:.2f}, {position_pct:.1f}%) | "
            f"Equity=${equity:.2f} | "
            f"Bid=${bid_price:.2f} ({bid_qty_btc:.6f} BTC) | "
            f"Ask=${ask_price:.2f} ({ask_qty_btc:.6f} BTC) | "
            f"Spread=${spread:.2f} ({spread_pct:.3f}%) | "
            f"Vol={latest['volatility']:.6f} | "
            f"Fair=${latest['fair_price']:.2f}"
        )
        
        # Risk warning
        if abs(position_pct) > 10:
            print(f"⚠️  WARNING: Position is {abs(position_pct):.1f}% of equity - consider reducing exposure")
        if latest['volatility'] > 0.15:
            print(f"⚠️  WARNING: High volatility ({latest['volatility']:.4f}) - strategy may halt quoting")
        
        time.sleep(POLL_INTERVAL)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(10)
