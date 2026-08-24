"""Hide fields from the model.

The record is loaded in full server-side. Only an explicit allowlist projection is
handed to the model, so withheld fields are absent rather than forbidden.
"""
import os

from signalwire_agents import AgentBase

# Everything the model is ever allowed to see about a customer.
EXPOSED = ("first_name", "plan", "renewal_date", "open_tickets")


def load_customer(phone):
    """Your system of record. Returns far more than the model should see."""
    return {
        "first_name": "Dana",
        "last_name": "Whitfield",
        "plan": "Business",
        "renewal_date": "2026-11-04",
        "open_tickets": 1,
        # --- none of the below is ever exposed ---
        "risk_score": 0.82,
        "margin_pct": 11.4,
        "internal_notes": "Threatened to churn in March. Do not offer a discount.",
        "card_last_four": "6411",
    }


class AccountAgent(AgentBase):
    def __init__(self):
        super().__init__(name="account", route="/account")
        self.prompt_add_section(
            "Role",
            "You help callers with their account. Answer only from the data given to "
            "you by tools. If a detail is absent, say you do not have it.",
        )

    @AgentBase.tool(description="Look up the calling customer's account")
    def get_account(self, args, raw_data):
        caller = (raw_data or {}).get("caller_id_num", "")
        record = load_customer(caller)
        # The projection is the security boundary.
        safe = {k: record[k] for k in EXPOSED if k in record}
        return self.result_data(safe)


if __name__ == "__main__":
    AccountAgent().serve(port=int(os.getenv("PORT", "8080")))
