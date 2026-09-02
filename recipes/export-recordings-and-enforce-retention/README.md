# Export recordings and enforce retention

> A pass lists every call recording across pages, copies each one older than your retention window to storage you control, and then deletes it from SignalWire. Nothing is deleted that was not copied first.

**Scenario:** a shop that must keep call recordings for a year in its own archive and nowhere else

## What this demonstrates

SignalWire keeps a recording until you delete it. The vendored REST spec lists
them at `GET /api/relay/rest/recordings`, paginated through `links.next`, and
every variant of recording it documents carries an `id`, a `created_at`, a
`duration_in_seconds` and a `url` "of the recording file".
`DELETE /api/relay/rest/recordings/{id}` answers `204`. Retention is therefore
three steps in a fixed order: find what is past the window, copy it out, delete
it. The copy is a GET of `url` with your project credentials as basic auth, so
it also works when the project's media protection is on. You reach the two
endpoints as `client.recordings.list` and `client.recordings.delete`.

## How it works

```python
def export_and_delete(now=None, fetch=download):
    now = now or datetime.now(timezone.utc)
    moved = []
    for recording in every_page(client.recordings.list):
        if not expired(recording, now):
            continue
        path = EXPORT_DIR / f"{recording['id']}{suffix_of(recording['url'])}"
        path.write_bytes(fetch(recording["url"]))     # copy first
        client.recordings.delete(recording["id"])      # then, and only then, delete
        moved.append({"id": recording["id"], "created_at": recording["created_at"],
                      "path": str(path)})
    return moved
```

What the platform receives, per expired recording:

```json
GET /api/relay/rest/recordings
GET /api/relay/rest/recordings?page_token=<from links.next>
GET <url>                                 with basic auth
DELETE /api/relay/rest/recordings/<id>    204
```

The order is the safety property. A copy that raises stops the pass on that
recording, before its `DELETE`, so a storage outage leaves recordings in
SignalWire rather than nowhere. `EXPORT_DIR` stands in for your object storage;
swap `write_bytes` for your client's upload.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: credentials, RETENTION_DAYS, EXPORT_DIR
python app.py
```

There is no server to expose; the script speaks to the REST API and exits. Run
it from a scheduler. Each line it prints is one recording moved: its id, when
it was made, and where the copy is.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

You swap the SDK's HTTP layer for a recorder that answers with two pages of
recordings, two past a 30-day window and one inside it, and the media fetcher
for a fake that records its URLs. You run a pass and assert the following.

- the pass makes `GET`, `GET`, `DELETE`, `DELETE` in that order; page two carries exactly the query from `links.next`
- the fetcher was asked for exactly the two expired URLs, and each copy sits in the export directory under its id with the file's own extension
- the fresh recording was neither fetched nor deleted, and the report names the two moved ones in order
- a second pass whose fetcher raises makes no `DELETE`
- every path and the page query are documented, the delete answers `204`, the list carries `links`, and every recording variant in the spec carries `id`, `created_at`, `url` and `duration_in_seconds`

## Limitations

You prove the order and the requests. What `url` serves, and how long the
platform takes to mark a recording `finished`, are the platform's side.

Writing a recording somewhere else at record time is a different mechanism. In
cXML, `<Record>` takes `storageUrl` for that; SWML's `record` and `record_call`
expose no storage URL, which is why this recipe works after the fact.

## What to change first

Swap the two lines marked `copy first` and `then, and only then, delete`, and
run the verifier. The failing-fetch case shows a `DELETE` for a recording that
was never copied, which is the failure this recipe exists to prevent.
