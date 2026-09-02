"""Prove the claim without a network.

Claim: one PATCH to the documented messaging path with `body: ""` redacts a
sent message's body, and the empty string is the only value the spec allows.

Proof: with the HTTP layer replaced by a recorder, `redact` makes exactly one
PATCH to the documented path for the id with the body `{"body": ""}`. The spec
marks `body` required and its description says it must be an empty string;
the operation's description names the terminal states that are eligible.
Expected values live here, not in app.py.
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

TEMPLATE = "/api/messaging/messages/{message_id}"
MID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
PATH = TEMPLATE.replace("{message_id}", MID)


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder()
    recipe.http = rec
    recipe.redact(MID)
    assert len(rec.calls) == 1, rec.calls
    (call,) = rec.calls
    assert (call["method"], call["path"]) == ("PATCH", PATH), call
    assert call["body"] == {"body": ""}, call
    V.assert_documented("rest", "PATCH", PATH, call["body"])

    # the spec's own words: body is required, and only "" is accepted
    spec = V.spec("rest")
    op = spec["paths"][TEMPLATE]["patch"]
    schema = op["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    assert schema["required"] == ["body"], schema.get("required")
    assert "empty string" in schema["properties"]["body"]["description"]
    desc = op.get("description", "")
    for state in ("delivered", "undelivered", "failed", "queued"):
        assert state in desc, state

    print(f"ok: PATCH {PATH} with {{\"body\": \"\"}}; the spec requires body, allows "
          f"only the empty string, and names the eligible terminal states")


if __name__ == "__main__":
    main()
