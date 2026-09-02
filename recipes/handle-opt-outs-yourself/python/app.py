"""Handle opt-outs yourself.

SignalWire does not manage STOP for you. The platform messaging page says
"Customers are responsible for handling inbound stop requests and removing
those customers from subscriber lists." It adds that messages should not go
out again "unless they have opted back in via an Unstop request"
(https://signalwire.com/docs/platform/messaging). So a handler of yours
receives the inbound message webhook and records the opt-out. Every later
send checks that record before it makes a request.

The inbound webhook is the SWML inbound message webhook: SignalWire POSTs a
JSON body whose `message` carries `from`, `to` and `body`, and expects a SWML
document back. A STOP gets a one-verb document, `send_sms`, confirming the
opt-out; START or UNSTOP gets one confirming the return. Anything else gets an
empty document, which sends nothing.

Written against signalwire-sdk 3.0.1 (RestClient) and Flask.
"""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()

# 3.0.1 wraps no method for POST /api/messaging/messages, so the send goes
# through the HTTP client every namespace shares
http = client._http

FROM = os.getenv("SMS_FROM")
if not FROM:
    raise SystemExit("SMS_FROM is required: the purchased number your sends go out from")

# the single words this handler honours, compared whole after trim and lowercase
STOP_WORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
START_WORDS = {"start", "unstop"}
STOPPED = ("You are unsubscribed from Ridgeline Cycles messages. "
           "Reply START to opt back in.")
RESUMED = "You are opted back in to Ridgeline Cycles messages. Reply STOP at any time."

# number -> when it opted out; swap for your database
OPT_OUTS = {}


class OptedOut(Exception):
    """Raised before any request is made."""


def keyword(body):
    return (body or "").strip().lower()


def reply(from_number, to_number, body):
    """A SWML document with one verb: the confirmation text."""
    sms = {"from_number": from_number, "to_number": to_number, "body": body}
    return {"version": "1.0.0", "sections": {"main": [{"send_sms": sms}]}}


def handle_inbound(message):
    """Record STOP or START and return the SWML document to run.

    `message` is the webhook's `message` object. Any other text returns an
    empty document, which sends nothing and records nothing."""
    word = keyword(message.get("body"))
    sender, ours = message["from"], message["to"]
    if word in STOP_WORDS:
        OPT_OUTS[sender] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return reply(ours, sender, STOPPED)
    if word in START_WORDS:
        OPT_OUTS.pop(sender, None)
        return reply(ours, sender, RESUMED)
    return {"version": "1.0.0", "sections": {"main": []}}


def send(to, body):
    """Every outbound send checks the record first. A refused send makes no request."""
    if to in OPT_OUTS:
        raise OptedOut(f"{to} opted out at {OPT_OUTS[to]}; no message sent")
    message = {"to": to, "from": FROM, "body": body}
    return http.post("/api/messaging/messages", body=message)


app = Flask(__name__)


@app.post("/inbound")
def inbound():
    payload = request.get_json(force=True)
    return jsonify(handle_inbound(payload["message"]))


@app.post("/send")
def outbound():
    """Your send path, in the process that holds the record. Put it behind
    your own authentication before anything else can reach it."""
    payload = request.get_json(force=True)
    try:
        sent = send(payload["to"], payload["body"])
    except OptedOut as e:
        return jsonify({"sent": False, "reason": str(e)}), 403
    return jsonify({"sent": True, "id": sent.get("id")}), 202


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "8080")))
