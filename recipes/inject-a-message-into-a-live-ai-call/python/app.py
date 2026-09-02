"""Inject a message into a live AI call.

One REST command, `calling.ai_message`, reaches into a conversation that is
already running. With `role: system` the text becomes an instruction the model
follows from its next turn; per the API reference the caller does not hear it.
The same command can merge keys into the session's `global_data`, or reset the
conversation with a new system prompt.

Your backend needs the call id, which every tool webhook and status callback
carries as `call_id`.

Written against signalwire-sdk 3.0.1 (RestClient.calling).
"""
import os

from dotenv import load_dotenv
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment when not passed explicitly.
client = RestClient()


def nudge(call_id, instruction):
    """A system message: the model follows it, the caller does not hear it."""
    return client.calling.ai_message(call_id, role="system",
                                     message_text=instruction)


def share(call_id, data):
    """Merge keys into the session's global_data mid-call."""
    return client.calling.ai_message(call_id, global_data=data)


def restart(call_id, system_prompt):
    """Drop the history and continue under a new system prompt."""
    return client.calling.ai_message(
        call_id, reset={"full_reset": True, "system_prompt": system_prompt})


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        raise SystemExit("usage: python app.py <call_id> <instruction>")
    print(nudge(sys.argv[1], " ".join(sys.argv[2:])))
