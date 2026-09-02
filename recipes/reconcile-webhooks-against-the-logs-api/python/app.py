"""Reconcile webhooks against the logs API.

A status webhook can be missed: your host was down, a proxy timed out, a
deploy was mid-flight. The voice and message logs are the record of what the
platform did, so a scheduled pass over a time window catches anything your
webhook handler never saw. `GET /api/voice/logs` and `GET /api/messaging/logs`
take `created_after` and `created_before`; each voice log's events are one
more GET away.

Written against signalwire-sdk 3.0.1 (RestClient.logs).
"""
from dotenv import load_dotenv
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()

# What your webhook handler recorded, keyed by call or message id. A real one
# is a table; the reconciler only needs membership.
SEEN = set()


def voice_logs(since, until, page_size=200):
    """Every voice log the platform kept for the window."""
    return client.logs.voice.list(created_after=since, created_before=until,
                                  page_size=page_size)


def message_logs(since, until, page_size=200):
    """Every message log for the window."""
    return client.logs.messages.list(created_after=since, created_before=until,
                                     page_size=page_size)


def missed(logs):
    """Log entries your webhook never recorded."""
    return [entry for entry in logs.get("data", []) if entry.get("id") not in SEEN]


def events_for(log_id):
    """The event trail of one voice log, for the ones you missed."""
    return client.logs.voice.list_events(log_id)


def reconcile(since, until):
    """One pass: list the window, diff against what you saw, fetch the trail
    of each missed call."""
    report = {"voice": [], "messages": []}
    for entry in missed(voice_logs(since, until)):
        report["voice"].append({"log": entry, "events": events_for(entry["id"])})
    report["messages"] = missed(message_logs(since, until))
    return report


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("usage: python app.py <since ISO-8601> <until ISO-8601>")
    print(json.dumps(reconcile(sys.argv[1], sys.argv[2]), indent=1))
