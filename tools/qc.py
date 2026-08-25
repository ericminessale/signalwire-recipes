#!/usr/bin/env python3
"""Render QC for the preview. Refuses on the bugs that got through by looking
at code or at the top of a page instead of using it.

    python tools/qc.py                # serves site/ itself, checks, exits non-zero on failure
    python tools/qc.py --url http://127.0.0.1:8765/preview.html

Checks, at 2560 / 1920 / 1280x720 / 820:
  overflow   no code pane or README code block wider than its box
  overlap    scrolled to several offsets, no heading or paragraph in a recipe
             view is covered by the (sticky) code block
  click      a card click swaps the view; back returns to the index
  toggle     the unbuilt toggle hides cards on screen (painted count), not just
             by attribute
  tabs       switching surface tabs changes the visible pane's text
  banner     the preview banner shows on the index and not on a recipe page

Uses playwright-cli (the repo's rendering tool). Each check evaluates in the
page and returns JSON; this script only reads verdicts.
"""
import json
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
SESSION = "qc"
VIEWPORTS = ((2560, 1100), (1920, 1000), (1280, 720), (820, 900))  # (width, height); 1280x720 is a laptop
RECIPES_TO_CHECK = ("scope-tools-per-step", "build-an-ivr-menu", "register-a-10dlc-brand-and-campaign")


def pw(*args, timeout=90):
    exe = shutil.which("playwright-cli") or shutil.which("playwright-cli.cmd")
    if not exe:
        raise SystemExit("playwright-cli not on PATH")
    r = subprocess.run([exe, f"-s={SESSION}", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r.stdout + r.stderr


def evaljs(expr):
    out = pw("eval", expr)
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            return json.loads(json.loads(line))  # eval returns a JSON string, quoted
    raise RuntimeError("no result from eval:\n" + out[-800:])


def goto(url):
    pw("goto", url)


def serve(directory):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    httpd = ThreadingHTTPServer(("127.0.0.1", port), lambda *a, **k: Quiet(*a, directory=str(directory), **k))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}"


JS_OVERFLOW = """(function(){var bad=[];document.querySelectorAll('[data-view]:not([hidden]) pre.src:not([hidden]), [data-view]:not([hidden]) pre.mdcode').forEach(function(p){if(p.scrollWidth>p.clientWidth+1)bad.push({cls:p.className,over:p.scrollWidth-p.clientWidth});});return JSON.stringify({bad:bad})})()"""

JS_OVERLAP = """(function(){var v=document.querySelector('[data-view]:not([hidden])');var cw=v&&v.querySelector('.cw');if(!cw)return JSON.stringify({covered:[]});var covered=[];var offs=[0,400,900,1400,2200,3200];offs.forEach(function(y){window.scrollTo(0,y);var c=cw.getBoundingClientRect();if(c.height===0)return;v.querySelectorAll('.dmain h2,.dmain p,.rels h3,.dfoot a').forEach(function(el){var r=el.getBoundingClientRect();if(r.height===0)return;if(r.top<c.bottom&&r.bottom>c.top&&r.left<c.right-1&&r.right>c.left+1)covered.push({at:y,text:el.textContent.slice(0,40)});});});window.scrollTo(0,0);return JSON.stringify({covered:covered.slice(0,5),n:covered.length})})()"""

JS_CLICK = """(function(){var a=document.querySelector('a.card[href]');if(!a)return JSON.stringify({error:'no card'});var before=[].slice.call(document.querySelectorAll('[data-view]')).filter(function(x){return !x.hidden}).map(function(x){return x.dataset.view});a.click();var after=[].slice.call(document.querySelectorAll('[data-view]')).filter(function(x){return !x.hidden}).map(function(x){return x.dataset.view});var banner=document.querySelector('.pvbanner');var bannerOnDetail=banner?!banner.hidden:false;var back=document.querySelector('[data-view]:not([hidden]) [data-home]');if(back)back.click();var home=[].slice.call(document.querySelectorAll('[data-view]')).filter(function(x){return !x.hidden}).map(function(x){return x.dataset.view});return JSON.stringify({before:before,after:after,home:home,bannerOnDetail:bannerOnDetail,bannerOnIndex:banner?!banner.hidden:null})})()"""

JS_TOGGLE = """(function(){var b=document.getElementById('pvtog');if(!b)return JSON.stringify({skip:true});var paint=function(){return [].slice.call(document.querySelectorAll('.card,.buildcard')).filter(function(c){return getComputedStyle(c).display!=='none'}).length};var stale=function(){var bad=[];document.querySelectorAll('details.cat').forEach(function(g){g.querySelectorAll('.tgroup').forEach(function(tg){var k=[].slice.call(tg.querySelectorAll('.card')).filter(function(c){return getComputedStyle(c).display!=='none'}).length;var strip=g.querySelector('.tgs .tg[data-g="'+tg.dataset.g+'"]');if(!strip)return;var shown=strip.hidden?0:parseInt(strip.querySelector('.cn').textContent,10);if(shown!==k)bad.push(tg.dataset.g+':'+shown+'!='+k);});});return bad};var before=paint();b.click();var after=paint();var sw1=!!b.querySelector('.sw');var badStrip=stale();b.click();var sw2=!!b.querySelector('.sw');return JSON.stringify({before:before,after:after,total:document.querySelectorAll('.card,.buildcard').length,hasSwitch:sw1&&sw2,staleStrip:badStrip.slice(0,4)})})()"""

JS_TABS = """(function(){var v=document.querySelector('[data-view]:not([hidden])');var tabs=v?v.querySelectorAll('.stab'):[];if(tabs.length<2)return JSON.stringify({skip:true});var t0=v.querySelector('pre.src:not([hidden])').textContent.slice(0,40);tabs[1].click();var t1=v.querySelector('pre.src:not([hidden])').textContent.slice(0,40);var f1=v.querySelector('.fn:not([hidden])').textContent;tabs[0].click();return JSON.stringify({t0:t0,t1:t1,fn:f1,changed:t0!==t1})})()"""


def main(argv):
    url = None
    if "--url" in argv:
        url = argv[argv.index("--url") + 1]
    httpd = None
    if not url:
        site = ROOT / "site"
        if not (site / "preview.html").exists():
            raise SystemExit("site/preview.html missing - run: python build.py && python build.py --preview --all")
        httpd, base = serve(site)
        url = base + "/preview.html"
    failures = []

    def fail(width, check, detail):
        failures.append(f"{width:>5}  {check:<9} {detail}")

    pw("open", url, timeout=120)
    try:
        for w, h in VIEWPORTS:
            pw("resize", str(w), str(h))
            goto(url)
            pw("reload")
            r = evaljs(JS_CLICK)
            if len(r.get("after") or []) != 1:
                fail(w, "click", f"exactly one view must be visible after a click, got {r.get('after')}")
            if not r.get("after") or r["after"] == ["index"]:
                fail(w, "click", f"card click did not open a recipe: {r}")
            if r.get("home") != ["index"]:
                fail(w, "click", f"back did not return to the index: {r.get('home')}")
            if r.get("bannerOnDetail"):
                fail(w, "banner", "preview banner visible on a recipe page")
            if r.get("bannerOnIndex") is False:
                fail(w, "banner", "preview banner missing on the index")
            r = evaljs(JS_TOGGLE)
            if not r.get("skip"):
                if not (r["after"] < r["before"]):
                    fail(w, "toggle", f"toggle did not reduce painted cards ({r['before']} -> {r['after']} of {r['total']})")
                if not r.get("hasSwitch"):
                    fail(w, "toggle", "the switch element (.sw) disappeared after clicking")
                if r.get("staleStrip"):
                    fail(w, "toggle", f"category header strip did not follow the toggle: {r['staleStrip']}")
            for slug in RECIPES_TO_CHECK:
                goto(f"{url}#{slug}")
                pw("reload")
                r = evaljs(JS_OVERFLOW)
                if r["bad"]:
                    fail(w, "overflow", f"{slug}: {r['bad']}")
                r = evaljs(JS_OVERLAP)
                if r["n"]:
                    fail(w, "overlap", f"{slug}: code block covers {r['n']} element(s), e.g. {r['covered'][:2]}")
                r = evaljs(JS_TABS)
                if not r.get("skip") and not r.get("changed"):
                    fail(w, "tabs", f"{slug}: switching tabs did not change the pane ({r})")
    finally:
        pw("close")
        if httpd:
            httpd.shutdown()

    if failures:
        print("QC FAILED")
        for f in failures:
            print("  " + f)
        return 1
    print("QC ok: overflow, overlap, click, toggle, tabs, banner at "
          + ", ".join(f"{w}x{h}" for w, h in VIEWPORTS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
