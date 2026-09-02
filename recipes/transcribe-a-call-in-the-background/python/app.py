"""Transcribe a call in the background.

Two REST commands and one webhook. The vendored REST spec's `calling.transcribe`
variant takes `control_id`, required, and a `status_url`; `calling.transcribe.stop`
takes the same `control_id`. When the transcription is ready SignalWire POSTs
the transcribe status callback to `status_url`: `event_type` is
`calling.transcript.completed` or `calling.transcript.failed`, and
`params.text` is "The transcribed text of the call. Omitted when there is no
transcribed text."

The call itself carries on. Nothing here plays into it or waits on it; the
transcript is a document that arrives later.

Written against signalwire-sdk 3.0.1 (RestClient.calling) and Flask.
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()

STATUS_URL = os.getenv("TRANSCRIBE_STATUS_URL")
if not STATUS_URL:
    raise SystemExit("TRANSCRIBE_STATUS_URL is required; see .env.example")

CONTROL_ID = "call-transcript"

# call_id -> what arrived; swap for your database
TRANSCRIPTS = {}


def start(call_id):
    """Begin transcribing a live call. The transcript lands on STATUS_URL."""
    return client.calling.transcribe(call_id, control_id=CONTROL_ID, status_url=STATUS_URL)


def stop(call_id):
    """End it early. What was transcribed so far is what arrives."""
    return client.calling.transcribe_stop(call_id, control_id=CONTROL_ID)


def record(event):
    """One status callback. `text` is absent when nothing was transcribed."""
    params = event["params"]
    TRANSCRIPTS[params["call_id"]] = {
        "status": event["event_type"].rsplit(".", 1)[-1],   # completed | failed
        "text": params.get("text"),
        "at": event["timestamp"],
    }


app = Flask(__name__)


@app.post("/transcripts")
def status():
    record(request.get_json(force=True))
    return "", 204


@app.get("/transcripts/<call_id>")
def read(call_id):
    return jsonify(TRANSCRIPTS.get(call_id) or {"status": "pending", "text": None})


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] in ("start", "stop"):
        print((start if sys.argv[1] == "start" else stop)(sys.argv[2]))
    elif len(sys.argv) == 1:
        app.run(port=int(os.getenv("PORT", "8080")))
    else:
        raise SystemExit("usage: python app.py            (serve the status URL)\n"
                         "       python app.py start|stop <call_id>")
