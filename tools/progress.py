#!/usr/bin/env python3
"""Render the progress board: every inventory row, built or not, one page.

Generated from docs/enum/inventory.json plus the state of recipes/ (folder
present? verify.py present?). Built recipes render in full; folders that are
not written yet are dimmed; planned rows dimmer still; holds are tagged. This is
the single place to show where the directory stands.

    python tools/progress.py [out.html]      # default: prints the path it wrote
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import vocab  # noqa: E402

V = vocab.load()
CATS = [(c["key"], c["label"]) for c in V["categories"]]
CAT_LABEL = dict(CATS)
TG = {"call-control": "Call control", "routing": "Routing & queueing", "observe": "Monitoring",
      "governance": "Governance", "knowledge": "Knowledge", "tools": "Tools & integrations",
      "handoff": "Handoff", "other": "Other"}
STATE = {  # inventory status -> (label, css state)
    "verified": ("Verified", "done"),
    "written": ("Written, not verified", "written"),
    "stub": ("Folder, not written", "stub"),
    "proposed": ("Planned", "planned"),
    "hold": ("On hold", "hold"),
}


def esc(s):
    return html.escape(str(s), quote=True)


ACRONYMS = {"pii", "sms", "mms", "otp", "pbx", "ivr", "sip", "dtmf", "mcp", "api", "rtmp", "e911",
            "10dlc", "crm", "sdk", "ani", "twiml", "url", "pstn", "webrtc", "pubsub", "yaml", "swml",
            "rest", "relay", "ai", "id"}


def title_for(slug):
    words = [w.upper() if w in ACRONYMS else w for w in slug.split("-")]
    words[0] = words[0] if words[0].isupper() else words[0].capitalize()
    return " ".join(words)


def backlog_names():
    """#n -> item name from the verbatim marketing backlog."""
    out = {}
    p = ROOT / "docs" / "MARKETING_BACKLOG.md"
    if p.exists():
        for m in re.finditer(r"^\| (\d+) \| ([^|]+?) \|", p.read_text(encoding="utf-8"), re.M):
            out[f"#{m.group(1)}"] = re.sub(r"^AI ", "", m.group(2).strip())
    return out


BACKLOG = None


def scenarios(folds):
    global BACKLOG
    if BACKLOG is None:
        BACKLOG = backlog_names()
    out = []
    for f in folds:
        m = re.match(r"(?:scenario )?(#\d+)", f)
        if m and m.group(1) in BACKLOG:
            out.append(BACKLOG[m.group(1)])
        elif f.startswith("scenario ") and not f.startswith("scenario t:"):
            out.append(re.sub(r"^scenario ", "", f).split(" (")[0].split(" - ")[0])
    stems = sum(1 for f in folds if f.startswith("t:"))
    return out[:3], max(0, len(out) - 3), stems


def load():
    rows = json.loads((ROOT / "docs" / "enum" / "inventory.json").read_text(encoding="utf-8"))["rows"]
    for r in rows:
        d = ROOT / "recipes" / r["slug"]
        r["_folder"] = d.is_dir()
        r["_verify"] = (d / "verify.py").exists()
        meta = {}
        if (d / "recipe.json").exists():
            meta = json.loads((d / "recipe.json").read_text(encoding="utf-8"))
        r["_title"] = meta.get("title") or title_for(r["slug"])
        r["_alias"] = meta.get("alias") or ""
        r["_cat"] = r["products"][0]
    return rows


def card(r):
    label, state = STATE[r["status"]]
    sc, more, stems = scenarios(r.get("folds", []))
    tags = "".join('<span class="tag">%s</span>' % esc(s) for s in sc)
    if more:
        tags += '<span class="tag">+%d</span>' % more
    if stems:
        tags += '<span class="tag dim">%d Telnyx stem%s</span>' % (stems, "" if stems == 1 else "s")
    alias = '<span class="alias">%s</span>' % esc(r["_alias"]) if r["_alias"] else ""
    launch = '<span class="launch">launch</span>' if r.get("launch") else ""
    return (
        '<article class="card s-%s" data-status="%s" data-launch="%s" data-cat="%s" data-kind="%s" data-hay="%s">'
        '<div class="ch"><span class="state"><i></i>%s</span>%s</div>'
        '<h4>%s</h4><code class="slug">%s</code>%s'
        '<p class="claim">%s</p>'
        '<div class="tags">%s</div></article>'
        % (state, state, "1" if r.get("launch") else "0", esc(r["_cat"]), esc(r["kind"]),
           esc(" ".join([r["slug"], r["_title"], r["claim"], " ".join(r.get("capabilities", []))]).lower()),
           esc(label), launch, esc(r["_title"]), esc(r["slug"]), alias, esc(r["claim"]), tags)
    )


def bar(done, total, label=None):
    pct = round(100 * done / total) if total else 0
    return ('<div class="bar" role="img" aria-label="%d of %d verified"><span style="width:%d%%"></span></div>'
            '<span class="barn">%d<span class="of">/%d</span>%s</span>'
            % (done, total, pct, done, total, (" " + esc(label)) if label else ""))


def main(out_path=None):
    rows = load()
    recipes = [r for r in rows if r["kind"] == "recipe"]
    builds = [r for r in rows if r["kind"] == "build"]
    guides = [r for r in rows if r["kind"] == "guide"]
    tools = [r for r in rows if r["kind"] == "tool"]
    holds = [r for r in rows if r["kind"] == "hold"]
    n_done = sum(1 for r in rows if r["status"] == "verified")
    launch = [r for r in rows if r.get("launch")]
    l_done = sum(1 for r in launch if r["status"] == "verified")
    folders = sum(1 for r in rows if r["_folder"])

    chips = ['<button class="chip" data-f="all" aria-pressed="true">All <span class="n">%d</span></button>' % len(rows),
             '<button class="chip" data-f="launch" aria-pressed="false">Launch set <span class="n">%d</span></button>' % len(launch),
             '<button class="chip" data-f="done" aria-pressed="false">Verified <span class="n">%d</span></button>' % n_done,
             '<button class="chip" data-f="todo" aria-pressed="false">Not written yet <span class="n">%d</span></button>' % (len(rows) - n_done)]
    chips.append('<span class="sep"></span>')
    for k, lab in CATS:
        n = sum(1 for r in recipes if r["_cat"] == k)
        if n:
            chips.append('<button class="chip" data-f="cat:%s" aria-pressed="false">%s <span class="n">%d</span></button>' % (k, esc(lab), n))
    chips.append('<button class="chip kind" data-f="kind:build" aria-pressed="false">Builds <span class="n">%d</span></button>' % len(builds))

    sections = []
    for k, lab in CATS:
        items = [r for r in recipes if r["_cat"] == k]
        if not items:
            continue
        d = sum(1 for r in items if r["status"] == "verified")
        groups = {}
        for r in items:
            groups.setdefault(r["task_group"], []).append(r)
        order = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        blocks = "".join(
            '<div class="tg"><h3>%s <span class="n">%d</span></h3><div class="grid">%s</div></div>'
            % (esc(TG.get(g, g)), len(v), "".join(card(r) for r in sorted(
                v, key=lambda r: (["verified", "written", "stub", "proposed", "hold"].index(r["status"]), not r.get("launch"), r["slug"]))))
            for g, v in order)
        sections.append(
            '<section class="cat" data-cat="%s"><header class="cath"><h2>%s</h2>%s</header>%s</section>'
            % (esc(k), esc(lab), bar(d, len(items), "verified"), blocks))

    def flat(title, items, note):
        if not items:
            return ""
        return ('<section class="cat flat"><header class="cath"><h2>%s</h2><p class="note">%s</p></header>'
                '<div class="grid">%s</div></section>' % (esc(title), esc(note), "".join(card(r) for r in items)))

    sections.append(flat("Builds", builds, "Applications you run; each composes recipes. A build with no repository is a stub."))
    sections.append(flat("Guides", guides, "Operational workflows with nothing new to run - porting, verification forms, ticket-gated identity."))
    sections.append(flat("Tools", tools, "Benchmarks and harnesses, published with their method."))
    sections.append(flat("On hold", holds, "The mechanism exists; a named blocker must clear before a public sample."))

    body = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SignalWire Recipes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@500;600&family=Lexend:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root{{color-scheme:dark;--page:#0f0f12;--surface:#16161a;--raised:#1c1c21;--fg:#f4f4f6;--fg-2:#c9c9d0;
  --fg-muted:#8b8b96;--fg-subtle:#63636e;--line:rgba(255,255,255,.08);--line-2:rgba(255,255,255,.14);
  --fuchsia:#F72A72;--turquoise:#40E0D0;--head:'Instrument Sans',ui-sans-serif,system-ui,sans-serif;
  --body:Lexend,ui-sans-serif,system-ui,sans-serif;--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,monospace;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--page);color:var(--fg);font-family:var(--body);font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}}
a{{color:var(--turquoise);text-decoration:none}}
code{{font-family:var(--mono);font-feature-settings:'tnum','zero'}}
h1,h2,h3,h4{{font-family:var(--head);font-weight:600;letter-spacing:-.03em;line-height:1.15;margin:0;text-wrap:balance}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 28px 96px}}
.top{{padding:44px 0 18px;display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:1px solid var(--line)}}
.top h1{{font-size:clamp(28px,3.6vw,40px);letter-spacing:-.04em}}
.top p{{margin:10px 0 0;color:var(--fg-muted);max-width:62ch}}
.kpis{{display:flex;gap:28px;font-family:var(--mono);font-size:12px;color:var(--fg-muted);font-feature-settings:'tnum','zero'}}
.kpi b{{display:block;font-family:var(--head);font-size:26px;color:var(--fg);letter-spacing:-.03em;line-height:1}}
.kpi .sub{{display:block;margin-top:6px}}
.overall{{display:flex;align-items:center;gap:14px;padding:14px 0 0}}
.bar{{flex:1;height:6px;background:var(--raised);border-radius:3px;overflow:hidden}}
.bar span{{display:block;height:100%;background:var(--turquoise)}}
.barn{{font-family:var(--mono);font-size:12px;color:var(--fg-2);white-space:nowrap;font-feature-settings:'tnum','zero'}}
.barn .of{{color:var(--fg-subtle)}}
.controls{{position:sticky;top:0;z-index:5;background:var(--page);border-bottom:1px solid var(--line);padding:12px 0;display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
#q{{flex:1 1 14rem;min-width:10rem;background:var(--surface);color:var(--fg);border:1px solid var(--line-2);border-radius:4px;padding:7px 11px;font-family:var(--mono);font-size:12px}}
#q:focus-visible{{outline:none;border-color:var(--fg-muted)}}
.chip{{font-family:var(--body);font-size:12.5px;padding:6px 12px;border-radius:4px;border:1px solid transparent;background:transparent;color:var(--fg-muted);cursor:pointer}}
.chip:hover{{color:var(--fg)}}
.chip[aria-pressed="true"]{{color:var(--fg);background:var(--raised);border-color:var(--line-2)}}
.chip.kind[aria-pressed="true"]{{border-color:var(--fuchsia);color:var(--fg)}}
.chip .n,.cath .n,h3 .n{{font-family:var(--mono);font-size:11px;color:var(--fg-subtle);margin-left:2px}}
.chip:focus-visible{{outline:2px solid var(--fg-muted);outline-offset:2px}}
.sep{{width:1px;height:18px;background:var(--line-2);margin:0 6px}}
.cat{{padding:34px 0 0}}
.cath{{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:8px}}
.cath h2{{font-size:24px;flex:0 0 auto}}
.cath .bar{{max-width:260px}}
.cath .note{{margin:0;color:var(--fg-muted);font-size:13px;flex:1 1 30ch}}
.tg{{padding:14px 0 0}}
.tg h3{{font-size:14px;color:var(--fg-2);margin:0 0 10px}}
.grid{{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:8px;overflow:hidden;grid-template-columns:repeat(auto-fill,minmax(262px,1fr))}}
.card{{background:var(--page);padding:14px 16px 15px;display:flex;flex-direction:column;gap:6px;min-width:0}}
.card .ch{{display:flex;align-items:center;justify-content:space-between;gap:8px}}
.state{{font-size:11px;color:var(--fg-muted);display:inline-flex;align-items:center;gap:7px}}
.state i{{width:7px;height:7px;border-radius:999px;background:var(--fg-subtle);flex:none}}
.s-done .state i{{background:var(--turquoise)}}
.s-done .state{{color:var(--fg-2)}}
.s-hold .state i{{background:transparent;border:1.5px solid var(--fg-muted)}}
.launch{{font-family:var(--mono);font-size:10px;color:var(--fg-muted);border:1px solid var(--line-2);border-radius:3px;padding:1px 6px;letter-spacing:.02em}}
.card h4{{font-size:14.5px;letter-spacing:-.015em}}
.slug{{font-size:10.5px;color:var(--turquoise);overflow-wrap:anywhere}}
.alias{{font-family:var(--mono);font-size:10.5px;color:var(--fg-subtle);display:block}}
.claim{{margin:2px 0 0;font-size:12.5px;color:var(--fg-muted);line-height:1.5;flex:1}}
.tags{{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}}
.tag{{font-size:10.5px;color:var(--fg-muted);background:var(--raised);border-radius:3px;padding:1px 7px}}
.tag.dim{{color:var(--fg-subtle);background:transparent;border:1px solid var(--line)}}
.s-stub,.s-written{{background:var(--surface)}}
.s-stub h4,.s-written h4{{color:var(--fg-2)}}
.s-planned{{background:var(--surface)}}
.s-planned h4{{color:var(--fg-muted)}}
.s-planned .slug{{color:var(--fg-subtle)}}
.s-planned .claim,.s-stub .claim{{color:var(--fg-subtle)}}
.s-hold{{background:var(--surface)}}
.s-hold h4{{color:var(--fg-muted)}}
.card[hidden],.cat[hidden],.tg[hidden]{{display:none}}
.empty{{padding:40px 0;color:var(--fg-muted);text-align:center}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;padding:12px 0 0;font-size:12px;color:var(--fg-muted)}}
.legend span{{display:inline-flex;align-items:center;gap:7px}}
.legend i{{width:7px;height:7px;border-radius:999px;background:var(--fg-subtle)}}
.legend .d i{{background:var(--turquoise)}}
.legend .h i{{background:transparent;border:1.5px solid var(--fg-muted)}}
.foot{{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--fg-subtle)}}
@media (max-width:720px){{.top{{grid-template-columns:1fr}}.kpis{{gap:18px}}}}
</style>
<div class="wrap">
<header class="top">
  <div><h1>SignalWire Recipes</h1>
  <p>Every recipe the directory will carry, one card each. Built ones are shown in full; folders that exist but are not written yet are dimmed; planned ones dimmer still. Generated from the same inventory the site is built from.</p></div>
  <div class="kpis">
    <div class="kpi"><b>{n_done}</b><span class="sub">verified</span></div>
    <div class="kpi"><b>{folders}</b><span class="sub">folders</span></div>
    <div class="kpi"><b>{len(rows)}</b><span class="sub">planned in all</span></div>
  </div>
</header>
<div class="overall">{bar(n_done, len(rows), "verified overall")}</div>
<div class="overall" style="padding-top:8px">{bar(l_done, len(launch), "of the launch set")}</div>
<div class="legend"><span class="d"><i></i>Verified: runs, and proves its claim offline</span><span><i></i>Folder, not written</span><span><i></i>Planned, no folder yet</span><span class="h"><i></i>On hold</span></div>
<div class="controls"><input id="q" type="search" placeholder="filter by name, claim or capability" aria-label="Filter">{"".join(chips)}</div>
{"".join(sections)}
<p class="empty" id="none" hidden>Nothing matches.</p>
<p class="foot">Verified means <code>python verify.py &lt;slug&gt;</code> passes: the recipe is constructed and its mechanism is asserted in the artifact the platform receives (SWML validated against the SDK schema, REST requests checked against the OpenAPI specs, webhooks driven with documented payloads). Scenario tags are the marketing backlog items and Telnyx stems each mechanism absorbs.</p>
</div>
<script>
(function(){{
  var f='all', q='';
  var cards=[].slice.call(document.querySelectorAll('.card'));
  function show(c){{
    if(q && c.dataset.hay.indexOf(q)<0) return false;
    if(f==='all') return true;
    if(f==='launch') return c.dataset.launch==='1';
    if(f==='done') return c.dataset.status==='done';
    if(f==='todo') return c.dataset.status!=='done';
    if(f.indexOf('cat:')===0) return c.dataset.cat===f.slice(4) && c.dataset.kind==='recipe';
    if(f.indexOf('kind:')===0) return c.dataset.kind===f.slice(5);
    return true;
  }}
  function apply(){{
    var any=false;
    cards.forEach(function(c){{var s=show(c); c.hidden=!s; any=any||s;}});
    document.querySelectorAll('.tg').forEach(function(g){{g.hidden=!g.querySelector('.card:not([hidden])');}});
    document.querySelectorAll('.cat').forEach(function(s){{s.hidden=!s.querySelector('.card:not([hidden])');}});
    document.getElementById('none').hidden=any;
  }}
  document.querySelectorAll('.chip').forEach(function(b){{
    b.addEventListener('click',function(){{
      f=b.dataset.f;
      document.querySelectorAll('.chip').forEach(function(x){{x.setAttribute('aria-pressed',x===b?'true':'false');}});
      apply();
    }});
  }});
  document.getElementById('q').addEventListener('input',function(e){{q=e.target.value.trim().toLowerCase();apply();}});
}})();
</script>
"""
    out = pathlib.Path(out_path) if out_path else ROOT / "site" / "progress.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out} ({len(rows)} rows, {n_done} verified, launch {l_done}/{len(launch)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
