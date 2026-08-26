"""Prove the claim without a network.

Claim: a phone number is bound to a SWML webhook resource holding your agent's
URL. Whether a call then lands is a live-call question this cannot answer; what
it proves is that the binding is made correctly.

Proof: with the HTTP layer replaced by a recorder, two documented requests are
made in dependency order. The resource carries the agent URL as its primary
request URL, and the number is bound to the resource created a moment earlier,
with the handler set to calls rather than messages.
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
    "AGENT_URL": "https://recipes.example.test/agent",
    "PHONE_ROUTE_ID": "11111111-2222-3333-4444-555555555555",
})

import verifylib as V  # noqa: E402

WEBHOOKS = "/api/fabric/resources/swml_webhooks"


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder(responses=[{"id": "res-abc"}, {}])
    V.record_everything(recipe.client, rec)
    recipe.point_number_at()

    assert len(rec.calls) == 2, rec.calls
    create, assign = rec.calls

    # 1. the resource that holds the agent's URL
    assert (create["method"], create["path"]) == ("POST", WEBHOOKS), create
    body = create["body"]
    V.assert_documented("rest", "POST", WEBHOOKS, body)
    assert body["primary_request_url"] == os.environ["AGENT_URL"], body
    assert body["primary_request_method"] == "POST", body
    # a second URL for SignalWire to try; independence from the agent is a
    # deployment choice, so this asserts only that one is set
    assert body["fallback_request_url"], body

    # 2. the number, bound to the resource that was just created
    path = f"/api/fabric/resources/res-abc/phone_routes"
    assert (assign["method"], assign["path"]) == ("POST", path), assign
    V.assert_documented("rest", "POST", path, assign["body"])
    assert assign["body"]["phone_route_id"] == os.environ["PHONE_ROUTE_ID"], assign
    # calls, not messages: the same resource type serves both
    assert assign["body"]["handler"] == "calls", assign

    # The binding uses the id the create returned, not a value from config.
    assert "res-abc" in assign["path"], assign

    print(f"ok: POST {WEBHOOKS} carrying {os.environ['AGENT_URL']}, then "
          f"POST .../res-abc/phone_routes handler=calls")


if __name__ == "__main__":
    main()
