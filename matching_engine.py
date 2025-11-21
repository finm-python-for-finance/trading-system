import random
from order_book import Order

class MatchingEngine:
    """
    Simulates execution outcome for orders.
    """

    def simulate_execution(self, order: Order):
        r = random.random()

        if r < 0.70:
            # full fill
            filled_qty = order.qty
            status = "filled"

        elif r < 0.90:
            # partial fill
            filled_qty = int(order.qty * random.uniform(0.1, 0.9))
            status = "partial"

        else:
            # rejected
            filled_qty = 0
            status = "cancelled"

        return {
            "order_id": order.order_id,
            "status": status,
            "filled_qty": filled_qty
        }
