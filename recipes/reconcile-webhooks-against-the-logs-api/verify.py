"""Prove the claim without a network.

Claim: a pass over a time window walks every page of the voice and message
logs. It reports every entry your handler's store lacks, and fetches the event
trail of each such call.

Proof: the HTTP layer is a recorder that answers with fixtures: two voice
pages, two message pages, and a trail per unseen call. In each list, page
one's `links.next` URL points at page two. `reconcile` makes the requests in
order. Voice page one carries the window parameters and voice page two the
parameters from the next link, then one events request per unseen call. The
two message pages follow the same way. The report lists exactly the unseen calls with
their trails and the unseen messages, including one call and one message that
sat on a second page. The spec bounds `page_size` at exactly 1 and 1000 on
both lists. Expected values live here, not in app.py.
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
MNEXT = f"https://example.signalwire.com{MESSAGES}?page_token=mtok2&page_size=200"
MESSAGE_PAGE_1 = {"data": [{"id": "msg-seen", "status": "delivered"},
                           {"id": "msg-missed-1", "status": "failed"}],
                  "links": {"self": "...", "next": MNEXT}}
MESSAGE_PAGE_2 = {"data": [{"id": "msg-missed-2", "status": "undelivered"}],
                  "links": {"self": "..."}}


def trail(log_id, name, at, level):
    return {"data": [{"name": name, "event_at": at, "level": level, "details": {},
                      "project_id": "proj-1234", "log_id": log_id}]}


TRAILS = {"call-missed-1": trail("call-missed-1", "call.answered", "2026-09-01T10:00:00Z", "info"),
          "call-missed-2": trail("call-missed-2", "call.failed", "2026-09-01T11:00:00Z", "error")}


def main():
    V.sdk_banner()
    import app as recipe

    recipe.SEEN.update({"call-seen", "msg-seen"})
    rec = V.Recorder(responses=[VOICE_PAGE_1, VOICE_PAGE_2, TRAILS["call-missed-1"],
                                TRAILS["call-missed-2"], MESSAGE_PAGE_1, MESSAGE_PAGE_2])
    for ns in (recipe.client.logs.voice, recipe.client.logs.messages):
        ns._http = rec

    report = recipe.reconcile(SINCE, UNTIL)

    expected = [("GET", VOICE), ("GET", VOICE),
                ("GET", EVENTS.replace("{id}", "call-missed-1")),
                ("GET", EVENTS.replace("{id}", "call-missed-2")),
                ("GET", MESSAGES), ("GET", MESSAGES)]
    assert [(c["method"], c["path"]) for c in rec.calls] == expected, \
        [(c["method"], c["path"]) for c in rec.calls]
    page1, page2, ev1, ev2, msgs1, msgs2 = rec.calls
    assert page1["params"] == WINDOW, page1
    # a second page carries the query its next link gave, not the window
    assert page2["params"] == {"page_token": "tok2", "page_size": "200"}, page2
    assert msgs1["params"] == WINDOW, msgs1
    assert msgs2["params"] == {"page_token": "mtok2", "page_size": "200"}, msgs2
    assert ev1["params"] is None and ev2["params"] is None, (ev1, ev2)
    V.assert_documented("rest", "GET", VOICE, None, WINDOW)
    V.assert_documented("rest", "GET", VOICE, None, page2["params"])
    V.assert_documented("rest", "GET", MESSAGES, None, WINDOW)
    V.assert_documented("rest", "GET", MESSAGES, None, msgs2["params"])
    for c in (ev1, ev2):
        V.assert_documented("rest", "GET", c["path"], None)

    # the report holds exactly the entries SEEN lacks, across pages, each call
    # with its trail
    assert [v["log"]["id"] for v in report["voice"]] == ["call-missed-1", "call-missed-2"], report
    assert [v["events"] for v in report["voice"]] == [TRAILS["call-missed-1"], TRAILS["call-missed-2"]]
    assert [m["id"] for m in report["messages"]] == ["msg-missed-1", "msg-missed-2"], report

    # each event in a trail is shaped like the spec's event entry
    spec = V.spec("rest")
    schemas = spec["components"]["schemas"]

    def deref(node):
        while isinstance(node, dict) and "$ref" in node:
            node = schemas[node["$ref"].split("/")[-1]]
        return node

    events_schema = deref(spec["paths"][EVENTS]["get"]["responses"]["200"]["content"]
                          ["application/json"]["schema"])
    entry = deref(deref(events_schema["properties"]["data"])["items"])
    levels = deref(entry["properties"]["level"])["enum"]
    for fixture in TRAILS.values():
        for e in fixture["data"]:
            assert set(entry["required"]) <= set(e), sorted(set(entry["required"]) - set(e))
            assert set(e) <= set(entry["properties"]), sorted(set(e) - set(entry["properties"]))
            assert e["level"] in levels, (e["level"], levels)

    # the spec's own bounds on page_size, on both lists
    for path in (VOICE, MESSAGES):
        ps = next(p for p in spec["paths"][path]["get"]["parameters"] if p["name"] == "page_size")
        assert (ps["schema"]["minimum"], ps["schema"]["maximum"]) == (1, 1000), (path, ps["schema"])

    print(f"ok: two voice pages and two message pages walked through links.next, one events "
          f"request per unseen call; the report names both unseen calls and both unseen "
          f"messages, one of each from a second page, the calls with trails")


if __name__ == "__main__":
    main()
