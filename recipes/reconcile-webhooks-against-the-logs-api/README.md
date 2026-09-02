# Reconcile webhooks against the logs API

> A pass over a time window of the voice and message logs finds the calls and messages your webhook handler never recorded, and fetches the event trail of each missed call.

**Scenario:** a nightly job that catches the status callbacks a deploy swallowed

## What this demonstrates

A webhook is a best effort at your door. The logs are the platform's record.
`GET /api/voice/logs` and `GET /api/messaging/logs` take `created_after`,
`created_before` and `page_size` in the vendored REST spec, and
`GET /api/voice/logs/{id}/events` returns "an array of event entries for the
log", each with `event_at`, `level`, `name` and `details`. The SDK wraps them as
`client.logs.voice.list`, `client.logs.messages.list` and
`client.logs.voice.list_events`. Diffing a window against what your handler
stored is the whole reconciler.

## How it works

```python
def reconcile(since, until):
    report = {"voice": [], "messages": []}
    for entry in missed(voice_logs(since, until)):
        report["voice"].append({"log": entry, "events": events_for(entry["id"])})
    report["messages"] = missed(message_logs(since, until))
    return report

def missed(logs):
    return [entry for entry in logs.get("data", []) if entry.get("id") not in SEEN]
```

What the platform receives for one pass with one missed call:

```
GET /api/voice/logs?created_after=...&created_before=...&page_size=200
GET /api/voice/logs/<missed id>/events
GET /api/messaging/logs?created_after=...&created_before=...&page_size=200
```

`SEEN` stands in for whatever your webhook handler writes: a table of call and
message ids. Anything in the window that is not in it is a callback you never
processed. The events trail says what happened to that call. The spec bounds
`page_size` to 1000; a window with more entries than that needs the `links`
the list response carries for the next page.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: your project id, API token and space
python app.py 2026-09-01T00:00:00Z 2026-09-02T00:00:00Z
```

There is no server to expose; the script speaks to the REST API and exits.
Replace `SEEN` with a lookup into wherever your webhook handler records ids.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder that answers with fixture
pages. It marks one call and one message as seen, runs a pass, and asserts the
following.

- the pass makes exactly three requests, in order: the voice list, the missed call's events, the message list
- both lists carry `created_after`, `created_before` and `page_size` as documented query parameters, and the events request carries no query
- all three paths are documented in the vendored spec
- the report names the missed call with its event trail and the missed message, and nothing the handler saw
- the spec bounds `page_size` between 1 and 1000, so the default of 200 is legal

## Limitations

The verifier proves the requests and the diff against fixtures; what the logs
contain for a real window is the platform's record. Pagination is yours: the
recipe reads one page.

A log entry's fields depend on its `type`; the spec's voice log is a oneOf over
Relay, Fabric, video room, Dialogflow and discarded shapes, all with `id`.

## What to change first

Add `"call-missed"` to `SEEN` in the verifier's setup and run it. The request
sequence assertion fails because no events request is made. That is the point:
the reconciler only spends a request on what you did not already have.
