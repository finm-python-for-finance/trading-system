import pandas as pd

class MarketDataGateway:
    """
    Streams historical market data row-by-row to simulate real-time feed.
    """

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.data = pd.read_csv(csv_path, parse_dates=["Datetime"])
        self.data.sort_values("Datetime", inplace=True)
        self.pointer = 0
        self.length = len(self.data)

    def reset(self):
        self.pointer = 0

    def has_next(self):
        return self.pointer < self.length

    def get_next(self):
        """
        Returns next row as dict to simulate real-time update.
        """
        if not self.has_next():
            return None

        row = self.data.iloc[self.pointer].to_dict()
        self.pointer += 1
        return row

    def stream(self):
        """
        Generator for real-time streaming.
        """
        for i in range(self.pointer, self.length):
            yield self.data.iloc[i].to_dict()
