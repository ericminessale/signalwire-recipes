# Reconcile webhooks against the logs API

> A pass over a time window walks every page of the voice and message logs. It reports every entry your webhook handler's store lacks, and fetches the event trail of each such call.

**Scenario:** a nightly job that finds the calls and messages your status handler has no record of

## What this demonstrates

`GET /api/voice/logs` and `GET /api/messaging/logs` take `created_after`,
`created_before` and `page_size` in the vendored REST spec, and each page's
`links.next` is the URL of the next one. `GET /api/voice/logs/{id}/events`
returns "an array of event entries for the log", each with `event_at`, `level`,
`name` and `details`. You reach them as `client.logs.voice.list`,
`client.logs.messages.list` and `client.logs.voice.list_events`. You walk both
lists to the end, diff them against the ids your handler stored, and every id
the store lacks is a candidate to reconcile.

## How it works

```python
def every_page(fetch, **params):
    entries, page = [], fetch(**params)
    while True:
        entries.extend(page.get("data", []))
        nxt = (page.get("links") or {}).get("next")
        if not nxt:
            return entries
        page = fetch(**dict(parse_qsl(urlsplit(nxt).query)))

def reconcile(since, until):
    report = {"voice": [], "messages": []}
    for entry in missed(voice_logs(since, until)):
        report["voice"].append({"log": entry, "events": events_for(entry["id"])})
    report["messages"] = missed(message_logs(since, until))
    return report
```

What the platform receives for one pass over a two-page voice window:

```
GET /api/voice/logs?created_after=...&created_before=...&page_size=200
GET /api/voice/logs?page_token=...&page_size=200
GET /api/voice/logs/<first unseen id>/events
GET /api/voice/logs/<second unseen id>/events
GET /api/messaging/logs?created_after=...&created_before=...&page_size=200
```

`every_page` re-issues the query string each `links.next` carries, so it follows
whatever pagination the platform hands back. `SEEN` stands in for whatever your
webhook handler writes: a table of call and message ids. An id in the window
that your table lacks is an entry you have no record of. Why you have none is
for you to work out, and the events trail is where you start.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: your project id, API token and space
python app.py 2026-09-01T00:00:00Z 2026-09-02T00:00:00Z
```

There is no server to expose; the script speaks to the REST API and exits.
Replace `SEEN` with a lookup into wherever your webhook handler records ids.
With it empty, the report lists every entry in the window.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

You swap the SDK's HTTP layer for a recorder that answers with fixtures. They
are two voice pages joined by a `links.next` URL, one message page, and a trail
per unseen call. You run a pass and assert the following.

- the pass makes five requests in order: voice page one, voice page two, one events request per unseen call, the message page
- page one and the message page carry the window parameters; page two carries exactly the query from the `links.next` URL; the events requests carry no query
- the spec documents every path and parameter used
- the report names both unseen calls, one of them from page two, each with its own trail, and both unseen messages, and nothing the store holds
- the spec bounds `page_size` between 1 and 1000 on both lists, so 200 is legal

## Limitations

You prove the requests and the diff against fixtures; what the logs contain for
a real window is the platform's record.

A log entry's fields depend on its `type`. The spec's voice log is a oneOf over
Relay, Fabric, video room, Dialogflow and discarded shapes, and all of them
carry `id`.

## What to change first

Delete the `while` loop in `every_page` so it returns the first page and run
the verifier. The request sequence fails because page two is never fetched,
and the report loses the call that sat on it. That is the point: a window is
every page, not the first one.
