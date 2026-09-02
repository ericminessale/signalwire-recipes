"""Prove the claim without a network.

Claim: one POST creates a themed video conference from a `display_name` and
options the spec documents, and one GET lists the tokens the platform minted
for it, each with a name, a token and scopes.

Proof: with the HTTP layer replaced by a recorder that answers the create with
an `id`, `launch` makes one POST to the documented conferences path. Its body
carries `display_name`, the spec's one required field, and only documented
properties, with the theme colours in the documented fields. `tokens` makes
one GET to the documented conference tokens path for that id. The spec's
token schema carries `name`, `token` and `scopes`. Expected values live here,
not in app.py.
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))
os.environ.update({
    "SIGNALWIRE_PROJECT_ID": "proj-1234",
    "SIGNALWIRE_API_TOKEN": "PT-test",
    "SIGNALWIRE_SPACE": "example.signalwire.com",
})

import verifylib as V  # noqa: E402

CONFERENCES = "/api/video/conferences"
CID = "4a1f0a5e-6f2b-4c3d-9e8f-0b1c2d3e4f5a"
TOKENS = f"{CONFERENCES}/{CID}/conference_tokens"


def deref(spec, node):
    while isinstance(node, dict) and "$ref" in node:
        node = spec["components"]["schemas"][node["$ref"].split("/")[-1]]
    return node


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder(responses=[{"id": CID, "display_name": "Workshop stand-up"},
                                {"data": [{"id": "t1", "name": "moderator", "token": "x",
                                           "scopes": ["conference.moderator"]}]}])
    recipe.client.video.conferences._http = rec

    conf = recipe.launch("Workshop stand-up", name="workshop-standup", record_on_start=True)
    assert conf["id"] == CID
    listed = recipe.tokens(conf["id"])
    assert listed["data"][0]["name"] == "moderator"
    assert len(rec.calls) == 2, rec.calls
    create, toks = rec.calls

    spec = V.spec("rest")
    assert (create["method"], create["path"]) == ("POST", CONFERENCES), create
    body = create["body"]
    schema = deref(spec, spec["paths"][CONFERENCES]["post"]["requestBody"]["content"]["application/json"]["schema"])
    assert schema["required"] == ["display_name"], schema.get("required")
    assert body["display_name"] == "Workshop stand-up", body
    assert set(body) <= set(schema["properties"]), sorted(set(body) - set(schema["properties"]))
    assert body["name"] == "workshop-standup" and body["record_on_start"] is True, body
    assert body["light_primary"] == body["dark_primary"] == "#F72A72", body
    V.assert_documented("rest", "POST", CONFERENCES, body)

    assert (toks["method"], toks["path"]) == ("GET", TOKENS), toks
    assert toks["params"] is None, toks
    V.assert_documented("rest", "GET", TOKENS, None)
    resp = deref(spec, spec["paths"]["/api/video/conferences/{id}/conference_tokens"]["get"]
                 ["responses"]["200"]["content"]["application/json"]["schema"])
    token = deref(spec, resp["properties"]["data"]["items"])
    assert {"id", "name", "token", "scopes"} <= set(token["properties"]), sorted(token["properties"])

    print(f"ok: POST {CONFERENCES} with display_name and documented options, then GET "
          f"{TOKENS}; the spec's token carries name, token and scopes")


if __name__ == "__main__":
    main()
