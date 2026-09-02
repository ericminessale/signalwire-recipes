"""Push events from an agent to the browser.

A tool result can carry a SWML `user_event`, whose `event` is any JSON object.
The bundled schema describes it as sending events "to the connected client on
the call", which is how an agent talking to a Browser SDK client drives the
page: the handler decides what happened and the event carries the facts, not
the model's paraphrase of them.

`FunctionResult.swml_user_event(event)` wraps the verb in a one-verb SWML
document and adds it as a `SWML` action. The same event can also be pushed
from your backend with the REST command `calling.user_event`.

Written against signalwire-sdk 3.0.1.
"""
import os

from dotenv import load_dotenv
from signalwire import AgentBase, FunctionResult

# the SDK does not read .env for you
load_dotenv()

SLOTS = {"thu-14": "Thursday 2pm", "fri-10": "Friday 10am", "sat-09": "Saturday 9am"}


class BookingAgent(AgentBase):
    def __init__(self):
        super().__init__(name="booking", route="/booking")
        self.prompt_add_section(
            "Role",
            "You book workshop slots for Ridgeline Cycles from a web page that "
            "shows the available times. Use hold_slot when the caller picks one.",
        )

    @AgentBase.tool(
        name="hold_slot",
        description="Hold a workshop slot the caller has chosen.",
        parameters={
            "type": "object",
            "properties": {"slot": {"type": "string", "enum": sorted(SLOTS),
                                    "description": "The slot id shown on the page."}},
            "required": ["slot"],
        },
    )
    def hold_slot(self, args, raw_data):
        slot = args.get("slot")
        if slot not in SLOTS:
            return FunctionResult("INVALID: that slot is not on the page.")
        # the page gets the facts as data; the model gets a sentence
        return FunctionResult(
            f"Holding {SLOTS[slot]} for the caller."
        ).swml_user_event({"type": "slot_held", "slot": slot,
                           "label": SLOTS[slot], "held_for_seconds": 300})


agent = BookingAgent()

if __name__ == "__main__":
    agent.serve(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
