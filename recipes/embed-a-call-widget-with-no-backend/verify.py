"""Prove the claim without a network.

Claim: a `<sw-click-to-call>` element with a Click to Call token from the
Dashboard and a destination address puts a call button on a page, and no
server of yours is in the call path.

Proof: the Flask app serves one HTML page. The page loads the widget script
the guide names and holds exactly one `sw-click-to-call` element whose `token`,
`destination` and `label` attributes are the configured values, escaped. The
page carries no API token and no route other than the page, so nothing of
yours can be in the call path. The optional REST exchange makes one POST to
the documented embeds tokens path with exactly `token`, the spec's one
required field, and the spec's response carries `token`. Expected values live
here, not in app.py.
"""
import os
import pathlib
import re
import sys
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))
os.environ.update({
    "SIGNALWIRE_PROJECT_ID": "proj-1234",
    "SIGNALWIRE_API_TOKEN": "PT-test",
    "SIGNALWIRE_SPACE": "example.signalwire.com",
    "CLICK_TO_CALL_TOKEN": "c2c_verifier_only_0123456789abcdef",
    "DESTINATION": "/public/workshop",
    "LABEL": "Talk to the workshop",
})

import verifylib as V  # noqa: E402

SCRIPT = ("https://unpkg.com/@signalwire/web-components/dist/embed/"
          "signalwire-web-components-embed.iife.js")
EMBEDS = "/api/fabric/embeds/tokens"


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.widgets, self.scripts = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "sw-click-to-call":
            self.widgets.append(dict(attrs))
        if tag == "script":
            self.scripts.append(dict(attrs).get("src"))


def deref(spec, node):
    schemas = spec["components"]["schemas"]
    while isinstance(node, dict) and "$ref" in node:
        node = schemas[node["$ref"].split("/")[-1]]
    return node


def main():
    V.sdk_banner()
    import app as recipe

    client = recipe.app.test_client()
    r = client.get("/")
    assert r.status_code == 200 and r.mimetype == "text/html", (r.status_code, r.mimetype)
    body = r.get_data(as_text=True)
    parsed = Elements()
    parsed.feed(body)
    assert parsed.scripts == [SCRIPT], parsed.scripts
    assert parsed.widgets == [{"token": "c2c_verifier_only_0123456789abcdef",
                               "destination": "/public/workshop",
                               "label": "Talk to the workshop"}], parsed.widgets
    # nothing of yours in the call path: no API token on the page, no other route
    assert "PT-test" not in body and "proj-1234" not in body
    routes = sorted(str(rule) for rule in recipe.app.url_map.iter_rules() if rule.endpoint != "static")
    assert routes == ["/"], routes

    # attribute values are escaped, so a label with a quote cannot break out
    hostile = recipe.page(label='Talk" onclick="alert(1)')
    parsed = Elements()
    parsed.feed(hostile)
    assert parsed.widgets[0]["label"] == 'Talk" onclick="alert(1)', parsed.widgets
    assert "onclick" not in [k for w in parsed.widgets for k in w], parsed.widgets

    # the optional exchange, as the spec documents it
    from signalwire.rest import RestClient
    rec = V.Recorder(responses=[{"token": "guest-verifier-only"}])
    real_init = RestClient.__init__

    def patched_init(self, *a, **k):
        real_init(self, *a, **k)
        self.fabric.tokens._http = rec

    RestClient.__init__ = patched_init
    try:
        got = recipe.exchange()
    finally:
        RestClient.__init__ = real_init
    assert got == {"token": "guest-verifier-only"}, got
    (call,) = rec.calls
    assert (call["method"], call["path"]) == ("POST", EMBEDS), call
    assert call["body"] == {"token": "c2c_verifier_only_0123456789abcdef"}, call["body"]
    spec = V.spec("rest")
    V.assert_documented("rest", "POST", EMBEDS, call["body"])
    op = spec["paths"][EMBEDS]["post"]
    req = deref(spec, op["requestBody"]["content"]["application/json"]["schema"])
    assert req["required"] == ["token"], req["required"]
    assert "Click to Call" in deref(spec, req["properties"]["token"])["description"]
    resp = deref(spec, op["responses"]["201"]["content"]["application/json"]["schema"])
    assert "token" in resp["properties"], sorted(resp["properties"])

    print(f"ok: the page loads the widget script and one sw-click-to-call with the configured token, "
          f"destination and label, escaped; it exposes one route and no API token; the exchange "
          f"POSTs {EMBEDS} with exactly the documented field")


if __name__ == "__main__":
    main()
