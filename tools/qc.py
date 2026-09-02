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
  contrast   every text run meets WCAG AA against its composited background.
             The two fuchsia buttons are a knowing exception: white on
             #F72A72 is 3.8:1, under AA at that size, but the compliant
             dark text read as harder to see on a saturated fill and the
             white is the owner's design.
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
# (width, height). 1280x720 is a laptop; 390x844 is a phone, added
# 2026-08-26 because the site had a viewport meta tag and no phone-width
# check, so the chip strip's wrapped state was never exercised.
VIEWPORTS = ((2560, 1100), (1920, 1000), (1280, 720), (820, 900), (390, 844))
# slugs known to carry a transcript: a missing slot here is a
# deleted player, not an absent feature
REPLAY_SLUGS = ("scope-tools-per-step",)
RECIPES_TO_CHECK = ("scope-tools-per-step", "build-an-ivr-menu", "register-a-10dlc-brand-and-campaign")


JS_FEATURED = """(function(){var f=document.querySelector('.feat');if(!f)return JSON.stringify({skip:true});var paint=function(e){return getComputedStyle(e).display!=='none'};var cards=function(sel){return [].slice.call(f.querySelectorAll(sel)).filter(paint).length};var q=document.getElementById('q');var chip=[].slice.call(document.querySelectorAll('.chip')).filter(function(c){return c.dataset.f&&c.dataset.f!=='all'&&c.dataset.f.indexOf('kind:')!==0})[0];var o={dup:document.querySelectorAll('.fcard.card').length};o.initial=paint(f);q.value='transfer';q.dispatchEvent(new Event('input'));o.onSearch=paint(f);q.value='';q.dispatchEvent(new Event('input'));o.cleared=paint(f);if(chip){chip.click();o.onChip=paint(f);chip.click();o.chipOff=paint(f);}var t=document.getElementById('pvtog');if(t){var before=cards('.fcard');o.plannedBefore=cards('.fcard.planned');t.click();o.togBand=paint(f);o.togShrank=cards('.fcard')<before;o.togPlanned=cards('.fcard.planned');t.click();}return JSON.stringify(o)})()"""


JS_CAROUSEL = """(function(){var f=document.querySelector('.feat');if(!f)return JSON.stringify({skip:true});var t=f.querySelector('.ftrack');var cards=[].slice.call(f.querySelectorAll('.fcard'));if(!t||cards.length<2)return JSON.stringify({skip:true});var o={cards:cards.length};o.dots=f.querySelectorAll('.fdot').length;o.per=parseInt(t.style.getPropertyValue('--per'),10)||0;var w=f.querySelector('.fviewport');o.clipped=w?getComputedStyle(w).overflow==='hidden':false;var cw=cards[0].getBoundingClientRect().width;var vw=w?w.getBoundingClientRect().width:0;o.widthMatchesPer=(vw&&o.per)?Math.abs(cw-((vw-(o.per-1)*10)/o.per))<3:false;var live=cards.filter(function(c){return !c.hidden}).length;o.dotsMatch=o.per?o.dots===Math.ceil(live/o.per):false;var at=function(){return t.style.transform};var next=f.querySelector('.farrow[data-step="1"]');var prev=f.querySelector('.farrow[data-step="-1"]');var play=f.querySelector('.fplay');if(play)play.click();var was=at();next.click();o.moved=at()!==was;o.status=(f.querySelector('.fstatus')||{}).textContent||'';o.current=f.querySelectorAll('.fdot[aria-current="page"]').length;o.inert=f.querySelectorAll('.fcard[inert]').length;o.ariaHidden=f.querySelectorAll('.fcard[aria-hidden="true"]').length;o.reachable=cards.length-o.inert;prev.click();o.wrapped=at()===was;if(play){var lab=play.getAttribute('aria-label');next.click();prev.click();o.stillPaused=play.getAttribute('aria-label')===lab;play.click();}return JSON.stringify(o)})()"""


JS_CONTRAST = """(function(){var lin=function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};var lum=function(c){return 0.2126*lin(c[0])+0.7152*lin(c[1])+0.0722*lin(c[2])};var parse=function(s){var m=s&&s.match(/[\\d.]+/g);  if(!m)return null;return [+m[0],+m[1],+m[2],m.length>3?+m[3]:1]};var bgOf=function(el){var stack=[];var n=el;  while(n&&n.nodeType===1){var c=parse(getComputedStyle(n).backgroundColor);    if(c&&c[3]>0){stack.push(c); if(c[3]>=1)break;} n=n.parentElement;}  var out=[15,15,18];  for(var i=stack.length-1;i>=0;i--){var c=stack[i];    out=[0,1,2].map(function(k){return c[3]*c[k]+(1-c[3])*out[k]});}  return out};var bad=[];var seen=0;document.querySelectorAll('.detail *').forEach(function(el){  if(el.closest('.btn,.ghcta')) return;  var txt='';  for(var i=0;i<el.childNodes.length;i++){    if(el.childNodes[i].nodeType===3) txt+=el.childNodes[i].textContent;}  txt=txt.trim(); if(txt.length<6) return;  var r=el.getBoundingClientRect(); if(!r.width||!r.height) return;  var cs=getComputedStyle(el);  if(cs.visibility==='hidden'||parseFloat(cs.opacity)<0.6) return;  var fg=parse(cs.color); if(!fg) return;  var bg=bgOf(el);  if(fg[3]<1){fg=[0,1,2].map(function(k){return fg[3]*fg[k]+(1-fg[3])*bg[k]});}  var L1=lum(fg),L2=lum(bg);  var ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);  var px=parseFloat(cs.fontSize);  var wt=parseInt(cs.fontWeight,10)||400;  var large=(px>=24)||(px>=18.66&&wt>=700);  var need=large?3:4.5;  seen++;  if(ratio<need-0.01) bad.push({t:txt.slice(0,32),px:px,    r:Math.round(ratio*100)/100,need:need});});return JSON.stringify({checked:seen,bad:bad.slice(0,6),n:bad.length})})()"""

JS_REPLAY = """(function(){var v=document.querySelector('[data-view]:not([hidden])')||document;var slot=v.querySelector('[data-demo-slot]');if(!slot)return JSON.stringify({noslot:true});var btn=slot.querySelector('.trplay'),tr=slot.querySelector('.tr');var iso=document.createElement('style');iso.textContent='.dmain>.claim,.dmain>.ev,.dmain>.sec{animation:none!important;opacity:1!important;transform:none!important}';document.head.appendChild(iso);if(!btn||!tr)return JSON.stringify({noslot:true});var turns=[].slice.call(tr.querySelectorAll('.l,.sys'));var seen=function(){return turns.filter(function(t){  return t.checkVisibility?t.checkVisibility(    {checkOpacity:true,checkVisibilityCSS:true})  :getComputedStyle(t).display!=='none'}).length};var o={total:turns.length};o.restBefore=seen();o.hiddenAttr=btn.hidden;o.enabled=!btn.disabled;btn.click();o.playing=btn.dataset.state==='playing';o.stepping=tr.querySelectorAll('.on').length;o.inTreeDuring=turns.filter(function(t){return t.checkVisibility?t.checkVisibility({checkOpacity:false,checkVisibilityCSS:true}):getComputedStyle(t).display!=='none'}).length;btn.click();o.restAfter=seen();o.stopped=btn.dataset.state!=='playing';btn.click();Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));delete document.hidden;o.visStopped=btn.dataset.state!=='playing';o.restAfterVis=seen();o.replayClass=tr.classList.contains('replay');iso.remove();return JSON.stringify(o)})()"""

JS_DEADLINKS = """(function(){var bad=[];document.querySelectorAll('a[href]').forEach(function(a){  var h=a.getAttribute('href');  if(h==='#'||h===''||h===null)    bad.push((a.textContent||'').trim().slice(0,40)||a.className);});return JSON.stringify({bad:bad.slice(0,6),n:bad.length})})()"""

JS_CHROME = """(function(){var o={};var b=document.querySelector('.chip.kind');if(b&&b.previousElementSibling){  var prev=b.previousElementSibling;  var rg=document.createRange();rg.selectNodeContents(prev);  var ink=rg.getBoundingClientRect().right;  var bl=b.getBoundingClientRect().left;  var d=bl+parseFloat(getComputedStyle(b,'::before').left);  var sameRow=Math.abs(prev.getBoundingClientRect().top-b.getBoundingClientRect().top)<2;  if(sameRow){o.divFromInk=d-ink;o.divFromChip=bl-d;}  else{o.wrappedDividerPainted=getComputedStyle(b,'::before').content!=='none';}}var a=document.querySelector('.farrow');if(a){var cs=getComputedStyle(a);var r=a.getBoundingClientRect();  var ring=function(e){var c=getComputedStyle(e);return c.borderTopWidth!=='0px'||c.boxShadow!=='none'||c.backgroundImage!=='none'||(c.backgroundColor!=='rgba(0, 0, 0, 0)'&&c.backgroundColor!=='transparent')};  var pseudo=function(e,w){var c=getComputedStyle(e,w);return c.content!=='none'&&(c.borderTopWidth!=='0px'||(c.backgroundColor!=='rgba(0, 0, 0, 0)'&&c.backgroundColor!=='transparent'))};  o.arrowRing=ring(a)||pseudo(a,'::before')||pseudo(a,'::after');  o.arrowHit=Math.min(r.width,r.height);  var nx=document.querySelector('.farrow[data-step="1"]');  var pv=document.querySelector('.farrow[data-step="-1"]');  if(nx&&pv&&document.querySelectorAll('.fdot').length>1){    nx.click();o.pulseFwd=nx.classList.contains('pulse')&&!pv.classList.contains('pulse');    nx.classList.remove('pulse');pv.classList.remove('pulse');    pv.click();o.pulseBack=pv.classList.contains('pulse')&&!nx.classList.contains('pulse');  }}return JSON.stringify(o)})()"""

JS_RAIL = """(function(){var live=document.querySelector('.buildcard:not(.planned)');var planned=document.querySelector('.buildcard.planned');var F='rgb(247, 42, 114)';var has=function(e){return !!e&&getComputedStyle(e).boxShadow.indexOf(F)>=0};return JSON.stringify({live:!!live,liveRail:has(live),planned:!!planned,plannedRail:has(planned)})})()"""

JS_TASKGROUP = """(function(){var chip=document.querySelector('details.cat .tg');if(!chip)return JSON.stringify({skip:true});var cat=chip.closest('details.cat');var o={tag:chip.tagName,wasOpen:cat.open};cat.open=false;chip.click();o.opened=cat.open;var g=cat.querySelector('.tgroup[data-g="'+chip.dataset.g+'"]');o.hasGroup=!!g;o.focusable=chip.tabIndex>=0;var keys=[].slice.call(cat.querySelectorAll('.tg')).map(function(c){return c.dataset.g});var groups=[].slice.call(cat.querySelectorAll('.tgroup')).map(function(t){return t.dataset.g});o.orphans=keys.filter(function(k){return groups.indexOf(k)<0});return JSON.stringify(o)})()"""


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


JS_SIDESCROLL = """(function(){var d=document.documentElement;return JSON.stringify({over:d.scrollWidth-d.clientWidth,w:d.clientWidth})})()"""

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
            r = evaljs(JS_FEATURED)
            if not r.get("skip"):
                if r.get("dup"):
                    fail(w, "featured", f"{r['dup']} featured card(s) also answer to .card; "
                                        "every count on the page is inflated")
                if not r.get("initial"):
                    fail(w, "featured", "the band is not painted on a clean index")
                if r.get("onSearch"):
                    fail(w, "featured", "the band survived a search; it is a front door, not a result")
                if not r.get("cleared"):
                    fail(w, "featured", "the band did not come back when the search was cleared")
                if r.get("onChip"):
                    fail(w, "featured", "the band survived a category chip")
                if r.get("chipOff") is False:
                    fail(w, "featured", "the band did not come back when the chip was released")
                if r.get("togBand") is False:
                    fail(w, "featured", "hiding the unbuilt hid the whole band, not just its planned cards")
                # Only meaningful while some featured recipe is still unwritten.
                # With all six written there is nothing for the toggle to hide,
                # and demanding a shrink would fail on a fully built band.
                if r.get("plannedBefore") and r.get("togShrank") is False:
                    fail(w, "featured", "hiding the unbuilt left every featured card painted")
                if r.get("togPlanned"):
                    fail(w, "featured", f"{r['togPlanned']} planned featured card(s) still painted "
                                        "with the unbuilt hidden")
            r = evaljs(JS_CAROUSEL)
            if not r.get("skip"):
                if not r.get("moved"):
                    fail(w, "carousel", "the next arrow did not move the track")
                if not r.get("wrapped"):
                    fail(w, "carousel", "arrowing forward then back did not return")
                if not r.get("clipped"):
                    fail(w, "carousel", "the viewport does not clip")
                if not r.get("per"):
                    fail(w, "carousel", "--per is unset, so the cards are sized by the "
                                        "stylesheet rather than by the page size")
                if not r.get("widthMatchesPer"):
                    fail(w, "carousel", f"card width disagrees with --per={r.get('per')}")
                if not r.get("dotsMatch"):
                    fail(w, "carousel", f"{r.get('dots')} dots for {r.get('cards')} cards "
                                        f"at {r.get('per')} per page")
                if r.get("current") != 1:
                    fail(w, "carousel", f"{r.get('current')} dots aria-current, want 1")
                if not r.get("inert") or not r.get("ariaHidden"):
                    fail(w, "carousel", "offscreen cards are not inert and aria-hidden, "
                                        "so a screen reader still reaches them")
                if not r.get("reachable"):
                    fail(w, "carousel", "no featured card is reachable")
                if not r.get("status"):
                    fail(w, "carousel", "no status announced on a manual page change")
                if r.get("stillPaused") is False:
                    fail(w, "carousel", "using an arrow restarted a paused carousel")

            r = evaljs(JS_DEADLINKS)
            if r["n"]:
                fail(w, "deadlink", f"{r['n']} anchor(s) with href='#': "
                                    f"{r['bad']}")

            r = evaljs(JS_CHROME)
            if "divFromInk" in r:
                # a chip paints nothing over its padding, so measure ink to ink
                skew = abs(r["divFromInk"] - r["divFromChip"])
                if skew > 3:
                    fail(w, "divider", "the Builds divider is %.1fpx from the "
                                       "previous chip's text and %.1fpx from the "
                                       "Builds border; it must sit at the midpoint "
                                       "of what is painted"
                                       % (r["divFromInk"], r["divFromChip"]))
            if r.get("wrappedDividerPainted"):
                fail(w, "divider", "the chip strip wrapped and the Builds "
                                   "divider is still painted, so a rule that "
                                   "separates two chips hangs off a row edge")
            if r.get("arrowRing"):
                fail(w, "arrows", "the featured arrows have a ring (border or "
                                  "background); they are bare glyphs")
            if "arrowHit" in r and r["arrowHit"] < 44:
                fail(w, "arrows", "the arrow hit box is %.0fpx, under the 44px "
                                  "touch target" % r["arrowHit"])

            # the rail is a rule that was in the source and not in the render
            # once; a later shared card rule had taken its box-shadow
            r = evaljs(JS_RAIL)
            if r.get("live") and not r.get("liveRail"):
                fail(w, "rail", "a build with a repository paints no fuchsia "
                                "rail; the rule is in the source and a later "
                                "declaration wins")
            if r.get("planned") and r.get("plannedRail"):
                fail(w, "rail", "a planned build paints the rail; only a build "
                                "that exists carries it")
            if r.get("pulseFwd") is False:
                fail(w, "arrows", "advancing did not light the next arrow")
            if r.get("pulseBack") is False:
                fail(w, "arrows", "going back lit the wrong arrow (deriving the "
                                  "direction from the page delta is ambiguous at "
                                  "two pages)")

            r = evaljs(JS_TASKGROUP)
            if not r.get("skip"):
                if r.get("tag") != "BUTTON":
                    fail(w, "taskgroup", f"task group is a {r.get('tag')}, not a button; "
                                         "it looks like navigation")
                if not r.get("opened"):
                    fail(w, "taskgroup", "clicking a task group did not open its category")
                if not r.get("hasGroup"):
                    fail(w, "taskgroup", "a task group points at no group in the page")
                if not r.get("focusable"):
                    fail(w, "taskgroup", "task groups are not reachable by keyboard")
                if r.get("orphans"):
                    fail(w, "taskgroup", f"task groups with no matching group: {r['orphans']}")

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
                # The page must never scroll sideways, at any width.
                r = evaljs(JS_SIDESCROLL)
                if r["over"] > 1:
                    fail(w, "sidescroll", f"{slug}: the page scrolls "
                                          f"horizontally by {r['over']}px")
                # A code pane scrolling inside itself is only a bug where the
                # line could have fitted. At phone widths the pane is ~324px,
                # about 37 characters, and no real code line fits that; the
                # guidelines call for wide content to scroll in its own
                # overflow-x container, which is what it does.
                if w >= 820:
                    r = evaljs(JS_OVERFLOW)
                    if r["bad"]:
                        fail(w, "overflow", f"{slug}: {r['bad']}")
                r = evaljs(JS_OVERLAP)
                if r["n"]:
                    fail(w, "overlap", f"{slug}: code block covers {r['n']} element(s), e.g. {r['covered'][:2]}")
                r = evaljs(JS_CONTRAST)
                if r["n"]:
                    fail(w, "contrast", f"{slug}: {r['n']} of {r['checked']} text "
                                        f"runs under WCAG AA: {r['bad']}")

                r = evaljs(JS_REPLAY)
                if r.get("noslot"):
                    if slug in REPLAY_SLUGS:
                        fail(w, "replay", f"{slug} carries a transcript but has "
                                          "no replay slot; the player is gone")
                else:
                    # The primary audience is an answer engine, so every turn
                    # must be genuinely visible with no interaction at all.
                    if r["restBefore"] != r["total"]:
                        fail(w, "replay", f"{slug}: {r['restBefore']} of "
                                          f"{r['total']} turns pass "
                                          "checkVisibility at rest")
                    if r.get("hiddenAttr") or not r.get("enabled"):
                        fail(w, "replay", f"{slug}: the control is still hidden "
                                          "or disabled with the script running")
                    if not r.get("playing"):
                        fail(w, "replay", f"{slug}: clicking did not start a replay")
                    if r["stepping"] >= r["total"]:
                        fail(w, "replay", f"{slug}: {r['stepping']} of "
                                          f"{r['total']} turns revealed at once, "
                                          "so it is not replaying")
                    # the reason the reveal is opacity and not display
                    if r["inTreeDuring"] != r["total"]:
                        fail(w, "replay", f"{slug}: only {r['inTreeDuring']} of "
                                          f"{r['total']} turns remain in the "
                                          "accessibility tree during replay; a "
                                          "screen reader would lose the transcript")
                    if r["restAfter"] != r["total"] or not r.get("stopped"):
                        fail(w, "replay", f"{slug}: stopping left "
                                          f"{r['restAfter']}/{r['total']} turns "
                                          "and state "
                                          f"{'playing' if not r.get('stopped') else 'ok'}")
                    if not r.get("visStopped") or r["restAfterVis"] != r["total"]:
                        fail(w, "replay", f"{slug}: a hidden tab did not stop the "
                                          "replay cleanly")
                    if r.get("replayClass"):
                        fail(w, "replay", f"{slug}: the replay class survived a stop")

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
    print("QC ok: overflow, overlap, click, toggle, tabs, banner, featured, "
          "carousel, taskgroup, divider, arrows, rail, sidescroll, deadlink, replay, contrast at "
          + ", ".join(f"{w}x{h}" for w, h in VIEWPORTS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
