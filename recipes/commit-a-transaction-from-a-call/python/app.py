"""Commit a transaction from a call.

Three tools, one write. `set_order` records what the caller wants in
`global_data` and marks it unconfirmed. `confirm_order` reads the order back
and marks it confirmed. `commit_order` writes it, once, and only when the
confirmation is on record. The model proposes each step; the handlers decide
whether the step is allowed, and nothing reaches the order book before the
caller has confirmed.

The handlers read state from `global_data` in `raw_data`, the copy the
platform posts with every tool call, not from anything the model says.

Written against signalwire-sdk 3.0.1.
"""
import os

from dotenv import load_dotenv
from signalwire import AgentBase, FunctionResult

# the SDK does not read .env for you
load_dotenv()

MENU = {"cargo-rack": 45.00, "puncture-kit": 12.50, "helmet": 89.00}

# The order book. Keyed by call id, so a call can commit exactly once. A real
# handler writes to your order system here.
ORDERS = {}


class OrderAgent(AgentBase):
    def __init__(self):
        super().__init__(name="orders", route="/orders")
        self.prompt_add_section(
            "Role",
            "You take accessory orders for Ridgeline Cycles. Use set_order when "
            "the caller says what they want, confirm_order to read it back, and "
            "commit_order only after they agree to the total.",
        )

    @AgentBase.tool(
        name="set_order",
        description="Record the items the caller wants. Replaces any earlier list.",
        parameters={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string", "enum": sorted(MENU)},
                    "description": "Catalogue item names.",
                }
            },
            "required": ["items"],
        },
    )
    def set_order(self, args, raw_data):
        items = [i for i in (args.get("items") or []) if i in MENU]
        if not items:
            return FunctionResult("INVALID: none of those are catalogue items. "
                                  "Offer the catalogue.")
        total = round(sum(MENU[i] for i in items), 2)
        r = FunctionResult(f"Order noted: {', '.join(items)}, total {total:.2f}. "
                           "Read it back and ask the caller to confirm.")
        # any new list resets the confirmation
        r.add_action("set_global_data", {"order": {"items": items, "total": total},
                                         "confirmed": False})
        return r

    @AgentBase.tool(
        name="confirm_order",
        description="Record that the caller agreed to the items and the total.",
        parameters={"type": "object", "properties": {}},
    )
    def confirm_order(self, args, raw_data):
        order = ((raw_data or {}).get("global_data") or {}).get("order")
        if not order:
            return FunctionResult("INCOMPLETE: there is no order to confirm yet.")
        r = FunctionResult(f"Confirmed: {', '.join(order['items'])} for "
                           f"{order['total']:.2f}. You may commit it now.")
        r.add_action("set_global_data", {"confirmed": True})
        return r

    @AgentBase.tool(
        name="commit_order",
        description="Place the confirmed order. Only after confirm_order.",
        parameters={"type": "object", "properties": {}},
    )
    def commit_order(self, args, raw_data):
        raw = raw_data or {}
        data = raw.get("global_data") or {}
        call_id = raw.get("call_id")
        if call_id in ORDERS:
            # the model asked twice; the book already has it
            return FunctionResult(f"ALREADY_PLACED: order {ORDERS[call_id]['id']} "
                                  "is on file. Do not place it again.")
        if not data.get("order"):
            return FunctionResult("INCOMPLETE: take the order first.")
        if data.get("confirmed") is not True:
            return FunctionResult("NOT_CONFIRMED: read the order back and get a yes "
                                  "before committing.")
        order_id = f"RC-{len(ORDERS) + 1001}"
        ORDERS[call_id] = {"id": order_id, **data["order"]}
        r = FunctionResult(f"Placed as {order_id}. Tell the caller the number.")
        r.add_action("set_global_data", {"order_id": order_id})
        return r


agent = OrderAgent()

if __name__ == "__main__":
    agent.serve(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
