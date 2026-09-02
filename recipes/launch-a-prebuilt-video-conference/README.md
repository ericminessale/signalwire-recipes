# Launch a prebuilt video conference

> One POST creates a themed video conference from a `display_name` and the options the spec documents. One GET lists the tokens the platform minted for it, each with a name, a token and scopes.

**Scenario:** a workshop that wants a video room with its own colours, with nothing to build

## What this demonstrates

`POST /api/video/conferences` creates a prebuilt conference: the hosted room UI,
themed with the colour fields the vendored REST spec lists (`light_primary`,
`dark_primary`, backgrounds, foregrounds, success and negative). `display_name`
is the one required field; `name`, `quality`, `layout`, `record_on_start`,
`join_from`, `join_until` and `enable_chat` are among the options. The response
carries an `id`. `GET /api/video/conferences/{id}/conference_tokens` lists the
tokens the platform minted for it; the spec's token schema carries `name`,
`token` and `scopes`. The SDK wraps the two as `client.video.conferences.create`
and `client.video.conferences.list_conference_tokens`.

## How it works

```python
def launch(display_name, *, name=None, record_on_start=False, quality="720p",
           layout="grid-responsive", primary="#F72A72"):
    body = {"display_name": display_name, "record_on_start": record_on_start,
            "quality": quality, "layout": layout,
            "light_primary": primary, "dark_primary": primary}
    if name:
        body["name"] = name
    return client.video.conferences.create(**body)

def tokens(conference_id):
    return client.video.conferences.list_conference_tokens(conference_id)
```

What the platform receives:

```json
POST /api/video/conferences
{"display_name": "Workshop stand-up", "name": "workshop-standup",
 "record_on_start": true, "quality": "720p", "layout": "grid-responsive",
 "light_primary": "#F72A72", "dark_primary": "#F72A72"}

GET /api/video/conferences/<id>/conference_tokens
```

The tokens are what you hand out. Each carries `scopes`, "a list of
permissions", which is how a moderator's token differs from a guest's. Reset
one with `POST /api/video/conference_tokens/{id}/reset` when it leaks.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: your project id, API token and space
python app.py "Workshop stand-up" workshop-standup
```

There is no server to expose; the script speaks to the REST API and exits. It
prints the conference and then its tokens.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

You swap the SDK's HTTP layer for a recorder that answers the create with an id,
call both helpers, and assert the following.

- `launch` makes one `POST` to the documented conferences path
- the spec's required list is exactly `display_name`, present, and every other field sent is a documented property
- the body carries the name, `record_on_start: true`, and the same colour in `light_primary` and `dark_primary`
- `tokens` makes one `GET` to the documented conference tokens path for the id the create returned, with no query
- the spec's token schema carries `id`, `name`, `token` and `scopes`

## Limitations

You prove the requests and the documented shapes. Which tokens the platform
mints, and what scopes each carries, appear in the live response.

The prebuilt UI is the platform's. For your own room UI, see
`create-a-video-room-and-join-from-the-browser`.

## What to change first

Remove `display_name` from the body and run the verifier. The required-field
assertion fails, which is the point: it is the one thing a conference cannot do
without.
