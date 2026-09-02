"""Prove the claim without a network.

Claim: a pass over a time window walks every page of the voice and message
logs, reports every entry your handler's store lacks, and fetches the event
trail of each such call.

Proof: the HTTP layer is a recorder that answers with fixtures: two voice
pages joined by a `links.next` URL, one message page, and a trail per unseen
call. `reconcile` makes the requests in order: the first voice page with the
window parameters, the second with the parameters from the next link, one
events request per unseen call, then the message page. The report lists
exactly the unseen calls with their trails and the unseen messages, including
a call that sat on the second page. The spec bounds `page_size` between 1 and
1000 on both lists. Expected values live here, not in app.py.
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
WINDOW = {"created_after": SINCE, "created_before": UNTIL, "page_size": 200}
NEXT = f"https://example.signalwire.com{VOICE}?page_token=tok2&page_size=200"
VOICE_PAGE_1 = {"data": [{"id": "call-seen", "status": "ended"},
                         {"id": "call-missed-1", "status": "ended"}],
                "links": {"self": "...", "next": NEXT}}
VOICE_PAGE_2 = {"data": [{"id": "call-missed-2", "status": "failed"}], "links": {"self": "..."}}
MESSAGE_PAGE = {"data": [{"id": "msg-seen", "status": "delivered"},
                         {"id": "msg-missed-1", "status": "failed"},
                         {"id": "msg-missed-2", "status": "undelivered"}], "links": {}}
TRAILS = {"call-missed-1": {"data": [{"name": "call.answered", "event_at": "2026-09-01T10:00:00Z"}]},
          "call-missed-2": {"data": [{"name": "call.failed", "event_at": "2026-09-01T11:00:00Z"}]}}


def main():
    V.sdk_banner()
    import app as recipe

    recipe.SEEN.update({"call-seen", "msg-seen"})
    rec = V.Recorder(responses=[VOICE_PAGE_1, VOICE_PAGE_2, TRAILS["call-missed-1"],
                                TRAILS["call-missed-2"], MESSAGE_PAGE])
    for ns in (recipe.client.logs.voice, recipe.client.logs.messages):
        ns._http = rec

    report = recipe.reconcile(SINCE, UNTIL)

    expected = [("GET", VOICE), ("GET", VOICE),
                ("GET", EVENTS.replace("{id}", "call-missed-1")),
                ("GET", EVENTS.replace("{id}", "call-missed-2")), ("GET", MESSAGES)]
    assert [(c["method"], c["path"]) for c in rec.calls] == expected, \
        [(c["method"], c["path"]) for c in rec.calls]
    page1, page2, ev1, ev2, msgs = rec.calls
    assert page1["params"] == WINDOW, page1
    # the second page carries the query the next link gave, not the window
    assert page2["params"] == {"page_token": "tok2", "page_size": "200"}, page2
    assert msgs["params"] == WINDOW, msgs
    assert ev1["params"] is None and ev2["params"] is None, (ev1, ev2)
    V.assert_documented("rest", "GET", VOICE, None, WINDOW)
    V.assert_documented("rest", "GET", VOICE, None, page2["params"])
    V.assert_documented("rest", "GET", MESSAGES, None, WINDOW)
    for c in (ev1, ev2):
        V.assert_documented("rest", "GET", c["path"], None)

    # the report holds exactly the entries SEEN lacks, across pages, each call
    # with its trail
    assert [v["log"]["id"] for v in report["voice"]] == ["call-missed-1", "call-missed-2"], report
    assert [v["events"] for v in report["voice"]] == [TRAILS["call-missed-1"], TRAILS["call-missed-2"]]
    assert [m["id"] for m in report["messages"]] == ["msg-missed-1", "msg-missed-2"], report

    # the spec's own bounds on page_size, on both lists
    spec = V.spec("rest")
    for path in (VOICE, MESSAGES):
        ps = next(p for p in spec["paths"][path]["get"]["parameters"] if p["name"] == "page_size")
        assert ps["schema"]["minimum"] <= 200 <= ps["schema"]["maximum"], (path, ps["schema"])

    print(f"ok: two voice pages walked through links.next, one message page, one events "
          f"request per unseen call; the report names both unseen calls (one from page two) "
          f"with trails and both unseen messages")


if __name__ == "__main__":
    main()
