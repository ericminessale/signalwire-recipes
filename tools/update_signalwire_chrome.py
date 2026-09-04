#!/usr/bin/env python3
"""Refresh the official SignalWire header/footer source without transforming it."""
import hashlib
import pathlib
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "signalwire-chrome.html"
SOURCE = "https://signalwire.com/landing/chrome/template.html"

REQUIRED = (
    b"CUT HERE \xe2\x80\x94 START OF CONTENT",
    b"CUT HERE \xe2\x80\x94 END OF CONTENT",
    b'<nav class="fr-nav">',
    b'<footer class="fr-foot">',
    b"GTM-567VSN6",
    b"GTM-T23S86H",
    b"js.hs-scripts.com/47316764.js",
    b"@signalwire/status-widget@0.2.0",
    b"<sw-status",
)


def main():
    request = urllib.request.Request(
        SOURCE, headers={"User-Agent": "signalwire-recipes chrome updater"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    missing = [needle.decode("utf-8") for needle in REQUIRED if needle not in data]
    if missing:
        raise SystemExit("refusing unexpected chrome template; missing: " + ", ".join(missing))
    if not data.startswith(b"<!DOCTYPE html>") or not data.rstrip().endswith(b"</html>"):
        raise SystemExit("refusing incomplete chrome template")

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"updated {TARGET.relative_to(ROOT)} ({len(data)} bytes, sha256 {digest})")


if __name__ == "__main__":
    main()
