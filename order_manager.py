import time

class OrderManager:
    """
    Validates and approves orders before they are sent to order book.
    """

    def __init__(self, capital=100000, max_position=500, max_orders_per_min=30):
        self.capital = capital
        self.max_position = max_position
        self.max_orders_per_min = max_orders_per_min
        self.order_timestamps = []
        self.current_position = 0

    def _check_capital(self, order):
        if order.side == "buy":
            return order.price * order.qty <= self.capital
        return True

    def _check_position_limit(self, order):
        if order.side == "buy":
            return self.current_position + order.qty <= self.max_position
        else:
            return self.current_position - order.qty >= -self.max_position

    def _check_order_rate(self):
        now = time.time()
        self.order_timestamps = [t for t in self.order_timestamps if now - t < 60]
        return len(self.order_timestamps) < self.max_orders_per_min

    def validate(self, order):
        if not self._check_capital(order):
            return False, "Not enough capital"
        if not self._check_position_limit(order):
            return False, "Position limit exceeded"
        if not self._check_order_rate():
            return False, "Order rate limit exceeded"

        # record approved order
        self.order_timestamps.append(time.time())

        # update position
        if order.side == "buy":
            self.current_position += order.qty
            self.capital -= order.price * order.qty
        else:
            self.current_position -= order.qty

        return True, "Order approved"


# Logging Gateway
import json

class OrderLoggingGateway:
    """
    Logs all order events: new, modified, canceled, filled.
    """

    def __init__(self, file_path="order_log.json"):
        self.file_path = file_path

    def log(self, event_type, data):
        event = {
            "event": event_type,
            "timestamp": time.time(),
            "data": data
        }
        with open(self.file_path, "a") as f:
            f.write(json.dumps(event) + "\n")
