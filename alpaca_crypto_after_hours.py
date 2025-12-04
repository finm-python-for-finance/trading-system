import asyncio
import time
import datetime
import os
from dataclasses import dataclass, field
from typing import Dict, List

from alpaca.data.live import CryptoDataStream
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.trading.requests import MarketOrderRequest

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if API_KEY is None or SECRET_KEY is None:
    raise ValueError("Missing Alpaca API keys in environment variables.")

PAPER = True

# === Config ===
SYMBOLS: List[str] = ["BTC/USD", "ETH/USD"]  # just edit this list later

IMB_THRESHOLD = 0.25             # |OBI| must exceed this
MICRO_DEV_THRESHOLD = 0.0003     # 3 bps deviation
COOLDOWN_SECONDS = 5

MAX_TOTAL_NOTIONAL = 300      # total exposure across all symbols
MAX_NOTIONAL_PER_SYMBOL = 150 # per symbol cap
PER_TRADE_FRACTION_OF_BP = 0.01  # 10% of available buying power per trade

MIN_SPREAD_BPS = 0.5 / 10_000    # avoid weird quotes (too tight / crossed)

DAILY_LOSS_LIMIT = 100         # stop trading for the day if loss >= this (USD)


@dataclass
class SymbolState:
    position_side: str = "flat"   # "long", "short", "flat"
    last_trade_time: float = 0.0


@dataclass
class GlobalState:
    symbols: Dict[str, SymbolState] = field(default_factory=dict)
    trading_halted: bool = False
    start_equity: float = 0.0
    last_reset_date: str = ""     # YYYY-MM-DD


state = GlobalState(symbols={s: SymbolState() for s in SYMBOLS})

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=PAPER)


# ===== Helpers for account/positions/exposure =====

def get_account():
    return trading_client.get_account()

def get_equity() -> float:
    return float(get_account().equity)

def get_buying_power() -> float:
    return float(get_account().buying_power)

def get_position_qty(symbol: str) -> float:
    """Return current position quantity for a symbol (can be 0)."""
    try:
        pos = trading_client.get_open_position(symbol)
        return float(pos.qty)
    except Exception:
        # no position
        return 0.0

def get_position_notional(symbol: str) -> float:
    """Approximate notional of open position for a symbol (abs(value))."""
    try:
        pos = trading_client.get_open_position(symbol)
        return abs(float(pos.market_value))
    except Exception:
        return 0.0

def get_total_crypto_notional() -> float:
    """Sum notional across all symbols in SYMBOLS."""
    total = 0.0
    for s in SYMBOLS:
        total += get_position_notional(s)
    return total


# ===== Order sending =====

async def send_order(symbol: str, side: str, notional: float):
    if notional <= 0:
        return

    order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

    req = MarketOrderRequest(
        symbol=symbol,
        side=order_side,
        notional=notional,
        time_in_force=TimeInForce.IOC,
        type=OrderType.MARKET,
    )

    try:
        order = trading_client.submit_order(req)
        print(f"[ORDER] {symbol} {side.upper()} notional={notional:.2f} | id={order.id}")
    except Exception as e:
        print(f"[ORDER ERROR] {symbol} | {e}")


async def flip_to_long(symbol: str, notional: float):
    qty = get_position_qty(symbol)
    if qty < 0:
        # buy to cover
        await send_order(symbol, "buy", abs(qty) * 1.01)
    await send_order(symbol, "buy", notional)
    state.symbols[symbol].position_side = "long"
    state.symbols[symbol].last_trade_time = time.time()


async def flip_to_short(symbol: str, notional: float):
    qty = get_position_qty(symbol)
    if qty > 0:
        # sell to flatten
        await send_order(symbol, "sell", abs(qty) * 1.01)
    await send_order(symbol, "sell", notional)
    state.symbols[symbol].position_side = "short"
    state.symbols[symbol].last_trade_time = time.time()


async def flatten_symbol(symbol: str):
    qty = get_position_qty(symbol)
    if abs(qty) > 0:
        side = "sell" if qty > 0 else "buy"
        await send_order(symbol, side, abs(qty) * 1.01)
    state.symbols[symbol].position_side = "flat"
    state.symbols[symbol].last_trade_time = time.time()


async def flatten_all_symbols():
    print("[RISK] Flattening all symbols due to daily loss limit.")
    tasks = []
    for s in SYMBOLS:
        tasks.append(flatten_symbol(s))
    if tasks:
        await asyncio.gather(*tasks)


# ===== Daily loss limit logic =====

def maybe_reset_daily_equity():
    """Reset start_equity at the beginning of a new day."""
    today = datetime.date.today().isoformat()
    if state.last_reset_date != today:
        eq = get_equity()
        state.start_equity = eq
        state.last_reset_date = today
        state.trading_halted = False
        print(f"[INIT] New trading day {today}, start_equity={eq:.2f}")


def check_daily_loss_exceeded() -> bool:
    """Check whether daily loss limit is exceeded."""
    maybe_reset_daily_equity()
    current_eq = get_equity()
    loss = state.start_equity - current_eq
    print(f"[RISK] Equity={current_eq:.2f}, Start={state.start_equity:.2f}, Loss={loss:.2f}")
    return loss >= DAILY_LOSS_LIMIT


# ===== Signal computation =====

def compute_signals(bid, ask, bid_sz, ask_sz):
    mid = (bid + ask) / 2
    spread = ask - bid
    if bid_sz + ask_sz == 0 or mid <= 0:
        return None

    spread_bps = spread / mid
    if spread_bps < MIN_SPREAD_BPS:
        # ignore strange or "too perfect" quotes
        return None

    obi = (bid_sz - ask_sz) / (bid_sz + ask_sz)
    micro = (ask * bid_sz + bid * ask_sz) / (bid_sz + ask_sz)
    micro_dev = (micro - mid) / mid

    return {
        "mid": mid,
        "spread": spread,
        "obi": obi,
        "micro": micro,
        "micro_dev": micro_dev,
    }


# ===== Main quote handler =====

async def on_crypto_quote(q):
    symbol = q.symbol

    # Only handle symbols we track
    if symbol not in state.symbols:
        return

    # If already halted, do nothing
    if state.trading_halted:
        return

    # Check daily loss limit
    if check_daily_loss_exceeded():
        state.trading_halted = True
        print(f"[RISK] Daily loss limit {DAILY_LOSS_LIMIT:.2f} reached or exceeded. Halting trading for today.")
        await flatten_all_symbols()
        return

    bid = float(q.bid_price)
    ask = float(q.ask_price)
    bid_sz = float(q.bid_size)
    ask_sz = float(q.ask_size)

    signals = compute_signals(bid, ask, bid_sz, ask_sz)
    if signals is None:
        return

    obi = signals["obi"]
    micro_dev = signals["micro_dev"]
    mid = signals["mid"]

    now = time.time()
    sym_state = state.symbols[symbol]

    # Throttle per symbol
    if now - sym_state.last_trade_time < COOLDOWN_SECONDS:
        return

    # Determine desired direction
    desired = "flat"
    if obi > IMB_THRESHOLD and micro_dev > MICRO_DEV_THRESHOLD:
        desired = "long"
    elif obi < -IMB_THRESHOLD and micro_dev < -MICRO_DEV_THRESHOLD:
        desired = "short"

    if desired == "flat":
        # For now, don't auto-flatten; just skip.
        return

    # Risk check: total exposure
    total_notional = get_total_crypto_notional()
    if total_notional >= MAX_TOTAL_NOTIONAL:
        print(f"[RISK] Total notional {total_notional:.2f} >= limit {MAX_TOTAL_NOTIONAL}, skipping {symbol}")
        return

    # Risk check: per-symbol exposure
    symbol_notional = get_position_notional(symbol)
    if symbol_notional >= MAX_NOTIONAL_PER_SYMBOL:
        print(f"[RISK] {symbol} notional {symbol_notional:.2f} >= per-symbol limit {MAX_NOTIONAL_PER_SYMBOL}, skipping")
        return

    buying_power = get_buying_power()
    trade_notional = min(
        MAX_NOTIONAL_PER_SYMBOL - symbol_notional,
        MAX_TOTAL_NOTIONAL - total_notional,
        buying_power * PER_TRADE_FRACTION_OF_BP,
    )

    if trade_notional <= 0:
        print(f"[WARN] No trade notional available for {symbol}")
        return

    print(
        f"[SIGNAL] {symbol} desired={desired}, obi={obi:.3f}, "
        f"micro_dev={micro_dev:.5f}, mid={mid:.2f}, trade_notional={trade_notional:.2f}"
    )

    if desired == "long" and sym_state.position_side != "long":
        await flip_to_long(symbol, trade_notional)
    elif desired == "short" and sym_state.position_side != "short":
        await flip_to_short(symbol, trade_notional)


# ===== Main runner =====

async def main():
    # Initialize daily equity baseline
    maybe_reset_daily_equity()

    stream = CryptoDataStream(API_KEY, SECRET_KEY)

    # subscribe to quotes for all symbols
    stream.subscribe_quotes(on_crypto_quote, *SYMBOLS)

    print(f"Starting crypto HFT strategy on {SYMBOLS} (paper={PAPER})...")
    await stream.run()


if __name__ == "__main__":
    asyncio.run(main())
