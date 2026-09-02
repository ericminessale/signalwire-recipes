"""Prove the claim without a network.

Claim: your backend pushes a message into a running AI conversation with one
REST command, `calling.ai_message`, addressed by call id. A `system` role
carries an instruction; the same command merges `global_data` or resets the
conversation.

Proof: with the HTTP layer replaced by a recorder, each helper makes exactly
one POST to the documented calling path with `command: calling.ai_message`,
the call id at the top level as `id`, and only documented `params`. The role
is one of the documented enum values. Expected values live here, not in
app.py.
"""
import json
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

PATH = "/api/calling/calls"
CALL = "6d3f4a0e-2b1c-4e7a-9f0d-1c2b3a4d5e6f"


def documented_variant(command):
    """The command's params schema, read from the spec rather than assumed."""
    spec = V.spec("rest")
    schemas = spec["components"]["schemas"]

    def deref(node):
        while isinstance(node, dict) and "$ref" in node:
            node = schemas[node["$ref"].split("/")[-1]]
        return node

    for variant in schemas["Calling.CallRequest"]["oneOf"]:
        cmd = deref(variant["properties"]["command"])
        if command in (cmd.get("enum") or []):
            params = deref(variant["properties"]["params"])
            return variant.get("required", []), {
                k: deref(v) for k, v in params["properties"].items()}
    raise AssertionError(f"{command} is not a documented call command")


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder()
    recipe.client.calling._http = rec

    recipe.nudge(CALL, "The caller is a returning customer. Skip the identity questions.")
    recipe.share(CALL, {"tier": "gold"})
    recipe.restart(CALL, "You are now the billing specialist.")
    assert len(rec.calls) == 3, rec.calls

    required, props = documented_variant("calling.ai_message")
    assert set(required) == {"command", "id", "params"}, required
    roles = props["role"]["enum"]
    assert set(roles) == {"system", "user", "assistant"}, roles

    expected_params = [
        {"role": "system", "message_text": "The caller is a returning customer. "
                                           "Skip the identity questions."},
        {"global_data": {"tier": "gold"}},
        {"reset": {"full_reset": True, "system_prompt": "You are now the billing "
                                                        "specialist."}},
    ]
    for call, want in zip(rec.calls, expected_params):
        assert (call["method"], call["path"]) == ("POST", PATH), call
        V.assert_documented("rest", "POST", PATH, None)
        body = call["body"]
        # the command, the call id at the top level, and exactly these params
        assert body == {"command": "calling.ai_message", "id": CALL, "params": want}, \
            json.dumps(body, indent=1)
        unknown = set(want) - set(props)
        assert not unknown, f"undocumented ai_message params: {sorted(unknown)}"
    assert rec.calls[0]["body"]["params"]["role"] in roles

    print(f"ok: three POST {PATH} calling.ai_message for id {CALL[:8]}...: a system "
          f"message, a global_data merge and a full reset, every param documented")


if __name__ == "__main__":
    main()
