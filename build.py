#!/usr/bin/env python3
"""Static generator: recipes/*/recipe.json  ->  site/

Adding a recipe means adding a folder. Nothing here is hand-maintained.
Emits: site/index.html, site/r/<slug>.html, site/r/<slug>.md,
       site/llms.txt, site/sitemap.xml
"""
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).parent
RECIPES = ROOT / "recipes"
SITE = ROOT / "site"
BASE = "https://signalwire.com/recipes"

import vocab

# The generator holds NO domain vocabulary. Categories, surfaces and evidence
# types are discovered from vocab/ at build time. Adding one is adding a file
# there — this module must never learn their names. check_extensible.py enforces
# that; if you find yourself wanting a literal here, add a vocab field instead.
V = vocab.load()
CATEGORIES = [(c["key"], c["label"]) for c in V["categories"]]
CAT_LABEL = V["category_label"]
SURFACE_ABBR = V["surface_abbr"]

TIER_ORDER = {"launch": 0, "next": 1, "later": 2}

CSS = """
:root{
  --ground:#F5F7F9; --surface:#FFFFFF; --surface-2:#EAEEF2; --surface-3:#E1E7ED;
  --ink:#121821; --ink-2:#37414E; --muted:#5B6573; --faint:#8A94A1;
  --rule:#D4DAE2; --rule-soft:#E5EAEF;
  --accent:#0B5FBF; --accent-soft:#E2ECF9;
  --gov:#7A3E9D; --gov-soft:#F0E7F7;
  --launch:#12664A; --launch-soft:#DFEFE8;
  --next:#8A5A10; --next-soft:#F5EEDC;
  --later:#5B6573; --later-soft:#E8EBEF;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Consolas,monospace;
  --sans:Archivo,"Helvetica Neue",Arial,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0C1219; --surface:#141C25; --surface-2:#1C2531; --surface-3:#243040;
    --ink:#E6EBF1; --ink-2:#C0C9D5; --muted:#8F9BA9; --faint:#6A7684;
    --rule:#293441; --rule-soft:#202935;
    --accent:#5AA3EE; --accent-soft:#16263A;
    --gov:#C4A0E4; --gov-soft:#241A31;
    --launch:#5CC69C; --launch-soft:#12281E;
    --next:#DCAB5A; --next-soft:#292011;
    --later:#8F9BA9; --later-soft:#252E3A;
  }
}
:root[data-theme="dark"]{
  --ground:#0C1219; --surface:#141C25; --surface-2:#1C2531; --surface-3:#243040;
  --ink:#E6EBF1; --ink-2:#C0C9D5; --muted:#8F9BA9; --faint:#6A7684;
  --rule:#293441; --rule-soft:#202935;
  --accent:#5AA3EE; --accent-soft:#16263A;
  --gov:#C4A0E4; --gov-soft:#241A31;
  --launch:#5CC69C; --launch-soft:#12281E;
  --next:#DCAB5A; --next-soft:#292011;
  --later:#8F9BA9; --later-soft:#252E3A;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;}
.wrap{max-width:74rem;margin:0 auto;padding:0 clamp(1rem,4vw,2.5rem) 5rem;}
a{color:inherit;text-decoration:none;}
code,.mono{font-family:var(--mono);}

header.top{padding:clamp(2rem,6vw,3.5rem) 0 1.25rem;}
.kicker{font-family:var(--mono);font-size:.6875rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);}
h1{font-size:clamp(1.75rem,4.5vw,2.5rem);font-weight:700;letter-spacing:-.022em;
  margin:.6rem 0 0;line-height:1.05;}
.sub{color:var(--ink-2);margin:.7rem 0 0;max-width:none;font-size:1rem;}
.counts{display:flex;flex-wrap:wrap;gap:.4rem .5rem;margin-top:1.25rem;}

.controls{position:sticky;top:0;z-index:5;background:var(--ground);
  padding:.85rem 0 .7rem;border-bottom:1px solid var(--rule);
  display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;}
#q{flex:1 1 15rem;min-width:11rem;background:var(--surface);color:var(--ink);
  border:1px solid var(--rule);border-radius:3px;padding:.42rem .6rem;
  font-family:var(--mono);font-size:.8125rem;}
#q:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent);}
.chip{font-family:var(--mono);font-size:.7rem;letter-spacing:.03em;padding:.34rem .55rem;
  border:1px solid var(--rule);border-radius:3px;background:var(--surface);
  color:var(--muted);cursor:pointer;}
.chip[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent);}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}

.grouphead{font-family:var(--mono);font-size:.6875rem;letter-spacing:.11em;
  text-transform:uppercase;color:var(--faint);padding:1.6rem 0 .5rem;}
.rows{display:flex;flex-direction:column;gap:1px;background:var(--rule-soft);
  border:1px solid var(--rule);border-radius:3px;overflow:hidden;}
.row{display:grid;grid-template-columns:1fr auto;gap:.5rem 1rem;align-items:start;
  background:var(--surface);padding:.7rem .85rem;cursor:pointer;border-left:2px solid transparent;}
.row:hover{background:var(--surface-2);}
.row.sel{border-left-color:var(--accent);background:var(--surface-2);}
.row .name{font-weight:600;font-size:.9375rem;letter-spacing:-.005em;}
.row .slug{font-family:var(--mono);font-size:.72rem;color:var(--muted);margin-top:.15rem;}
.row .sum{color:var(--ink-2);font-size:.84rem;margin-top:.3rem;max-width:70ch;}
.row .right{display:flex;flex-wrap:wrap;gap:.3rem;justify-content:flex-end;align-items:center;}
.b{font-family:var(--mono);font-size:.62rem;letter-spacing:.05em;text-transform:uppercase;
  padding:.18rem .36rem;border-radius:2px;white-space:nowrap;
  background:var(--surface-3);color:var(--muted);}
.b.gov{background:var(--gov-soft);color:var(--gov);}
.b.launch{background:var(--launch-soft);color:var(--launch);}
.b.next{background:var(--next-soft);color:var(--next);}
.b.later{background:var(--later-soft);color:var(--later);}
.surf{font-family:var(--mono);font-size:.68rem;color:var(--faint);white-space:nowrap;}
.empty{padding:2rem .85rem;color:var(--muted);background:var(--surface);font-size:.9rem;}
.hint{margin-top:1.1rem;font-family:var(--mono);font-size:.7rem;color:var(--faint);}
kbd{font-family:var(--mono);background:var(--surface-2);border:1px solid var(--rule);
  border-radius:2px;padding:.05rem .25rem;font-size:.95em;}

.detail{padding:clamp(2rem,6vw,3rem) 0 0;max-width:52rem;margin-inline:auto;}
.detail .sub,.detail .claim p,.detail .sec p{max-width:none;}
.back{font-family:var(--mono);font-size:.72rem;color:var(--muted);}
.detail h1{font-size:clamp(1.5rem,4vw,2.1rem);}
.alias{font-family:var(--mono);font-size:.8rem;color:var(--accent);margin-top:.5rem;}
.meta{display:flex;flex-wrap:wrap;gap:.35rem;margin:1.1rem 0 0;}
.panel{background:var(--surface);border:1px solid var(--rule);border-radius:3px;
  padding:1.1rem 1.2rem;margin:1.4rem 0;}
.panel h2{font-size:.98rem;font-weight:600;margin:0 0 .5rem;}
.panel p{margin:0;color:var(--ink-2);font-size:.9rem;}
.demoslot{background:var(--accent-soft);border:1px dashed var(--accent);border-radius:3px;
  padding:1.4rem 1.2rem;margin:1.4rem 0;text-align:center;}
.demoslot .lab{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--accent);}
.demoslot p{margin:.5rem 0 0;color:var(--ink-2);font-size:.88rem;}
.tabs{display:flex;gap:.3rem;margin:1.4rem 0 0;flex-wrap:wrap;}
.tab{font-family:var(--mono);font-size:.72rem;padding:.35rem .6rem;border:1px solid var(--rule);
  border-bottom:none;border-radius:3px 3px 0 0;background:var(--surface-2);color:var(--muted);}
.tab.on{background:var(--surface);color:var(--accent);border-color:var(--rule);}
.codebox{background:var(--surface);border:1px solid var(--rule);border-radius:0 3px 3px 3px;
  padding:1rem;font-family:var(--mono);font-size:.78rem;color:var(--muted);overflow-x:auto;}

/* --- recipe page --- */
.dh{padding:0 0 .2rem;}
.dh h1{font-size:clamp(1.5rem,4vw,2.15rem);}
.tech{font-family:var(--mono);font-size:.8rem;color:var(--accent);margin-top:.4rem;}
.claim{background:var(--accent-soft);border-left:3px solid var(--accent);
  padding:.9rem 1.1rem;margin:1.5rem 0;border-radius:0 3px 3px 0;}
.claim h2{font-family:var(--mono);font-size:.66rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--accent);margin:0 0 .35rem;}
.claim p{margin:0;color:var(--ink-2);font-size:.95rem;max-width:64ch;}
.ev{border:1px solid var(--rule);border-radius:3px;overflow:hidden;margin:1.5rem 0;}
.ev-h{display:flex;align-items:center;gap:.5rem;padding:.55rem .85rem;
  background:var(--surface-2);border-bottom:1px solid var(--rule-soft);
  font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);}
.ev-h .dot{width:.45rem;height:.45rem;border-radius:50%;background:var(--launch);flex:none;}
.ev-b{padding:1rem .9rem;background:var(--surface);}
.ev cite{display:block;margin-top:.7rem;font-style:normal;font-size:.78rem;color:var(--faint);}
.tr{font-family:var(--mono);font-size:.755rem;line-height:1.7;}
.tr .l{display:grid;grid-template-columns:3.9rem 1fr;gap:.65rem;}
.tr .w{color:var(--faint);text-align:right;}
.tr .w.ai{color:var(--accent);}
.tr .sys{background:var(--next-soft);color:var(--next);padding:.32rem .5rem;
  border-radius:2px;margin:.4rem 0;display:block;font-size:.71rem;}
.acts{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin-top:.9rem;}
.btn{font-family:var(--sans);font-weight:600;font-size:.85rem;background:var(--ink);
  color:var(--ground);padding:.5rem 1rem;border-radius:4px;border:none;cursor:pointer;}
.btn:hover{opacity:.88;}
.btn:active{transform:scale(.985);}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.acts .n{font-size:.76rem;color:var(--muted);flex:1 1 16rem;line-height:1.45;}
.sec{margin:1.6rem 0;}
.sec h2{font-size:1rem;font-weight:600;margin:0 0 .45rem;}
.sec p{margin:0 0 .7rem;color:var(--ink-2);font-size:.95rem;max-width:66ch;}
.sec p em{font-style:italic;color:var(--ink);}
.steps{font-family:var(--mono);font-size:.755rem;color:var(--ink-2);
  background:var(--surface-2);border:1px solid var(--rule-soft);border-radius:3px;
  padding:.75rem .9rem;line-height:1.85;overflow-x:auto;}
.cw{margin:1.6rem 0;}
.stabs{display:flex;gap:.22rem;}
.stab{font-family:var(--mono);font-size:.7rem;padding:.34rem .62rem;
  border:1px solid var(--rule);border-bottom:none;border-radius:3px 3px 0 0;
  background:var(--surface-2);color:var(--muted);}
.stab[aria-selected="true"]{background:#0F1720;color:#fff;border-color:#0F1720;}
pre.src{margin:0;background:#0F1720;color:#D9E1EA;padding:.95rem;
  border-radius:0 3px 3px 3px;font-family:var(--mono);font-size:.755rem;
  line-height:1.65;overflow-x:auto;}
.dfoot{border-top:1px solid var(--rule);margin-top:2rem;padding-top:1rem;
  display:flex;gap:1.1rem;flex-wrap:wrap;font-family:var(--mono);font-size:.73rem;}
.dfoot a{color:var(--accent);}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
"""

JS = """
const rows=[...document.querySelectorAll('.row')];
const q=document.getElementById('q');
const chips=[...document.querySelectorAll('.chip')];
let sel=-1;
function active(){return rows.filter(r=>r.style.display!=='none');}
function apply(){
  const t=q.value.trim().toLowerCase();
  const on=chips.filter(c=>c.getAttribute('aria-pressed')==='true').map(c=>c.dataset.f);
  rows.forEach(r=>{
    const hay=r.dataset.hay;
    const okT=!t||hay.includes(t);
    const okF=!on.length||on.every(f=>r.dataset.facets.split(' ').includes(f));
    r.style.display=(okT&&okF)?'':'none';
  });
  document.querySelectorAll('.grp').forEach(g=>{
    const any=[...g.querySelectorAll('.row')].some(r=>r.style.display!=='none');
    g.style.display=any?'':'none';
  });
  const n=active().length;
  document.getElementById('shown').textContent=n+' shown';
  document.getElementById('none').style.display=n?'none':'';
  sel=-1;rows.forEach(r=>r.classList.remove('sel'));
}
q.addEventListener('input',apply);
chips.forEach(c=>c.addEventListener('click',()=>{
  c.setAttribute('aria-pressed',c.getAttribute('aria-pressed')==='true'?'false':'true');apply();
}));
rows.forEach(r=>r.addEventListener('click',()=>{location.href=r.dataset.href;}));
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus();return;}
  if(e.key==='Escape'&&document.activeElement===q){q.value='';apply();q.blur();return;}
  const a=active();if(!a.length)return;
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){
    e.preventDefault();
    rows.forEach(r=>r.classList.remove('sel'));
    const cur=a.findIndex(r=>r===rows[sel]);
    let i=cur+(e.key==='ArrowDown'?1:-1);
    if(i<0)i=0;if(i>=a.length)i=a.length-1;
    sel=rows.indexOf(a[i]);a[i].classList.add('sel');
    a[i].scrollIntoView({block:'nearest'});
  }
  if(e.key==='Enter'&&sel>=0){location.href=rows[sel].dataset.href;}
});
apply();
"""


def esc(s):
    return html.escape(str(s), quote=True)


def load():
    out = []
    errors = []
    for m in sorted(RECIPES.glob("*/recipe.json")):
        r = json.loads(m.read_text(encoding="utf-8"))
        if m.parent.name != r.get("slug"):
            print(f"  ! slug/dirname mismatch: {m.parent.name} vs {r.get('slug')}")
        for e in vocab.validate_recipe(r, V, where=m.parent.name):
            print(f"  ! {e}")
            errors.append(e)
        r["_surfaces_on_disk"] = sorted(
            p.name for p in m.parent.iterdir() if p.is_dir()
        )
        out.append(r)
    if errors:
        raise SystemExit(
            f"{len(errors)} vocabulary error(s) - build refused. "
            "Unknown values are errors, never silently skipped."
        )
    return out


def page(title, body, favicon_title=None):
    return (
        "<title>" + esc(title) + "</title>\n"
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        "family=Archivo:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&"
        'display=swap">\n'
        "<style>" + CSS + "</style>\n" + body
    )


def badges(r):
    """Public metadata only. Tier and provenance are internal planning state."""
    out = []
    if r.get("governed"):
        out.append('<span class="b gov">governed</span>')
    if r.get("difficulty"):
        out.append('<span class="b">%s</span>' % esc(r["difficulty"]))
    return "".join(out)


def written_surfaces(r):
    """Only surfaces with code actually on disk. Never advertise an empty one."""
    d = RECIPES / r["slug"]
    return [
        x for x in r.get("surfaces", [])
        if isinstance(x, str) and read_code(d, x, V)
    ]



def build_index(recipes, body_only=False):
    n = len(recipes)
    launch = sum(1 for r in recipes if r.get("tier") == "launch")
    gov = sum(1 for r in recipes if r.get("governed"))

    chips = []
    for key, label in CATEGORIES:
        if any(r.get("category") == key for r in recipes):
            chips.append(
                f'<button class="chip" data-f="cat:{key}" aria-pressed="false">{esc(label)}</button>'
            )
    chips.append(
        '<button class="chip" data-f="gov" aria-pressed="false">governed</button>'
    )

    groups = []
    for key, label in CATEGORIES:
        items = [r for r in recipes if r.get("category") == key]
        if not items:
            continue
        items.sort(key=lambda r: (TIER_ORDER.get(r.get("tier"), 9), r["slug"]))
        rows = []
        for r in items:
            facets = [f"cat:{r.get('category')}"]
            if r.get("tier") == "launch":
                facets.append("launch")
            if r.get("governed"):
                facets.append("gov")
            hay = " ".join(
                [
                    r["slug"],
                    r["title"],
                    r.get("alias", ""),
                    r.get("summary", ""),
                    r.get("scenario", ""),
                    " ".join(r.get("capabilities", [])),
                    " ".join(r.get("surfaces", [])),
                ]
            ).lower()
            surf = " ".join(
                SURFACE_ABBR.get(s, s) for s in written_surfaces(r)
            )
            rows.append(
                f'<div class="row" tabindex="-1" data-href="r/{esc(r["slug"])}.html" '
                f'data-hay="{esc(hay)}" data-facets="{esc(" ".join(facets))}">'
                f'<div><div class="name">{esc(r["title"])}</div>'
                f'<div class="slug">{esc(r["slug"])}'
                + (
                    f' &middot; <span style="color:var(--accent)">{esc(r["alias"])}</span>'
                    if r.get("alias")
                    else ""
                )
                + "</div>"
                f'<div class="sum">{esc(r.get("summary",""))}</div></div>'
                f'<div class="right">{badges(r)}<span class="surf">{esc(surf)}</span></div>'
                "</div>"
            )
        groups.append(
            f'<div class="grp"><div class="grouphead">{esc(label)} '
            f"&mdash; {len(items)}</div>"
            f'<div class="rows">{"".join(rows)}</div></div>'
        )

    body = f"""<div class="wrap">
<header class="top">
  <div class="kicker">SignalWire &middot; recipes</div>
  <h1>Recipes</h1>
  <p class="sub">Every recipe is one folder in one repository. This page is generated from
  those folders &mdash; adding a recipe adds a row here, with no edit to this page.</p>
  <div class="counts">
    <span class="b">{n} recipes</span>
    <span class="b gov">{gov} governed</span>
    <span class="b" id="shown">{n} shown</span>
  </div>
</header>
<div class="controls">
  <input id="q" type="search" placeholder="filter&hellip;  (press / )" aria-label="Filter recipes">
  {''.join(chips)}
</div>
{''.join(groups)}
<div class="empty" id="none" style="display:none">Nothing matches that filter.</div>
<p class="hint"><kbd>/</kbd> search &middot; <kbd>&uarr;</kbd><kbd>&darr;</kbd> move &middot;
<kbd>Enter</kbd> open &middot; <kbd>Esc</kbd> clear</p>
</div>
<script>{JS}</script>"""
    return body if body_only else page("SignalWire Recipes", body)



def md_inline(t):
    t = esc(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)
    return t


def read_sections(d):
    """README "## Heading" blocks -> {heading: [paragraph, ...]}."""
    f = d / "README.md"
    if not f.exists():
        return {}
    out, cur, buf = {}, None, []

    def flush():
        if cur is None:
            return
        paras = [x.strip() for x in "\n".join(buf).split("\n\n")]
        out[cur] = [md_inline(" ".join(x.split())) for x in paras if x.strip()]

    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            flush()
            cur, buf = line[3:].strip(), []
        elif cur is not None:
            buf.append(line)
    flush()
    return out


def read_code(d, surface, V):
    entry = V["surfaces"].get(surface, {}).get("entry")
    if not entry:
        return None
    f = d / surface / entry
    if not f.exists() or not f.stat().st_size:
        return None
    return f.read_text(encoding="utf-8")


def read_evidence(d, V):
    """Any vocab/evidence type whose file_key exists on disk gets rendered."""
    for key, spec in V["evidence"].items():
        fk = spec.get("file_key", key)
        for cand in (d / (fk + ".json"), d / (fk + ".sample.json")):
            if cand.exists():
                data = json.loads(cand.read_text(encoding="utf-8"))
                return spec, data, V["renderers"][spec["renderer"]](data)
    return None, None, None


def build_detail(r, body_only=False):
    d = RECIPES / r["slug"]
    sections = read_sections(d)
    surfaces = written_surfaces(r) or [
        x for x in r.get("surfaces", []) if isinstance(x, str)
    ]
    spec, edata, ehtml = read_evidence(d, V)
    modeinfo = V["demo_modes"].get(r.get("demo", "none"), {})

    demo_paras = sections.get("What this demonstrates", [])
    claim = demo_paras[0] if demo_paras else esc(r.get("summary", ""))

    out = [
        '<div class="wrap"><div class="detail">',
        '<p class="back"><a href="../index.html">&larr; all recipes</a></p>',
        '<div class="kicker">%s</div>' % esc(CAT_LABEL.get(r.get("category"), "")),
        '<div class="dh"><h1>%s</h1>' % esc(r["title"]),
    ]
    if r.get("alias"):
        out.append('<div class="tech">%s</div>' % esc(r["alias"]))
    out.append('<p class="sub">%s</p>' % esc(r.get("summary", "")))
    # public metadata only - tier and provenance are internal planning state
    meta = ""
    if r.get("governed"):
        meta += '<span class="b gov">governed</span>'
    if r.get("difficulty"):
        meta += '<span class="b">%s</span>' % esc(r["difficulty"])
    meta += "".join(
        '<span class="b">%s</span>' % esc(x) for x in r.get("products", [])
    )
    out.append('<div class="meta">%s</div></div>' % meta)
    out.append('<div class="claim"><h2>The claim</h2><p>%s</p></div>' % claim)

    if ehtml:
        out.append(
            '<div class="ev"><div class="ev-h"><span class="dot"></span>'
            "evidence &middot; %s</div><div class=\"ev-b\">%s" % (esc(spec["label"]), ehtml)
        )
        if edata.get("caption"):
            out.append("<cite>%s</cite>" % esc(edata["caption"]))
        if modeinfo.get("interactive"):
            out.append(
                '<div class="acts"><button class="btn">%s</button>'
                '<span class="n">%s Runtime not built yet.</span></div>'
                % (esc(modeinfo["label"]), esc(modeinfo.get("copy", "")))
            )
        out.append("</div></div>")

    if len(demo_paras) > 1:
        out.append(
            '<div class="sec"><h2>Why it holds</h2>%s</div>'
            % "".join("<p>%s</p>" % x for x in demo_paras[1:])
        )

    for h in ("How it works", "Limitations"):
        if h in sections:
            out.append(
                '<div class="sec"><h2>%s</h2>%s</div>'
                % (esc(h), "".join("<p>%s</p>" % x for x in sections[h]))
            )

    if surfaces:
        tabs = "".join(
            '<span class="stab" aria-selected="%s">%s</span>'
            % ("true" if i == 0 else "false", esc(V["surfaces"][x]["label"]))
            for i, x in enumerate(surfaces)
            if x in V["surfaces"]
        )
        code = read_code(d, surfaces[0], V)
        if code:
            body = esc(code)
        else:
            body = esc(
                "# not written yet - recipes/%s/%s/%s"
                % (r["slug"], surfaces[0],
                   V["surfaces"].get(surfaces[0], {}).get("entry", "?"))
            )
        out.append(
            '<div class="cw"><div class="stabs">%s</div><pre class="src">%s</pre></div>'
            % (tabs, body)
        )

        sv = V["surfaces"].get(surfaces[0], {})
        run = ["git clone &hellip; &amp;&amp; cd %s/%s" % (esc(r["slug"]), esc(surfaces[0])),
               "cp .env.example .env"]
        if sv.get("install"):
            run.append(esc(sv["install"]))
        if sv.get("run"):
            run.append(esc(sv["run"]))
        out.append(
            '<div class="sec"><h2>Run it</h2><div class="steps">%s</div></div>'
            % "<br>".join(run)
        )

    if "What to change first" in sections:
        out.append(
            '<div class="sec"><h2>What to change first</h2>%s</div>'
            % "".join("<p>%s</p>" % x for x in sections["What to change first"])
        )

    out.append(
        '<div class="dfoot"><a href="#">View folder on GitHub</a>'
        '<a href="#">Report an issue</a></div></div></div>'
    )
    body = "".join(out)
    return body if body_only else page(
        r["title"] + " - SignalWire Recipes", body
    )



def build_md(r):
    lines = [
        f"# {r['title']}",
        "",
        f"> {r.get('summary','')}",
        "",
        f"- **Technical:** `{r.get('alias','')}`",
        f"- **Scenario:** {r.get('scenario','')}",
        f"- **Category:** {CAT_LABEL.get(r.get('category'), r.get('category',''))}",
        f"- **Products:** {', '.join(r.get('products', []))}",
        f"- **Capabilities:** {', '.join(r.get('capabilities', []))}",
        f"- **Surfaces:** {', '.join(r.get('surfaces', []))}",
        f"- **Governed:** {'yes' if r.get('governed') else 'no'}",
        f"- **Tier:** {r.get('tier','')}",
        f"- **Provenance:** {r.get('provenance','')}",
        "",
        f"Canonical: {BASE}/{r['slug']}",
        "",
    ]
    return "\n".join(lines)


def build_llms(recipes):
    out = [
        "# SignalWire Recipes",
        "",
        "> Deployable recipes for SignalWire: voice, messaging, chat and AI agents.",
        "> Each entry is a self-contained folder you can clone and run. Governed",
        "> recipes demonstrate enforcement in code rather than in a prompt.",
        "",
    ]
    for key, label in CATEGORIES:
        items = [r for r in recipes if r.get("category") == key]
        if not items:
            continue
        items.sort(key=lambda r: r["slug"])
        out.append(f"## {label}")
        out.append("")
        for r in items:
            out.append(
                f"- [{r['title']}]({BASE}/{r['slug']}.md): {r.get('summary','')}"
            )
        out.append("")
    return "\n".join(out)


def build_sitemap(recipes):
    urls = "".join(
        f"<url><loc>{BASE}/{r['slug']}</loc></url>" for r in sorted(recipes, key=lambda r: r["slug"])
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{BASE}</loc></url>{urls}</urlset>\n"
    )



def has_content(r):
    """A recipe is showable when someone has actually written it."""
    d = RECIPES / r["slug"]
    readme = d / "README.md"
    if not readme.exists() or "_TODO" in readme.read_text(encoding="utf-8"):
        return False
    if not read_sections(d).get("What this demonstrates"):
        return False
    for surface in r.get("surfaces", []):
        if isinstance(surface, str) and read_code(d, surface, V):
            return True
    return False


PREVIEW_JS = """
var views = document.querySelectorAll('[data-view]');
function show(id){
  views.forEach(function(v){ v.hidden = (v.dataset.view !== id); });
  window.scrollTo(0, 0);
  if (id !== 'index') history.replaceState(null, '', '#' + id);
  else history.replaceState(null, '', location.pathname);
}
document.addEventListener('click', function(e){
  var row = e.target.closest('.row');
  if (row && row.dataset.slug) { show(row.dataset.slug); return; }
  var back = e.target.closest('[data-home]');
  if (back) { e.preventDefault(); show('index'); }
});
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') show('index');
});
show(location.hash ? location.hash.slice(1) : 'index');
"""

PREVIEW_CSS = """
.pvbanner{max-width:74rem;margin:0 auto;padding:1rem clamp(1rem,4vw,2.5rem) 0;}
.pvbanner div{border:1px solid var(--accent);background:var(--accent-soft);
  border-radius:3px;padding:.7rem .95rem;font-size:.85rem;color:var(--ink-2);}
.pvbanner b{color:var(--accent);font-family:var(--mono);font-size:.7rem;
  letter-spacing:.09em;text-transform:uppercase;}
[data-view][hidden]{display:none;}
"""


def build_preview(recipes):
    """One file, index plus every showable recipe, navigable without a server."""
    live = [r for r in recipes if has_content(r)]
    if not live:
        raise SystemExit("no recipe has content yet - nothing to preview")

    parts = [
        '<div class="pvbanner"><div><b>Preview</b> &nbsp;'
        "Generated by <code>build.py --preview</code> from %d recipe folder%s. "
        "Click a recipe; Esc returns. Interactive demos are declared but their "
        "runtime is not built yet."
        "</div></div>" % (len(live), "" if len(live) == 1 else "s"),
        '<div data-view="index">%s</div>' % build_index(live, body_only=True),
    ]
    for r in live:
        parts.append(
            '<div data-view="%s" hidden>%s</div>'
            % (esc(r["slug"]), build_detail(r, body_only=True))
        )
    body = "".join(parts) + "<script>%s</script>" % PREVIEW_JS
    html_doc = page("SignalWire Recipes - preview", body)
    return html_doc.replace("</style>", PREVIEW_CSS + "</style>", 1)


def main():
    if not RECIPES.exists():
        print("no recipes/ dir — run scaffold.py first")
        return 1
    recipes = load()
    if "--preview" in sys.argv:
        SITE.mkdir(parents=True, exist_ok=True)
        out = SITE / "preview.html"
        out.write_text(build_preview(recipes), encoding="utf-8")
        live = [r for r in recipes if has_content(r)]
        print(
            f"preview: {len(live)} of {len(recipes)} recipes have content "
            f"-> {out.name} ({out.stat().st_size // 1024} KB)"
        )
        for r in live:
            print(f"    + {r['slug']}")
        return 0
    if not recipes:
        print("no recipe.json found under recipes/")
        return 1

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "r").mkdir(parents=True)

    (SITE / "index.html").write_text(build_index(recipes), encoding="utf-8")
    for r in recipes:
        (SITE / "r" / f"{r['slug']}.html").write_text(build_detail(r), encoding="utf-8")
        (SITE / "r" / f"{r['slug']}.md").write_text(build_md(r), encoding="utf-8")
    (SITE / "llms.txt").write_text(build_llms(recipes), encoding="utf-8")
    (SITE / "sitemap.xml").write_text(build_sitemap(recipes), encoding="utf-8")

    launch = sum(1 for r in recipes if r.get("tier") == "launch")
    print(
        f"build: {len(recipes)} recipes -> site/  "
        f"({launch} launch tier, {len(recipes)*2+3} files)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
