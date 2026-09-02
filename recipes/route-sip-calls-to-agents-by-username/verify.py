"""Prove the claim without a network.

Claim: calls to different SIP usernames on one domain land on different
agents behind one AgentServer, decided by a routing callback that reads the
username from the platform's request body.

Proof: drive the server's own FastAPI app with the test client. A POST to
either agent's `/sip` path whose body carries `call.to` of
`sip:workshop@...` answers 307 with `Location: /support`; `sip:sales@...`
answers 307 to `/sales`; a `tel:` destination and an unknown username answer
200 with the SWML of the agent that received the request, because the
callback returned None. A request with no basic auth is refused. The
`extract_sip_username` helper is the SDK's; its behaviour on `sip:`, `tel:`
and bare values is asserted directly. Expected values live here, not in
app.py.
"""
import base64
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))

import verifylib as V  # noqa: E402

# fixed, verifier-only credentials
os.environ["SWML_BASIC_AUTH_USER"] = "signalwire"
os.environ["SWML_BASIC_AUTH_PASSWORD"] = "verify-only-password"

ROUTES = {"sales": "/sales", "orders": "/sales", "support": "/support", "workshop": "/support"}


def auth():
    return {"Authorization": "Basic " + base64.b64encode(
        b"signalwire:verify-only-password").decode()}


def body(to):
    return {"call": {"call_id": "c1", "to": to, "from": "sip:alice@phones.example.com"}}


def main():
    V.sdk_banner()
    from fastapi.testclient import TestClient
    from signalwire import SWMLService
    import app as recipe

    server = recipe.build_server(port=3000)
    for agent in server.agents.values():
        V.assert_basic_auth_from_env(agent)
    client = TestClient(server.app)

    # the SDK helper the callback relies on
    assert SWMLService.extract_sip_username(body("sip:Workshop@pbx.example.com")) == "Workshop"
    assert SWMLService.extract_sip_username(body("tel:+15550100001")) == "+15550100001"
    assert SWMLService.extract_sip_username({}) is None

    # every username lands on its agent, from either agent's /sip path
    for username, route in ROUTES.items():
        for entry in ("/sales", "/support"):
            r = client.post(f"{entry}/sip", json=body(f"sip:{username}@pbx.example.com"),
                            headers=auth(), follow_redirects=False)
            assert (r.status_code, r.headers.get("location")) == (307, route), \
                (username, entry, r.status_code, r.headers.get("location"))

    # no match: the callback returns None and the receiving agent answers itself
    for to in ("sip:nobody@pbx.example.com", "tel:+15550100001"):
        r = client.post("/sales/sip", json=body(to), headers=auth(), follow_redirects=False)
        assert r.status_code == 200, (to, r.status_code, r.text[:100])
        doc = r.json()
        V.validate_swml(doc)
        ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]
        assert "sales desk" in json.dumps(ai["prompt"]), (to, ai["prompt"])

    # basic auth still gates the path
    r = client.post("/sales/sip", json=body("sip:workshop@pbx.example.com"),
                    follow_redirects=False)
    assert r.status_code == 401, r.status_code

    print(f"ok: {sorted(ROUTES)} redirect 307 to their agents from either /sip path; an "
          f"unknown username and a tel: destination get the receiving agent's SWML; "
          f"no auth is 401")


if __name__ == "__main__":
    main()
