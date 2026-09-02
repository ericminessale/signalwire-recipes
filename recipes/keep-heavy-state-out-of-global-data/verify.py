"""Prove the claim without a network.

Claim: per-call state lives server-side keyed by call_id, and only a short
AI-facing summary is written to global_data.

Proof: record three long findings on one call and one on another. After each,
the `set_global_data` action carries only a count and a comma-separated list
of areas, never the detail text, and stays under a fixed size while the store
grows past it. The store holds the full text under each call id and the two
calls do not mix. `read_back_report` returns every detail from the store for
its own call and nothing for a call with no findings. Expected values live
here, not in app.py.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))

import verifylib as V  # noqa: E402

# what a reader's .env supplies; without it the SDK generates a password that
# exists only in this process and the number's webhook gets a 401
os.environ.setdefault("SWML_BASIC_AUTH_USER", "signalwire")
os.environ.setdefault("SWML_BASIC_AUTH_PASSWORD", "verify-only-password")

# Expected values live here, not imported from app.py.
AREAS = ["brakes", "gears", "wheels", "frame", "lights"]
FINDINGS_A = [
    ("brakes", "Front pads worn to the wear line, rear pads glazed, both calipers "
               "sticking on release; recommend new pads and a caliper service."),
    ("gears", "Rear derailleur hanger bent inwards, cable frayed at the barrel "
              "adjuster, shifting skips under load in the three smallest cogs."),
    ("wheels", "Rear wheel out of true by about four millimetres with two loose "
               "spokes on the drive side; front bearing has slight play."),
]
FINDING_B = ("lights", "Rear light bracket cracked.")
GLOBAL_DATA_CAP = 120  # bytes of JSON per set_global_data action


def run(agent, call_id, tool, **args):
    raw = {"call_id": call_id, "argument": {"parsed": [args]}}
    return agent._execute_swaig_function(tool, args, call_id=call_id, raw_data=raw)


def main():
    V.sdk_banner()
    import app as recipe

    agent = recipe.agent
    V.assert_basic_auth_from_env(agent)
    doc = json.loads(agent._render_swml())
    V.validate_swml(doc)
    ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]
    fns = {f["function"]: f for f in ai["SWAIG"]["functions"]}
    assert sorted(fns) == ["read_back_report", "record_finding"], sorted(fns)
    assert fns["record_finding"]["parameters"]["properties"]["area"]["enum"] == AREAS

    recipe.STORE.clear()
    for n, (area, detail) in enumerate(FINDINGS_A, 1):
        r = run(agent, "call-A", "record_finding", area=area, detail=detail)
        (action,) = r["action"]
        gd = action["set_global_data"]
        # a count and the areas, and the detail text is not in it
        assert gd == {"findings": n,
                      "areas": ", ".join(a for a, _ in FINDINGS_A[:n])}, gd
        assert detail[:20] not in json.dumps(gd), gd
        assert len(json.dumps(gd)) <= GLOBAL_DATA_CAP, (len(json.dumps(gd)), gd)
    # the store has every word, and it is already bigger than the cap allows
    stored = recipe.STORE["call-A"]
    assert [(f["area"], f["detail"]) for f in stored] == FINDINGS_A, stored
    assert len(json.dumps(stored)) > GLOBAL_DATA_CAP * 3, len(json.dumps(stored))

    # another call is another record
    r = run(agent, "call-B", "record_finding", area=FINDING_B[0], detail=FINDING_B[1])
    assert r["action"] == [{"set_global_data": {"findings": 1, "areas": "lights"}}], r
    assert [(f["area"], f["detail"]) for f in recipe.STORE["call-B"]] == [FINDING_B]
    assert len(recipe.STORE["call-A"]) == 3

    # the read-back comes from the store, in full, for its own call only
    r = run(agent, "call-A", "read_back_report")
    assert "action" not in r, r
    for _, detail in FINDINGS_A:
        assert detail in r["response"], (detail[:30], r["response"][:80])
    assert FINDING_B[1] not in r["response"]
    r = run(agent, "call-C", "read_back_report")
    assert r["response"].startswith("INCOMPLETE") and "action" not in r, r

    # a bad finding writes nowhere
    r = run(agent, "call-A", "record_finding", area="saddle", detail="torn")
    assert r["response"].startswith("INVALID") and "action" not in r, r
    assert len(recipe.STORE["call-A"]) == 3

    print(f"ok: three findings on call-A kept every set_global_data under "
          f"{GLOBAL_DATA_CAP} bytes while the store holds "
          f"{len(json.dumps(stored))} bytes; call-B is separate; read_back_report "
          f"returns the full text from the store")


if __name__ == "__main__":
    main()
