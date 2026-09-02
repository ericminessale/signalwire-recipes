# Publish events to browsers with PubSub

> A PubSub token grants `read` or `write` on named channels for a number of minutes, and your server mints one per member with the role your sign-in decided. The browser never holds the project API token.

**Scenario:** a workshop status board in the shop's browser that updates when a repair is done, with customers' phones allowed to read and only the board allowed to write

## What this demonstrates

The vendored REST spec's `POST /api/pubsub/tokens` requires two fields. `ttl`
is "The maximum time, in minutes, for which the access token will be valid.
Between 1 and 43,200 (30 days)". `channels` is "User-defined channel names.
Each channel is an object with `read` and/or `write` properties". It also takes
`member_id`, "The unique identifier of the member", and `state`, "An arbitrary
JSON object available to store stateful application information in". It
answers with a `token`. So the token is where the permissions live: a reader's
token names the channel with `read` true and `write` false, and a publisher's
has `write` true. The SDK wraps the call as `client.pubsub.create_token`.

## How it works

```python
def reader_token(member_id):
    return client.pubsub.create_token(
        ttl=TOKEN_TTL_MINUTES, member_id=member_id,
        channels={CHANNEL: {"read": True, "write": False}},
        state={"role": "reader"})

@app.post("/pubsub/token")
def token():
    body = request.get_json(force=True)
    minted = publisher_token(body["member_id"]) if body.get("role") == "publisher" \
        else reader_token(body["member_id"])
    return jsonify({"token": minted["token"], "channel": CHANNEL})
```

What the platform receives, for a reader and then for the board:

```json
POST /api/pubsub/tokens
{"ttl": 60, "member_id": "dana",
 "channels": {"workshop-board": {"read": true, "write": false}}, "state": {"role": "reader"}}

POST /api/pubsub/tokens
{"ttl": 60, "member_id": "board-1",
 "channels": {"workshop-board": {"read": true, "write": true}}, "state": {"role": "publisher"}}
```

The route hands the browser the minted token and the channel name, and nothing
else. Who counts as a publisher is your sign-in's decision. The route here
takes a `role` field as a stand-in for it; replace that with your own session
check.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: credentials, CHANNEL, TOKEN_TTL_MINUTES
python app.py
```

Then, from a page you serve:

```bash
curl -X POST http://localhost:8080/pubsub/token -H 'Content-Type: application/json' \
     -d '{"member_id": "dana"}'
```

The browser side is the Browser SDK's PubSub client: it takes the token,
subscribes to the channel, and receives what a publisher sends. That client is
outside this recipe; the token it needs is what this recipe mints.

## Verify it

No network, no account.

```bash
cd ..                     # back to the recipe folder
python verify.py
```

The verifier swaps the SDK's HTTP layer for a recorder and drives the Flask
route with its test client. It asserts the following.

- `reader_token` and `publisher_token` each make one `POST` to the documented PubSub tokens path
- the reader body is exactly `ttl` 60, the member id, the channel with `read` true and `write` false, and a `state`; the publisher body has `write` true
- the spec requires exactly `ttl` and `channels`, describes `ttl` in minutes with the 43,200 bound and `channels` as objects with `read` and/or `write`, documents `member_id` and `state`, and answers with `token`
- the route returns exactly the token and the channel name, mints a reader by default and a publisher when your sign-in says so
- a request without a member id is refused and mints nothing, and no request carries the API token

## Limitations

You prove the tokens and the route. Whether a subscribed browser receives a
publish is the Browser SDK's and the platform's side. The token gates who may
publish; it does not deliver anything by itself.

`state` is yours to define. The spec only says it must be valid JSON with a
size limit.

## What to change first

Give the reader's channel `write` true and run the verifier. The reader body
assertion fails. A customer's phone that can write to the board is the bug this
split of two token shapes exists to prevent.
