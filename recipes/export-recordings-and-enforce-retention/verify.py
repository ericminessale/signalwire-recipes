"""Prove the claim without a network.

Claim: a pass lists every call recording across pages, copies each one older
than your retention window to storage you control, and then deletes it from
SignalWire. Nothing is deleted that was not copied first.

Proof: the HTTP layer is a recorder that answers with two recording pages
joined by `links.next`: two recordings past the window, one inside it. The
media fetcher is a fake that records the URLs it was asked for. The pass makes
GET, GET, DELETE, DELETE in that order, downloads exactly the two expired
URLs, writes each to the export directory under its id, and leaves the fresh
one alone. A second pass whose fetcher raises makes no DELETE at all. Every
path is documented, the delete answers 204, and the spec's recording variants
all carry `id`, `created_at` and `url`. Expected values live here, not in
app.py.
"""
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))
EXPORTS = pathlib.Path(tempfile.mkdtemp(prefix="recipe-exports-"))
os.environ.update({
    "SIGNALWIRE_PROJECT_ID": "proj-1234",
    "SIGNALWIRE_API_TOKEN": "PT-test",
    "SIGNALWIRE_SPACE": "example.signalwire.com",
    "RETENTION_DAYS": "30",
    "EXPORT_DIR": str(EXPORTS),
})

import verifylib as V  # noqa: E402

PATH = "/api/relay/rest/recordings"
NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
NEXT = f"https://example.signalwire.com{PATH}?page_token=tok2"


def recording(rid, created, ext="wav"):
    return {"id": rid, "created_at": created, "status": "finished", "duration_in_seconds": 61,
            "url": f"https://example.signalwire.com/api/relay/rest/recordings/{rid}.{ext}"}


OLD1 = recording("rec-old-1", "2026-07-01T09:00:00Z")          # 63 days old
FRESH = recording("rec-fresh", "2026-08-30T09:00:00Z")         # 3 days old
OLD2 = recording("rec-old-2", "2026-08-02T09:00:00Z", "mp3")   # 31 days old
PAGE1 = {"data": [OLD1, FRESH], "links": {"self": "...", "next": NEXT}}
PAGE2 = {"data": [OLD2], "links": {"self": "..."}}


def deref(spec, node):
    schemas = spec["components"]["schemas"]
    while isinstance(node, dict) and "$ref" in node:
        node = schemas[node["$ref"].split("/")[-1]]
    return node


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder(responses=[PAGE1, PAGE2, {}, {}])
    recipe.client.recordings._http = rec
    fetched = []

    def fake_fetch(url):
        fetched.append(url)
        return b"RIFF" + url.encode()

    moved = recipe.export_and_delete(now=NOW, fetch=fake_fetch)

    expected = [("GET", PATH), ("GET", PATH), ("DELETE", f"{PATH}/rec-old-1"),
                ("DELETE", f"{PATH}/rec-old-2")]
    assert [(c["method"], c["path"]) for c in rec.calls] == expected, \
        [(c["method"], c["path"]) for c in rec.calls]
    page1, page2 = rec.calls[:2]
    assert page1["params"] is None, page1
    assert page2["params"] == {"page_token": "tok2"}, page2
    assert fetched == [OLD1["url"], OLD2["url"]], fetched
    assert [m["id"] for m in moved] == ["rec-old-1", "rec-old-2"], moved
    for m, ext in zip(moved, ("wav", "mp3")):
        path = pathlib.Path(m["path"])
        assert path == EXPORTS / f"{m['id']}.{ext}", path
        assert path.read_bytes() == b"RIFF" + f"https://example.signalwire.com{PATH}/{m['id']}.{ext}".encode()
    assert not (EXPORTS / "rec-fresh.wav").exists()

    # a copy that fails stops the pass before the delete
    rec2 = V.Recorder(responses=[{"data": [OLD1], "links": {}}])
    recipe.client.recordings._http = rec2

    def broken_fetch(url):
        raise OSError("storage unreachable")

    try:
        recipe.export_and_delete(now=NOW, fetch=broken_fetch)
    except OSError:
        pass
    else:
        raise AssertionError("a failed copy did not stop the pass")
    assert [c["method"] for c in rec2.calls] == ["GET"], rec2.calls

    # the spec's word on the two paths
    spec = V.spec("rest")
    V.assert_documented("rest", "GET", PATH, None)
    V.assert_documented("rest", "GET", PATH, None, page2["params"])
    V.assert_documented("rest", "DELETE", f"{PATH}/{{id}}", None)
    delete = spec["paths"][f"{PATH}/{{id}}"]["delete"]
    assert "204" in delete["responses"], list(delete["responses"])
    listing = deref(spec, spec["paths"][PATH]["get"]["responses"]["200"]["content"]["application/json"]["schema"])
    assert "links" in listing["properties"], sorted(listing["properties"])
    items = deref(spec, deref(spec, listing["properties"]["data"])["items"])
    variants = [deref(spec, v) for v in items.get("oneOf", [items])]
    assert len(variants) >= 1
    for variant in variants:
        props = variant["properties"]
        assert {"id", "created_at", "url", "duration_in_seconds"} <= set(props), sorted(props)
        assert "recording file" in deref(spec, props["url"])["description"], props["url"]
    for fixture in (OLD1, FRESH, OLD2):
        assert set(fixture) <= set(variants[0]["properties"]), sorted(set(fixture) - set(variants[0]["properties"]))

    print(f"ok: two pages walked, {len(fetched)} expired recordings copied to {EXPORTS.name} "
          f"then deleted in order, the 3-day-old one kept; a failed copy made no DELETE")


if __name__ == "__main__":
    main()
