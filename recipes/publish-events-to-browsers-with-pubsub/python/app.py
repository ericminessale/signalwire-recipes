"""Publish events to browsers with PubSub.

The token is the part your server owns. The vendored REST spec's
`POST /api/pubsub/tokens` requires `ttl`, "The maximum time, in minutes, for
which the access token will be valid. Between 1 and 43,200 (30 days)", and
`channels`, "User-defined channel names. Each channel is an object with `read`
and/or `write` properties." It takes an optional `member_id` and a `state`
object, and answers with a `token`. A browser that holds a token with `read`
on a channel subscribes to it; a publisher holds one with `write`. Your server
never hands out the project API token, and it decides per channel who reads
and who writes.

Written against signalwire-sdk 3.0.1 (RestClient.pubsub). The subscribe and
publish calls are the Browser SDK's, outside this recipe.
"""
import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()

CHANNEL = os.getenv("CHANNEL", "workshop-board")
TOKEN_TTL_MINUTES = int(os.getenv("TOKEN_TTL_MINUTES", "60"))


def reader_token(member_id):
    """A browser's token: read on the channel, nothing else."""
    return client.pubsub.create_token(
        ttl=TOKEN_TTL_MINUTES, member_id=member_id,
        channels={CHANNEL: {"read": True, "write": False}},
        state={"role": "reader"})


def publisher_token(member_id):
    """The board's token: write as well as read."""
    return client.pubsub.create_token(
        ttl=TOKEN_TTL_MINUTES, member_id=member_id,
        channels={CHANNEL: {"read": True, "write": True}},
        state={"role": "publisher"})


app = Flask(__name__)


@app.post("/pubsub/token")
def token():
    """Your sign-in decides the role; the platform token then carries it."""
    body = request.get_json(force=True)
    member_id = body.get("member_id")
    if not member_id:
        abort(400)
    minted = publisher_token(member_id) if body.get("role") == "publisher" \
        else reader_token(member_id)
    return jsonify({"token": minted["token"], "channel": CHANNEL})


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "8080")))
