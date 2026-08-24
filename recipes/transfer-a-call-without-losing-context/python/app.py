"""Transfer a call without losing context.

Intake writes to the shared call context; the receiving agent reads it on its first
turn. Nothing is serialised into the transfer target.
"""
import os

from signalwire_agents import AgentBase


class IntakeAgent(AgentBase):
    def __init__(self):
        super().__init__(name="intake", route="/intake")
        self.prompt_add_section(
            "Role", "Collect the caller's name and reason, then hand off."
        )

    @AgentBase.tool(description="Record the caller and route to a specialist")
    def route_caller(self, args, raw_data):
        name = (args.get("name") or "").strip()
        reason = (args.get("reason") or "").strip()
        # Written into the shared context - it survives the transfer.
        return (
            self.result("Thanks " + name + ", connecting you to billing.")
            .set_global_data(
                {"caller_name": name, "intake_reason": reason, "verified": True}
            )
            .connect("/private/billing-specialist")
        )


class BillingAgent(AgentBase):
    def __init__(self):
        super().__init__(name="billing", route="/billing-specialist")
        # The receiving agent reads context that already exists.
        self.prompt_add_section(
            "Context",
            "The caller is ${global_data.caller_name}. They already explained: "
            "${global_data.intake_reason}. They are already verified. Do not ask "
            "for their name or their reason again.",
        )


if __name__ == "__main__":
    IntakeAgent().serve(port=int(os.getenv("PORT", "8080")))
