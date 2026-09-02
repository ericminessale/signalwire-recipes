"""Prove the claim without a network.

Claim: no outbound call is placed to a number without a consent record and
inside the permitted local calling window, and the check runs in code before
the dial.

Proof: with the HTTP layer replaced by a recorder, `place()` for a number with
no record, a number whose consent was withdrawn, and a consented number at
21:30 local time each raise `NoConsent` naming the reason, and the recorder
sees no request. The same consented number at 10:00 local time makes exactly
one POST to the documented calling path with `command: dial` and documented
params. The window is checked in the callee's zone, not the server's. Expected
values live here, not in app.py.
"""
import os
import pathlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))
os.environ.update({
    "SIGNALWIRE_PROJECT_ID": "proj-1234",
    "SIGNALWIRE_API_TOKEN": "PT-test",
    "SIGNALWIRE_SPACE": "example.signalwire.com",
    "SIGNALWIRE_PHONE_NUMBER": "+15550001111",
})

import verifylib as V  # noqa: E402

PATH = "/api/calling/calls"
OK, WITHDRAWN, UNKNOWN = "+15557654321", "+15550009999", "+15550001234"
# 04:30 UTC is 21:30 the previous evening in Los Angeles; 17:00 UTC is 10:00
LATE = datetime(2026, 9, 2, 4, 30, tzinfo=ZoneInfo("UTC"))
MORNING = datetime(2026, 9, 2, 17, 0, tzinfo=ZoneInfo("UTC"))


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder()
    recipe.client.calling._http = rec

    for number, when, reason in [(UNKNOWN, MORNING, "no consent on record"),
                                 (WITHDRAWN, MORNING, "consent withdrawn"),
                                 (OK, LATE, "outside the calling window")]:
        try:
            recipe.place(number, "hello", now=when)
        except recipe.NoConsent as e:
            assert reason in str(e), (number, str(e))
        else:
            raise AssertionError(f"{number} at {when} was dialled")
        assert rec.calls == [], rec.calls  # the check ran before any request

    # the window is the callee's local time: 17:00 UTC is 10:00 in Los Angeles
    assert recipe.allowed(OK, MORNING) is None
    assert "21:30" in recipe.allowed(OK, LATE)

    recipe.place(OK, "Your bike is ready.", now=MORNING)
    assert len(rec.calls) == 1, rec.calls
    (call,) = rec.calls
    assert (call["method"], call["path"]) == ("POST", PATH), call
    body = call["body"]
    assert body["command"] == "dial", body
    params = body["params"]
    assert params["to"] == OK and params["from"] == "+15550001111", params
    V.assert_documented("rest", "POST", PATH, None)
    schema = V.spec("rest")["components"]["schemas"]["Calling.CallCreateParamsSWML"]
    assert set(params) <= set(schema["properties"]), sorted(set(params) - set(schema["properties"]))
    assert set(schema.get("required", [])) <= set(params), schema.get("required")
    V.validate_swml(params["swml"])

    print(f"ok: no record, withdrawn consent and 21:30 local each raised NoConsent with "
          f"no request; the consented number at 10:00 local made one POST {PATH} "
          f"command=dial with documented params and valid inline SWML")


if __name__ == "__main__":
    main()
