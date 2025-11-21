# Algorithmic Trading Backtesting Framework 🧠💹

This repository implements a modular, extensible **algorithmic trading backtesting system**, designed to simulate real-world trading environments including market data streaming, order management, matching, and strategy evaluation.

The project is divided into **three main parts**:

---

# 📦 Project Structure

- clean_data_crypto/
- clean_data_stock/
- raw_data_crypto/
- raw_data_stock/
- cleaning.ipynb
- fetch_data_crypto.ipynb
- fetch_data_stock.ipynb
- strategy_base.py
- gateway.py
- matching_engine.py
- order_book.py
- order_manager.py
- Strategy_Backtesting.py
- Readme.md


---

# 🔍 Part 1 — Data cleaning and Strategy Architecture

## 📥 1. Data Gathering  
Files:
- `fetch_data_stock.ipynb`
- `fetch_data_crypto.ipynb`

This stage automatically downloads raw intraday market data.

### Features:
✔ Fetch **stock data** using `yfinance`  
✔ Fetch **crypto data** from exchange APIs (e.g., Binance)  
✔ Save raw tick/interval data into:
- raw_data_stock/
- raw_data_crypto/

### The downloaded dataset includes:
- Datetime  
- Open / High / Low / Close  
- Volume  
- (Exchange-specific fields if available)

### Example (Stock via yfinance):
```python
import yfinance as yf

data = yf.download(
    tickers="AAPL",
    period="7d",
    interval="1m"
)
data.to_csv("raw_data_stock/AAPL_raw.csv")
```

---

## 🧹 **Data Cleaning**

markdown
## 🧹 2. Data Cleaning  
File:
- `cleaning.ipynb`

This stage prepares raw market data for modeling and backtesting.

### Features:
✔ Remove missing or corrupted rows  
✔ Remove duplicated timestamps  
✔ Convert timestamp column to `datetime`  
✔ Chronologically sort the dataset  
✔ Optional: add derived features (returns, rolling metrics)

### Cleaned data is saved to:
- clean_data_stock/
- clean_data_crypto/

### Example:
```python
import pandas as pd

df = pd.read_csv("raw_data_stock/AAPL_raw.csv")

df.dropna(inplace=True)
df.drop_duplicates(inplace=True)
df["Datetime"] = pd.to_datetime(df["Datetime"])
df.sort_values("Datetime", inplace=True)

df.to_csv("clean_data_stock/AAPL_clean.csv", index=False)
```

## 🔍 3. Strategy Architecture

### Files:
- `strategy_base.py`
- `Strategy_Backtesting.py` (strategy logic + MA crossover)

### Features:
✔ Base `Strategy` class  
✔ `MovingAverageStrategy` derived from the base class  
✔ Supports:
- Indicator generation  
- Signal generation  
- Extensible architecture for future ML, momentum, sentiment models  

---

# 🔁 Part 2 — Trading System Components

This section simulates a simplified exchange and trading flow.

### Files:
- `gateway.py`
- `order_book.py`
- `order_manager.py`
- `matching_engine.py`

### Components:

## 🧩 Market Data Gateway (`gateway.py`)
Simulates **live market data feed** using historical CSV data.
- Reads cleaned market data
- Streams candles tick-by-tick
- Provides `get_next()` and generator-based streaming

---

## 📈 Order Book (`order_book.py`)
Implements a **price-time priority matching engine**.
- Bid/ask stored using heaps (priority queues)
- Supports:
  - Add order  
  - Modify order  
  - Cancel order  
  - Match order  

Receives validated orders and performs matching when bid ≥ ask.

---

## 📤 Order Manager (`order_manager.py`)
Validates orders before they enter the exchange.
- Capital sufficiency checks  
- Position limit control  
- Order rate per minute limit  
- Updates cash & positions  
- Interfaces with audit logging system

---

## ⚙️ Matching Engine (`matching_engine.py`)
Simulates realistic exchange execution behavior:
- Full fills  
- Partial fills  
- Random cancellations/rejections  

Execution outcomes are returned to the backtester.

---

# 📊 Part 3 — Backtesting Engine

### File:
- `Strategy_Backtesting.py`

### Responsibilities:
The backtesting engine integrates all components to simulate real-world trading.

✔ Feeds live data → strategy generates signals  
✔ Submits orders → validated by OrderManager  
✔ Orders enter OrderBook → executed by MatchingEngine  
✔ Logs every execution  
✔ Tracks:
- Cash  
- Positions  
- Equity curve  
- Realized P&L  

---

# 📈 Performance & Reporting

The backtester outputs:
- **Equity curve**  
- **PnL**  
- **Sharpe ratio**  
- **Maximum drawdown**  
- **Trade log**  

Visualization functions are included (matplotlib).

---

# 🚀 How to Run

### 1. Prepare cleaned historical data  
Use `fetch_data_*.ipynb` and `cleaning.ipynb` to download and prepare stock or crypto data.

### 2. Run backtest:
```python
from gateway import MarketDataGateway
from strategy_base import MovingAverageStrategy
from order_book import OrderBook
from order_manager import OrderManager
from matching_engine import MatchingEngine
from Strategy_Backtesting import Backtester

data = MarketDataGateway("clean_data_stock/AAPL_clean.csv")
strategy = MovingAverageStrategy(short_window=20, long_window=60)
order_manager = OrderManager()
order_book = OrderBook()
matching_engine = MatchingEngine()

bt = Backtester(
    data_gateway=data,
    strategy=strategy,
    order_manager=order_manager,
    order_book=order_book,
    matching_engine=matching_engine
)

equity = bt.run()
equity.plot()

