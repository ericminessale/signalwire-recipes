"""Prove the claim without a network.

Claim: `tap` sends a copy of a call's audio to a WebSocket destination of
yours, and `stop_tap` ends it by control id, in SWML or mid-call over REST.

Proof: both SWML surfaces validate against the bundled schema, run answer,
tap, connect, stop_tap, hangup, and carry the same tap object: the wss URI,
both directions, PCMU, and a control id that `stop_tap` repeats. The schema
requires `uri` on `tap`, and the two surfaces render the same document. With
the HTTP layer replaced by a recorder, `start_tap` and `stop_tap` each make
one POST to the documented calling path with the command, the call id and
params the spec's variants require, and the `ws` device carries the URI.
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
    "TAP_URI": "wss://media.example.com/tap",
    "OWNER_NUMBER": "+15550100001",
})

import verifylib as V  # noqa: E402

PATH = "/api/calling/calls"
CALL = "6d3f4a0e-2b1c-4e7a-9f0d-1c2b3a4d5e6f"
URI = "wss://media.example.com/tap"
TAP = {"uri": URI, "control_id": "workshop-tap", "direction": "both", "codec": "PCMU"}


def deref(spec, node):
    schemas = spec["components"]["schemas"]
    while isinstance(node, dict) and "$ref" in node:
        node = schemas[node["$ref"].split("/")[-1]]
    return node


def variant(spec, command):
    for v in spec["components"]["schemas"]["Calling.CallRequest"]["oneOf"]:
        if command in (deref(spec, v["properties"]["command"]).get("enum") or []):
            return v.get("required", []), deref(spec, v["properties"]["params"])
    raise AssertionError(f"{command} is not a documented call command")


def check(doc, label):
    V.validate_swml(doc)
    assert V.verb_names(doc) == ["answer", "tap", "connect", "stop_tap", "hangup"], \
        (label, V.verb_names(doc))
    assert V.first(doc, "tap") == TAP, (label, V.first(doc, "tap"))
    assert V.first(doc, "stop_tap") == {"control_id": "workshop-tap"}, label


def main():
    V.sdk_banner()
    import app as recipe
    py = recipe.build().get_document()
    check(py, "python")
    y = V.load_yaml(HERE / "swml" / "agent.yaml")
    check(y, "yaml")
    assert py == y, "python and yaml surfaces differ"
    tap_schema = V.swml_schema()["$defs"]["Tap"]["properties"]["tap"]
    assert tap_schema["required"] == ["uri"], tap_schema.get("required")

    rec = V.Recorder()
    recipe.client.calling._http = rec
    recipe.start_tap(CALL)
    recipe.stop_tap(CALL)
    assert len(rec.calls) == 2, rec.calls
    spec = V.spec("rest")
    start, stop = rec.calls
    V.assert_documented("rest", "POST", PATH, None)
    for call in (start, stop):
        assert (call["method"], call["path"]) == ("POST", PATH), call
        assert call["body"]["id"] == CALL, call["body"]

    assert start["body"]["command"] == "calling.tap", start["body"]
    required, params = variant(spec, "calling.tap")
    assert set(required) == {"command", "id", "params"}, required
    p = start["body"]["params"]
    assert set(p) <= set(params["properties"]), sorted(set(p) - set(params["properties"]))
    assert set(params.get("required", [])) <= set(p), params.get("required")
    assert p["device"] == {"type": "ws", "params": {"uri": URI}}, p["device"]
    assert p["tap"] == {"type": "audio", "params": {"direction": "both"}}, p["tap"]
    assert p["control_id"] == "workshop-tap", p

    assert stop["body"]["command"] == "calling.tap.stop", stop["body"]
    required, params = variant(spec, "calling.tap.stop")
    assert set(required) == {"command", "id", "params"}, required
    assert stop["body"]["params"] == {"control_id": "workshop-tap"}, stop["body"]
    assert set(stop["body"]["params"]) <= set(params["properties"]), params

    print(f"ok: both surfaces run answer, tap({URI}, both, PCMU), connect, stop_tap, "
          f"hangup and render the same document; calling.tap and calling.tap.stop POST "
          f"documented params for id {CALL[:8]}...")


if __name__ == "__main__":
    main()
