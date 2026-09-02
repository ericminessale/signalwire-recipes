"""Prove the claim without a network.

Claim: a pass over a time window of the voice and message logs finds the calls
and messages your webhook handler never recorded, and fetches the event trail
of each missed call.

Proof: with the HTTP layer replaced by a recorder that answers with fixture
pages, `reconcile` makes one GET to the documented voice logs path and one to
the documented message logs path, each with `created_after`, `created_before`
and `page_size` as documented query parameters. It then makes one GET to the
documented events path for each voice log whose id is not in `SEEN`, and none
for the ones that are. The report lists exactly the missed entries. Expected
values live here, not in app.py.
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

VOICE, MESSAGES = "/api/voice/logs", "/api/messaging/logs"
EVENTS = "/api/voice/logs/{id}/events"
SINCE, UNTIL = "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z"
VOICE_PAGE = {"data": [{"id": "call-seen", "status": "ended"},
                       {"id": "call-missed", "status": "ended"}], "links": {}}
MESSAGE_PAGE = {"data": [{"id": "msg-seen", "status": "delivered"},
                         {"id": "msg-missed", "status": "failed"}], "links": {}}
TRAIL = {"data": [{"name": "call.answered", "event_at": "2026-09-01T10:00:00Z"}]}


def main():
    V.sdk_banner()
    import app as recipe

    recipe.SEEN.update({"call-seen", "msg-seen"})
    rec = V.Recorder(responses=[VOICE_PAGE, TRAIL, MESSAGE_PAGE])
    for ns in (recipe.client.logs.voice, recipe.client.logs.messages):
        ns._http = rec

    report = recipe.reconcile(SINCE, UNTIL)

    assert [(c["method"], c["path"]) for c in rec.calls] == [
        ("GET", VOICE), ("GET", EVENTS.replace("{id}", "call-missed")), ("GET", MESSAGES)], \
        [(c["method"], c["path"]) for c in rec.calls]
    window = {"created_after": SINCE, "created_before": UNTIL, "page_size": 200}
    assert rec.calls[0]["params"] == window and rec.calls[2]["params"] == window, rec.calls
    assert rec.calls[1]["params"] is None, rec.calls[1]
    V.assert_documented("rest", "GET", VOICE, None, window)
    V.assert_documented("rest", "GET", MESSAGES, None, window)
    V.assert_documented("rest", "GET", EVENTS.replace("{id}", "call-missed"), None)

    # the report holds exactly what the webhook never saw, with the trail
    assert [v["log"]["id"] for v in report["voice"]] == ["call-missed"], report
    assert report["voice"][0]["events"] == TRAIL, report["voice"][0]
    assert [m["id"] for m in report["messages"]] == ["msg-missed"], report

    # the spec's own bounds on page_size, so the default here is legal
    spec = V.spec("rest")
    ps = next(p for p in spec["paths"][VOICE]["get"]["parameters"] if p["name"] == "page_size")
    assert ps["schema"]["minimum"] <= 200 <= ps["schema"]["maximum"], ps["schema"]

    print(f"ok: GET {VOICE} and {MESSAGES} for the window with page_size 200, one GET "
          f"{EVENTS} for the missed call only; the report names call-missed and "
          f"msg-missed and nothing your webhook saw")


if __name__ == "__main__":
    main()
