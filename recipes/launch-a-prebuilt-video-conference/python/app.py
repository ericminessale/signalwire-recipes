"""Launch a prebuilt video conference.

One POST creates a themed video conference, and a second GET lists the tokens
the platform minted for it, each with a `name`, a `token` and its `scopes`.
The prebuilt conference is the hosted room UI: you pass a `display_name` and,
if you want them, a layout, a quality, a join window and the light and dark
theme colours, and get back an `id` to hand out. Nothing here is a Browser SDK
client of your own.

Written against signalwire-sdk 3.0.1 (RestClient.video.conferences).
"""
from dotenv import load_dotenv
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()


def launch(display_name, *, name=None, record_on_start=False, quality="720p",
           layout="grid-responsive", primary="#F72A72"):
    """Create the conference. `display_name` is the spec's one required field."""
    body = {"display_name": display_name, "record_on_start": record_on_start,
            "quality": quality, "layout": layout,
            "light_primary": primary, "dark_primary": primary}
    if name:
        body["name"] = name
    return client.video.conferences.create(**body)


def tokens(conference_id):
    """The tokens the platform minted for the conference, by name and scopes."""
    return client.video.conferences.list_conference_tokens(conference_id)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("usage: python app.py '<display name>' [slug]")
    conf = launch(sys.argv[1], name=sys.argv[2] if len(sys.argv) > 2 else None)
    print(conf)
    print(tokens(conf["id"]))
