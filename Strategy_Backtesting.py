import pandas as pd
import numpy as np

class Backtester:
    """
    Integrates:
    - MarketDataGateway
    - Strategy (signals)
    - OrderManager
    - OrderBook
    - MatchingEngine
    - Logging
    """

    def __init__(
        self,
        data_gateway,
        strategy,
        order_manager,
        order_book,
        matching_engine,
        logger=None
    ):
        self.data_gateway = data_gateway
        self.strategy = strategy
        self.order_manager = order_manager
        self.order_book = order_book
        self.matching_engine = matching_engine
        self.logger = logger

        self.trades = []      # store executed trades
        self.equity_curve = [] # track portfolio value over time
        self.position = 0
        self.cash = 100000  # initial capital
        self.portfolio_value = self.cash
        self.last_price = None

        self.market_df = []   # store data for strategy

    def _execute_order(self, order):
        """
        Send order to matching engine to simulate execution.
        """
        result = self.matching_engine.simulate_execution(order)

        if result["status"] == "filled" or result["status"] == "partial":
            fill_qty = result["filled_qty"]
            fill_price = order.price

            # update cash & position
            if order.side == "buy":
                self.position += fill_qty
                self.cash -= fill_price * fill_qty
            else:
                self.position -= fill_qty
                self.cash += fill_price * fill_qty

            # record trade
            self.trades.append({
                "timestamp": pd.Timestamp.now(),
                "side": order.side,
                "price": fill_price,
                "qty": fill_qty,
                "status": result["status"]
            })

        if self.logger:
            self.logger.log("execution", result)

        return result

    def _update_equity(self, price):
        """
        Update portfolio value based on price.
        """
        self.last_price = price
        self.portfolio_value = self.cash + self.position * price
        self.equity_curve.append(self.portfolio_value)

    def run(self):
        """
        Main backtest loop.
        Steps:
          1. Feed market data
          2. Accumulate DF for indicator calc
          3. Generate signals
          4. Submit orders
          5. Match with engine
          6. Track PnL
        """

        for row in self.data_gateway.stream():
            self.market_df.append(row)
            df = pd.DataFrame(self.market_df)

            # must ensure strategy indicators are computable
            df = self.strategy.run(df)

            # get latest signal (1=buy, -1=sell, 0=hold)
            signal = df.iloc[-1]["signal"]
            price = df.iloc[-1]["Close"]

            # update portfolio value with latest market price
            self._update_equity(price)

            # no trade signal
            if signal == 0:
                continue

            # Create order
            from order_book import Order
            order = Order(
                order_id=f"order_{len(self.trades)}",
                side="buy" if signal == 1 else "sell",
                price=price,
                qty=10   # fixed size or configurable
            )

            # Validate
            ok, msg = self.order_manager.validate(order)
            if not ok:
                if self.logger:
                    self.logger.log("rejected", {"reason": msg, "order_id": order.order_id})
                continue

            # Add to order book
            self.order_book.add_order(order)
            if self.logger:
                self.logger.log("submitted", order.__dict__)

            # Simulate execution
            exec_result = self._execute_order(order)

        return pd.DataFrame(self.equity_curve, columns=["equity"])


class PerformanceAnalyzer:
    def __init__(self, equity_curve, trades):
        self.equity_curve = equity_curve
        self.trades = trades

    def pnl(self):
        return self.equity_curve[-1] - self.equity_curve[0]

    def returns(self):
        eq = np.array(self.equity_curve)
        return np.diff(eq) / eq[:-1]

    def sharpe(self, rf=0.0):
        r = self.returns()
        if r.std() == 0:
            return 0
        return (r.mean() - rf) / r.std() * np.sqrt(252 * 6.5 * 60)  # intraday scaling

    def max_drawdown(self):
        eq = np.array(self.equity_curve)
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / peak
        return dd.min()

    def win_rate(self):
        wins = 0
        losses = 0
        for t in self.trades:
            if t["side"] == "buy":
                # wins determined on sell?
                continue
        # simplified win rate
        return None


import matplotlib.pyplot as plt

def plot_equity(equity_df):
    plt.figure(figsize=(12,4))
    plt.plot(equity_df["equity"])
    plt.title("Equity Curve")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")
    plt.grid(True)
    plt.show()

from strategy_base import MovingAverageStrategy
from gateway import MarketDataGateway
from order_book import OrderBook
from order_manager import OrderManager
from matching_engine import MatchingEngine
from order_manager import OrderLoggingGateway

# Components
data_gateway = MarketDataGateway("clean_data_stock/AAPL_1m_clean.csv")
strategy = MovingAverageStrategy(20, 60)
order_manager = OrderManager()
order_book = OrderBook()
matching_engine = MatchingEngine()
logger = OrderLoggingGateway("order_log.json")

# Backtester
bt = Backtester(
    data_gateway,
    strategy,
    order_manager,
    order_book,
    matching_engine,
    logger
)

equity_df = bt.run()

# Analyze
pa = PerformanceAnalyzer(equity_df["equity"].tolist(), bt.trades)
print("PnL:", pa.pnl())
print("Sharpe:", pa.sharpe())
print("Max Drawdown:", pa.max_drawdown())

plot_equity(equity_df)
