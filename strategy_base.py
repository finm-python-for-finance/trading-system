import pandas as pd
import numpy as np

class Strategy:
    """
    Base Strategy Class
    Every strategy must implement:
      - add_indicators()
      - generate_signals()
    """

    def add_indicators(self, df):
        raise NotImplementedError("add_indicators() must be implemented.")

    def generate_signals(self, df):
        raise NotImplementedError("generate_signals() must be implemented.")

    def run(self, df):
        """
        Pipeline for all strategies.
        """
        df = df.copy()
        df = self.add_indicators(df)
        df = self.generate_signals(df)
        return df


class MovingAverageStrategy(Strategy):
    """
    True Moving Average Crossover Strategy:
    Buy only when short MA crosses ABOVE long MA.
    Sell only when short MA crosses BELOW long MA.
    """

    def __init__(self, short_window=20, long_window=60):
        self.short_window = short_window
        self.long_window = long_window

    def add_indicators(self, df):
        df["MA_short"] = df["Close"].rolling(self.short_window).mean()
        df["MA_long"] = df["Close"].rolling(self.long_window).mean()
        return df

    def generate_signals(self, df):
        # Initialize
        df["signal"] = 0

        # Condition for cross up (BUY)
        buy_signal = (
            (df["MA_short"].shift(1) <= df["MA_long"].shift(1)) &
            (df["MA_short"] > df["MA_long"])
        )

        # Condition for cross down (SELL)
        sell_signal = (
            (df["MA_short"].shift(1) >= df["MA_long"].shift(1)) &
            (df["MA_short"] < df["MA_long"])
        )

        df.loc[buy_signal, "signal"] = 1
        df.loc[sell_signal, "signal"] = -1

        # Position (持倉)：填滿非交易訊號日期
        df["position"] = df["signal"].replace(0, np.nan).ffill().fillna(0)

        return df
