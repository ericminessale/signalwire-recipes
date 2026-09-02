"""Prove the claim without a network.

Claim: `calling.transcribe` starts transcribing a live call in the background
by `control_id`, `calling.transcribe.stop` ends it, and the transcript lands on
your `status_url` as a documented callback whose `params.text` holds the text
when there is any.

Proof: with the HTTP layer replaced by a recorder, `start` and `stop` each make
one POST to the documented calling path whose body equals one expected object,
and the spec's variants require exactly `control_id`. The Flask app receives
two callbacks shaped like the spec's transcribe status callback, every required
field present and nothing undocumented: a completed one with text and a failed
one without. It stores each under its call id, `GET /transcripts/<call_id>`
returns it, and an unknown call reads as pending. Expected values live here,
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
    "TRANSCRIBE_STATUS_URL": "https://example.com/transcripts",
})

import verifylib as V  # noqa: E402

PATH = "/api/calling/calls"
CALL = "6d3f4a0e-2b1c-4e7a-9f0d-1c2b3a4d5e6f"
FAILED = "0a1b2c3d-1111-4e7a-9f0d-1c2b3a4d5e6f"
TEXT = "Hi, this is Ridgeline Cycles. Your bike is ready for pickup any time before six."


def deref(spec, node):
    schemas = spec["components"]["schemas"]
    while isinstance(node, dict) and "$ref" in node:
        node = schemas[node["$ref"].split("/")[-1]]
    return node


def variant(spec, command):
    for v in spec["components"]["schemas"]["Calling.CallRequest"]["oneOf"]:
        v = deref(spec, v)
        if command in (deref(spec, v["properties"]["command"]).get("enum") or []):
            return v.get("required", []), deref(spec, v["properties"]["params"])
    raise AssertionError(f"{command} is not a documented call command")


def callback(event_type, call_id, **extra):
    return {"event_type": event_type, "timestamp": 1788350400.5, "project_id": "proj-1234",
            "space_id": "space-1",
            "params": {"id": "t-1", "call_id": call_id, "segment_id": "seg-1", **extra}}


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder()
    recipe.client.calling._http = rec
    recipe.start(CALL)
    recipe.stop(CALL)
    assert [(c["method"], c["path"]) for c in rec.calls] == [("POST", PATH), ("POST", PATH)], rec.calls
    start, stop = rec.calls
    assert start["body"] == {"command": "calling.transcribe", "id": CALL,
                             "params": {"control_id": "call-transcript",
                                        "status_url": "https://example.com/transcripts"}}, start
    assert stop["body"] == {"command": "calling.transcribe.stop", "id": CALL,
                            "params": {"control_id": "call-transcript"}}, stop

    spec = V.spec("rest")
    V.assert_documented("rest", "POST", PATH, None)
    for call, command in ((start, "calling.transcribe"), (stop, "calling.transcribe.stop")):
        required, params = variant(spec, command)
        assert set(required) == {"command", "id", "params"}, (command, required)
        assert params["required"] == ["control_id"], (command, params.get("required"))
        assert set(call["body"]["params"]) <= set(params["properties"]), \
            (command, sorted(set(call["body"]["params"]) - set(params["properties"])))
    _, params = variant(spec, "calling.transcribe")
    assert "status_url" in params["properties"], sorted(params["properties"])

    # the callback, as the spec documents it
    hook = spec["webhooks"]["subpackage_callingWebhooks.transcribe_status_callback"]["post"]
    schema = deref(spec, hook["requestBody"]["content"]["application/json"]["schema"])
    types = deref(spec, schema["properties"]["event_type"])["enum"]
    assert set(types) == {"calling.transcript.completed", "calling.transcript.failed"}, types
    p_schema = deref(spec, schema["properties"]["params"])
    assert "Omitted when there is no transcribed text" in \
        deref(spec, p_schema["properties"]["text"])["description"]
    done = callback("calling.transcript.completed", CALL, text=TEXT)
    failed = callback("calling.transcript.failed", FAILED)
    for e in (done, failed):
        assert set(schema["required"]) <= set(e), sorted(set(schema["required"]) - set(e))
        assert set(e) <= set(schema["properties"]), sorted(set(e) - set(schema["properties"]))
        assert set(p_schema.get("required", [])) <= set(e["params"]), p_schema.get("required")
        assert set(e["params"]) <= set(p_schema["properties"]), sorted(e["params"])
        assert e["event_type"] in types

    client = recipe.app.test_client()
    assert client.get(f"/transcripts/{CALL}").get_json() == {"status": "pending", "text": None}
    for e in (done, failed):
        r = client.post("/transcripts", json=e)
        assert r.status_code == 204, (r.status_code, r.data[:80])
    assert client.get(f"/transcripts/{CALL}").get_json() == \
        {"status": "completed", "text": TEXT, "at": 1788350400.5}
    assert client.get(f"/transcripts/{FAILED}").get_json() == \
        {"status": "failed", "text": None, "at": 1788350400.5}

    print(f"ok: calling.transcribe and calling.transcribe.stop POST the expected bodies for "
          f"{CALL[:8]}...; a completed callback stores {len(TEXT)} characters of text and a "
          f"failed one stores none; both are shaped like the spec's callback")


if __name__ == "__main__":
    main()
