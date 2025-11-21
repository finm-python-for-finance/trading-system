class MarketDataGateway:
    """
    Streams historical market data row-by-row to simulate real-time data.
    Supports both iterator and generator-based streaming.
    """

    def __init__(self, csv_path):
        self.data = pd.read_csv(csv_path, parse_dates=["Datetime"])
        self.data.sort_values("Datetime", inplace=True)
        self.length = len(self.data)
        self.pointer = 0

    # Iterator Methods

    def __iter__(self):
        """Reset and return iterator."""
        self.pointer = 0
        return self

    def __next__(self):
        """Return next row or raise StopIteration."""
        if self.pointer >= self.length:
            raise StopIteration

        row = self.data.iloc[self.pointer].to_dict()
        self.pointer += 1
        return row

    # Helper Methods

    def reset(self):
        """Reset pointer without recreating object."""
        self.pointer = 0

    def has_next(self):
        return self.pointer < self.length

    def get_next(self):
        """Safe wrapper around next(self)."""
        try:
            return next(self)
        except StopIteration:
            return None

    # Generator Methods

    def stream(self, delay=None, reset=False):
        """
        Generator version of the iterator stream.
        - delay: float seconds to wait between ticks
        - reset: if True, start from beginning
        """
        if reset:
            self.reset()

        while self.has_next():
            row = next(self)
            yield row

            if delay:
                time.sleep(delay)

