"""Scope an agent's tools per step.

Each step declares exactly which functions exist while it is active. A tool the
step does not list is not withheld from the model - it is not presented at all.
"""
import os

from signalwire_agents import AgentBase


class IntakeAgent(AgentBase):
    def __init__(self):
        super().__init__(name="intake", route="/intake")

        contexts = self.define_contexts()
        flow = contexts.add_context("default")

        # Step one: the only thing that exists here is save_name.
        flow.add_step("collect_name") \
            .add_section("Goal", "Ask for the caller's full name.") \
            .set_functions(["save_name"]) \
            .set_valid_steps(["collect_reason"])

        # Step two: transferring becomes possible only now.
        flow.add_step("collect_reason") \
            .add_section("Goal", "Ask why they are calling, then route them.") \
            .set_functions(["save_reason", "transfer_to_human"]) \
            .set_valid_steps(["done"])

    @AgentBase.tool(description="Record the caller's name")
    def save_name(self, args, raw_data):
        name = (args.get("name") or "").strip()
        if not name:
            return self.result("I did not catch that - could you repeat your name?")
        # The handler advances the step, so ordering does not rely on the model.
        return self.result(f"Thank you {name}.").swml_change_step("collect_reason")

    @AgentBase.tool(description="Record why the caller is calling")
    def save_reason(self, args, raw_data):
        return self.result("Got it.")

    @AgentBase.tool(description="Connect the caller to a human agent")
    def transfer_to_human(self, args, raw_data):
        return self.result("Connecting you now.").connect("/private/support-queue")


if __name__ == "__main__":
    IntakeAgent().serve(port=int(os.getenv("PORT", "8080")))
