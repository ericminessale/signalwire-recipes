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
# BASE and indexability come from site.config.json; see site_config().
# Assigned in main() once the config has been read.
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
  color-scheme:dark;
  --page:#0f0f12;
  --surface:#16161a;
  --raised:#1c1c21;
  /* depth scale: a well is recessed (read into), a plate is raised (asserted
     at you). Both are neutral - the hierarchy costs no colour. */
  --well:#0a0a0c;
  --well-line:rgba(0,0,0,.6);
  --plate:#1c1c22;
  --lip:inset 0 1px 0 rgba(255,255,255,.05);
  --sunk:inset 0 1px 3px rgba(0,0,0,.5);
  --lift:0 1px 2px rgba(0,0,0,.4),0 10px 28px -14px rgba(0,0,0,.7);
  --fg:#f4f4f6;
  --fg-2:#c9c9d0;
  /* The prose scale sits a step higher than it used to. #8b8b96 body text
     was grey on grey, and #63636e under it failed AA outright at 14px, which
     covered Run it, Verify it and every caption. */
  --fg-muted:#adadb8;
  --fg-subtle:#8b8b96;
  /* a ladder: a hairline inside a panel, a border around one, and an edge that
     is being pointed at. One strength is not a hierarchy. */
  --line:rgba(255,255,255,.11);
  --line-2:rgba(255,255,255,.17);
  --line-3:rgba(255,255,255,.24);
  --r-lg:10px;  /* code window, claim */
  --r-md:6px;   /* command wells, inline code blocks */
  --r-sm:3px;   /* chips */
  --fuchsia:#F72A72;
  /* Two accents, not three. Fuchsia acts and marks builds; periwinkle
     selects and navigates. Every accent job reads these, so the palette is
     one edit rather than a hunt through the stylesheet. */
  /* Three accents doing three different jobs, not one tinting everything.
     --accent is the exhibit (evidence, replay), --turq is the code and the
     things you type, and fuchsia carries the claim and selection. */
  --accent:#8B96FF;
  --accent-rgb:139,150,255;
  --select-rgb:110,123,255;
  --turq:#40E0D0;
  --turq-rgb:64,224,208;
  --fuchsia-rgb:247,42,114;
  --head:'Instrument Sans',ui-sans-serif,system-ui,sans-serif;
  --body:Lexend,ui-sans-serif,system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,monospace;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
.skip{position:absolute;left:-9999px;top:0;background:var(--fuchsia);color:#fff;
  padding:10px 16px;border-radius:0 0 var(--r-md) 0;font-size:13px;z-index:100;}
.skip:focus{left:0;}
/* author display rules (.card{display:flex}) beat the UA's [hidden]; the
   filters and the unbuilt toggle set the attribute, so it must always win */
[hidden]{display:none!important;}
button,a,summary{touch-action:manipulation;}
body{margin:0;background:var(--page);color:var(--fg);font-family:var(--body);
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;}
/* translucent on purpose: the selected text has to read through it */
::selection{background:rgba(var(--fuchsia-rgb),.32);color:#fff;}
a{color:inherit;text-decoration:none;}
code,.mono{font-family:var(--mono);font-feature-settings:'tnum','zero';}
h1,h2,h3{font-family:var(--head);font-weight:600;letter-spacing:-.04em;
  line-height:1.1;margin:0;color:var(--fg);text-wrap:balance;}
/* the frame grows with the screen: 1180 was a strip on a 4K monitor and left a
   code pane 80 characters wide. 1560 fits the longest recipe line (114ch) at
   1920 with room; below 1244px the viewport decides anyway */
.wrap{max-width:1560px;margin:0 auto;
  padding:0 max(32px,env(safe-area-inset-right)) 120px max(32px,env(safe-area-inset-left));}

/* hero, centred like the site's section heads */
.hero{padding:76px 0 0;text-align:center;}
.eyebrow{font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.16em;
  text-transform:uppercase;color:var(--fuchsia);display:inline-flex;align-items:center;
  gap:10px;}
.eyebrow::before{content:"";width:22px;height:1px;background:var(--fuchsia);}
.hero h1{font-size:clamp(38px,5.4vw,64px);margin:20px auto 0;max-width:17ch;}
.hero p{color:var(--fg-muted);font-size:16px;line-height:1.65;max-width:60ch;
  margin:18px auto 0;}
.cta{display:flex;gap:12px;justify-content:center;margin:28px 0 0;}
.btn{display:inline-flex;align-items:center;gap:8px;font-family:var(--body);
  font-size:13px;font-weight:500;padding:9px 20px;border-radius:var(--r-md);
  background:var(--fuchsia);color:#fff;border:1px solid var(--fuchsia);
  cursor:pointer;font-weight:600;}
.btn:hover{background:#ff3f81;border-color:#ff3f81;}
.btn.ghost{background:transparent;color:var(--fg);border-color:var(--line-2);}
.btn.ghost:hover{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.24);}
.btn:focus-visible{outline:2px solid var(--fuchsia);outline-offset:3px;}

/* sticky filter strip */
.controls{position:sticky;top:0;z-index:50;background:var(--page);
  border-bottom:1px solid var(--line);margin-top:58px;padding:14px 0;
  display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
#q{flex:1 1 15rem;min-width:11rem;background:var(--surface);color:var(--fg);
  border:1px solid var(--line-2);border-radius:var(--r-md);padding:8px 12px;
  font-family:var(--mono);font-size:12px;}
#q::placeholder{color:var(--fg-subtle);}
#q:focus-visible{outline:2px solid var(--fuchsia);outline-offset:1px;border-color:var(--fuchsia);}
.chip{font-family:var(--body);font-size:12.5px;padding:7px 14px;border-radius:var(--r-md);
  display:inline-flex;align-items:center;gap:7px;
  border:1px solid transparent;background:transparent;color:var(--fg-muted);cursor:pointer;}
.chip:hover{color:var(--fg);}
/* Selection is the one state that answers "what am I looking at", so it
   carries colour. It takes --select-rgb, a shade deeper than --accent, so a
   selected chip outranks ordinary accent text without becoming a third hue.
   Fuchsia's jobs are untouched. */
.chip[aria-pressed="true"]{color:#eef0ff;
  background:rgba(var(--select-rgb),.22);
  border-color:rgba(var(--select-rgb),.62);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07);}
.chip[aria-pressed="true"] .cn{color:#c8ceff;}
.chip[aria-pressed="true"]:hover{background:rgba(var(--select-rgb),.31);}
.chip:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}

/* category section */
.cat-h .n{font-family:var(--mono);font-size:12px;color:var(--fg-subtle);}

/* the build row: a wide band, one per category */

/* recipe grid: denser, four up */
.grid{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);
  border-radius:var(--r-lg);overflow:hidden;
  grid-template-columns:repeat(auto-fill,minmax(258px,1fr));}
.card{display:flex;flex-direction:column;gap:6px;min-width:0;background:var(--page);
  padding:17px 19px 18px;color:inherit;transition:background 140ms ease;
  /* the filter strip is sticky: keep a focused card out from under it */
  scroll-margin-top:86px;
  /* 113 cards in the preview: skip layout for offscreen ones. Find-in-page
     still reaches them, unlike virtualisation, which the crawler needs. */
  content-visibility:auto;contain-intrinsic-size:auto 186px;}
.card:hover{background:var(--surface);}
.card:focus-visible{outline:2px solid var(--fuchsia);outline-offset:-2px;}
/* preview --all: not yet written */
.card.planned{cursor:default;}
.card.planned:hover{background:var(--page);}
.card.planned .ct,.card.planned .cd{color:var(--fg-subtle);}
.card.planned .cs{color:var(--fg-subtle);opacity:.7;}
.card.planned .surf{color:var(--fg-subtle);border:1px solid var(--line);border-radius:var(--r-sm);padding:1px 6px;}
.card .ct{font-family:var(--head);font-weight:600;font-size:14.5px;line-height:1.3;
  letter-spacing:-.015em;}
.card .cs{font-family:var(--mono);font-size:10.5px;color:var(--accent);
  line-height:1.4;overflow-wrap:anywhere;}
.card .cd{font-size:12.5px;color:var(--fg-muted);line-height:1.55;flex:1;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
.card .cf{display:flex;gap:8px;align-items:center;margin-top:2px;}
.card .cf .sp{flex:1;}
.sublab{font-size:11px;color:var(--fg-subtle);}
.surf{font-family:var(--mono);font-size:10.5px;color:var(--fg-subtle);}

.empty{padding:48px 0;color:var(--fg-muted);text-align:center;}
.hint{margin-top:44px;font-family:var(--mono);font-size:11px;color:var(--fg-subtle);
  text-align:center;}
kbd{font-family:var(--mono);background:var(--raised);border:1px solid var(--line);
  border-radius:var(--r-sm);padding:1px 5px;font-size:11px;}

/* ---- recipe page ---- */
.detail{padding:56px 0 0;}
/* Two columns from 1080px: the argument on the left, the code and what to do
   with it on the right. Nothing sticks - both columns simply run, so neither
   can cover the other and neither dies halfway down. */
.dgrid{display:grid;grid-template-columns:minmax(0,1fr);gap:0 60px;align-items:start;margin-top:32px;}
@media (min-width:1080px){.dgrid{grid-template-columns:minmax(0,2fr) minmax(0,3fr);}
  .dgrid.solo{grid-template-columns:minmax(0,1fr);}}
/* nothing to sit beside the prose: one centred column reads as an essay,
   where a 2fr strip against an empty 3fr reads as a broken page */
.detail.solo{max-width:900px;margin-inline:auto;}
.detail.solo .rels{margin-top:44px;}
.dh{max-width:60ch;}
/* the first rule on the page, and the brand's colour rather than a grey */
.drule{height:2px;background:var(--fuchsia);margin:30px 0 0;}
/* The site header on a recipe page. Present, not sticky: a sticky element
   here has painted over three sections before. The mark is smaller than the
   index hero's so it reads as a header rather than a second hero. */
.shead{display:flex;align-items:center;gap:30px;padding:0 0 18px;margin:0;
  flex-wrap:wrap;}
.slock{display:inline-flex;align-items:center;gap:9px;color:var(--fg-2);
  font-family:var(--head);font-weight:600;font-size:15px;letter-spacing:-.01em;}
.slock:hover{color:var(--fg);}
.slock .lg{height:19px;width:auto;display:block;}
.slock .dot{width:3px;height:3px;border-radius:50%;background:var(--fg-subtle);}
.slock:focus-visible,.sback:focus-visible{outline:2px solid var(--fuchsia);
  outline-offset:3px;border-radius:var(--r-sm);}
.sback{font-family:var(--mono);font-size:11.5px;color:var(--fg-muted);}
.sback:hover{color:var(--fg);}
/* The page's primary action. The site exists to hand you a folder to clone,
   so this is not a footnote. Solid fuchsia: the action colour, as a fill. */
.ghcta{margin-left:auto;display:inline-flex;align-items:center;gap:8px;
  font-family:var(--body);font-size:12.5px;font-weight:600;color:#fff;
  background:var(--fuchsia);border-radius:var(--r-md);padding:8px 15px;
  white-space:nowrap;transition:filter 130ms ease,transform 130ms ease;}
.ghcta svg{width:14px;height:14px;display:block;flex:none;}
.ghcta:hover{filter:brightness(1.09);color:#fff;}
.ghcta:active{transform:translateY(1px);}
.ghcta:focus-visible{outline:2px solid var(--fuchsia);outline-offset:3px;}
@media (max-width:600px){.ghcta{margin-left:0;}}
.back{font-family:var(--mono);font-size:11.5px;color:var(--fg-muted);}
.back a:hover{color:var(--fg);}
.dh h1{font-size:clamp(30px,4vw,42px);margin-top:18px;}
/* an identifier is something you type, so it matches the code */
.tech{font-family:var(--mono);font-size:12px;color:var(--turq);}
/* product line, then the identifier, on one line under the title */
.kicker{display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-size:12.5px;
  font-weight:500;color:var(--fg-2);margin-top:14px;}
.kicker .kcat{color:var(--fg-2);}
.kicker .dot{width:3px;height:3px;border-radius:50%;background:var(--fg-subtle);
  flex:none;}

.sub{color:var(--fg-muted);font-size:16px;line-height:1.65;margin:16px 0 0;max-width:60ch;}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin:20px 0 0;}
.b{font-family:var(--mono);font-size:10.5px;color:var(--fg-subtle);
  background:var(--raised);border-radius:var(--r-sm);padding:3px 8px;}
/* The claim is the one thing the page asserts and the largest object on it,
   so it takes fuchsia. That is what makes a recipe page read as ours: the
   sentence the page is judged on is in the brand's colour, not a tint. */
/* One object, one accent. The claim is periwinkle throughout: wash, border
   and keyline. Two accents inside a single small object read as a mistake,
   whatever the reasoning behind the split was. */
.claim{background:rgba(var(--accent-rgb),.05);border:1px solid rgba(var(--accent-rgb),.2);
  border-radius:var(--r-lg);padding:24px 26px 26px;margin:0 0 40px;
  box-shadow:inset 3px 0 0 rgba(var(--accent-rgb),.85),inset 0 1px 0 rgba(255,255,255,.07),
    0 2px 5px rgba(0,0,0,.45),0 16px 36px -18px rgba(0,0,0,.85);}
.claim h2{font-family:var(--head);font-size:12.5px;letter-spacing:-.01em;
  color:var(--accent);font-weight:600;margin:0 0 10px;}
.claim p{margin:0;color:var(--fg);font-size:18px;line-height:1.55;letter-spacing:-.005em;
  max-width:62ch;}
/* Evidence is quoted, not framed: no fill and no border, a keyline down the
   left the way a pull quote is set. It is the one thing on the page nobody
   else in developer documentation has, and it should not look like a card. */
/* the exhibit keeps its own colour, so it reads as a distinct register */
.ev{margin:0 0 40px;padding-left:18px;border-left:2px solid rgba(var(--accent-rgb),.5);}
.ev-h{display:flex;align-items:center;gap:9px;padding:0 0 12px;
  font-family:var(--head);font-size:13px;font-weight:600;color:var(--fg-2);}
.ev-h .dot{width:7px;height:7px;border-radius:999px;background:var(--accent);flex:none;}
.ev-b{padding:0;}
.ev cite{display:block;margin-top:16px;font-style:normal;font-size:12px;color:var(--fg-subtle);}
.tr{font-family:var(--mono);font-size:12px;line-height:1.8;}
.tr .l{display:grid;grid-template-columns:52px 1fr;gap:14px;padding:1px 0;}
.tr .w{color:var(--fg-subtle);text-align:right;border-right:1px solid var(--line);
  padding-right:13px;margin-right:-1px;}
.tr .w.ai{color:var(--accent);}
/* the annotations are the editor speaking, not the call */
.tr .sys{color:var(--fg-muted);padding:9px 13px;margin:11px 0 11px 66px;display:block;
  font-size:11px;line-height:1.65;background:var(--surface);border-radius:var(--r-sm);}
.acts{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:18px;}
.acts .n{font-size:12px;color:var(--fg-subtle);flex:1 1 16rem;}
/* The replay control belongs to the evidence, so it sits in its header
   rather than under it as a call to action. */
.ev-h .trplay{margin-left:auto;display:inline-flex;align-items:center;gap:7px;
  font-family:var(--body);font-size:11.5px;letter-spacing:0;color:var(--accent);
  background:rgba(var(--accent-rgb),.08);border:1px solid rgba(var(--accent-rgb),.26);
  border-radius:var(--r-sm);padding:5px 11px;cursor:pointer;text-transform:none;
  transition:background 130ms ease,border-color 130ms ease,color 130ms ease;}
.ev-h .trplay:hover:not(:disabled){background:rgba(var(--accent-rgb),.16);
  border-color:rgba(var(--accent-rgb),.5);}
.ev-h .trplay:disabled{opacity:.4;cursor:default;}
.ev-h .trplay:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.trplay .ti{width:0;height:0;border-style:solid;border-width:4.5px 0 4.5px 7px;
  border-color:transparent transparent transparent currentColor;}
.trplay[data-state="playing"] .ti{width:7px;height:8px;border:none;
  background:linear-gradient(to right,currentColor 0 2.5px,transparent 2.5px 4.5px,
  currentColor 4.5px 7px);}
.evnote{font-size:11.5px;color:var(--fg-subtle);margin:14px 0 0;}
/* The reading column arrives in the order the argument is made.
   Driven by scroll position, not by events: an IntersectionObserver fires on
   threshold crossings, so a section that passes the viewport between frames
   goes from ratio 0 to ratio 0, never fires, and stays invisible for good.
   A view() timeline holds its end state once the range is passed, so no
   scroll speed, anchor jump or restored position can strand content.
   Browsers without support simply get the page, fully visible. */
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .dmain > .claim,
    .dmain > .ev,
    .dmain > .sec{
      animation:rvin linear both;
      animation-timeline:view();
      animation-range:entry 0% entry 34%;
    }
  }
}
@keyframes rvin{
  from{opacity:0;transform:translateY(10px);}
  to{opacity:1;transform:none;}
}

/* Replay fades turns in; it never removes them from the layout or from the
   accessibility tree. `display:none` would take an unrevealed turn out of
   that tree, so pressing Replay made the transcript vanish for a screen
   reader. Opacity keeps the whole transcript readable by assistive tech
   throughout, and reserves the block's full height, so nothing shifts. */
/* opacity:0, not display:none. An element at zero opacity stays in the
   accessibility tree and is still read, so a screen reader keeps the whole
   transcript while a sighted reader watches it arrive. */
.tr.replay .l,.tr.replay .sys{opacity:0;transition:opacity 240ms ease;}
.tr.replay .l.on,.tr.replay .sys.on{opacity:1;}
/* The caret rides the last revealed turn, so no node is moved and it cannot
   be orphaned or left mid-list. It hangs off the turn's text span: on .l,
   which is a grid, an ::after on the row itself becomes a third column and
   wraps to its own line. */
.tr.replay .l.tip span:last-child::after,
.tr.replay .sys.tip::after{content:"";display:inline-block;width:7px;height:12px;
  background:var(--accent);vertical-align:-2px;margin-left:7px;
  animation:trblink 1s steps(2,start) infinite;}
@keyframes trblink{50%{opacity:0;}}
/* Reduced motion keeps the reading pace and drops the animation. Collapsing
   the pace instead turned a replay into nine flashes in under a second. */
@media (prefers-reduced-motion:reduce){
  .tr.replay .l,.tr.replay .sys{transition:none;}
  .tr.replay .tip::after{animation:none;}}
.btn:disabled{background:var(--raised);border-color:var(--line);color:var(--fg-subtle);
  cursor:not-allowed;}
.sec{margin:34px 0;}
.sec h2{font-size:19px;margin:0 0 10px;}
.rels h2{font-size:13.5px;font-weight:600;color:var(--fg-2);}
/* A section break, not a page rule. Full width repeated at every boundary
   made the same gesture four times down one column; short and centred reads
   as punctuation between sections. The rule under the header stays full width
   because it separates the head from the body, which is a different job. */
.sec.arg{margin:0 0 40px;padding-top:30px;position:relative;}
.sec.arg::before{content:"";position:absolute;top:0;left:50%;
  transform:translateX(-50%);width:18%;min-width:64px;height:1px;
  background:var(--fuchsia);}
.sec.arg h2{font-size:21px;display:block;margin:0 0 14px;}
/* procedure sections are quieter and tighter: type alone separates them */
.sec.proc{margin:24px 0 0;}
.sec.proc h2{font-size:13.5px;font-weight:600;color:var(--fg-2);margin:0 0 9px;
  display:block;}
.sec p{margin:0 0 12px;color:var(--fg-muted);font-size:15px;line-height:1.7;max-width:66ch;}
.sec.proc p{font-size:14px;color:var(--fg-subtle);}
.sec p em{font-style:italic;color:var(--fg-2);}
.steps{font-family:var(--mono);font-size:12px;color:var(--fg-2);background:var(--well);
  border:none;border-left:2px solid rgba(var(--turq-rgb),.5);border-radius:0 var(--r-md) var(--r-md) 0;
  padding:13px 16px;line-height:1.9;overflow-x:auto;}
.steps .cl{display:block;padding-left:20px;text-indent:-20px;}
.steps .cl::before{content:"$";color:var(--fg-subtle);display:inline-block;width:20px;
  text-indent:0;}
.cw{margin:0;border:1px solid var(--line-2);border-radius:var(--r-lg);overflow:hidden;
  background:#131316;box-shadow:var(--lip),0 1px 2px rgba(0,0,0,.35),
    0 8px 20px -16px rgba(0,0,0,.65);}
.cwh{display:flex;align-items:stretch;justify-content:space-between;gap:12px;
  background:#131316;padding:0 6px 0 0;}
.cwr{display:flex;align-items:center;gap:12px;}
.cwr .fn{font-family:var(--mono);font-size:11px;color:var(--fg-subtle);}
.copy{font-family:var(--body);font-size:11.5px;color:var(--fg-muted);background:transparent;
  border:1px solid var(--line-2);border-radius:var(--r-md);padding:4px 10px;cursor:pointer;}
.copy:hover{color:var(--fg);border-color:var(--fg-subtle);}
.copy:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}
.stabs{display:flex;gap:2px;}
.stab{font-family:var(--mono);font-size:11px;padding:8px 13px;border:none;
  background:transparent;color:var(--fg-subtle);cursor:pointer;
  border-bottom:2px solid transparent;}
.stab:hover{color:var(--fg);}
.stab[aria-selected="true"]{color:var(--fg);border-bottom-color:var(--fuchsia);
  border-bottom-width:2px;}
pre.src{margin:0;background:var(--well);color:var(--fg-2);padding:18px 18px 20px;
  overscroll-behavior:contain;
  border:none;border-top:1px solid var(--well-line);box-shadow:var(--sunk);
  font-family:var(--mono);font-size:12px;line-height:1.8;overflow-x:auto;}
.cxlist{display:flex;flex-wrap:wrap;gap:6px;}
pre.src .c,pre.src .c1,pre.src .cm,pre.src .cs,pre.src .ch{color:var(--fg-subtle);font-style:italic;}
pre.src .k,pre.src .kn,pre.src .kd,pre.src .kr,pre.src .kt,pre.src .kc{color:var(--fg);font-weight:500;}
pre.src .s,pre.src .s1,pre.src .s2,pre.src .sd,pre.src .sa,pre.src .se,pre.src .si,pre.src .sb,pre.src .sh,pre.src .sx,pre.src .l-Scalar-Plain{color:var(--turq);}
pre.src .nf,pre.src .nc,pre.src .fm,pre.src .nx{color:var(--fg);}
pre.src .nd,pre.src .na{color:var(--fg-muted);}
pre.src .nt{color:var(--fg);}
pre.src .mi,pre.src .mf,pre.src .mh,pre.src .m{color:var(--fg-2);}
pre.src .nb,pre.src .bp,pre.src .nn{color:var(--fg-2);}
pre.src .o,pre.src .p,pre.src .punctuation{color:var(--fg-muted);}
/* illustrative code inside prose: quieter than a command, quieter than the
   artifact, and it wraps rather than scrolls */
pre.mdcode{margin:10px 0 14px;background:rgba(255,255,255,.025);color:var(--fg-muted);
  padding:13px 16px;border:none;border-left:1px solid var(--line);border-radius:0;
  font-family:var(--mono);font-size:12px;line-height:1.6;white-space:pre-wrap;
  overflow-wrap:anywhere;}
.rels{border-top:1px solid var(--line-2);padding-top:24px;margin-top:56px;}
.rels .rel{border-top:1px solid var(--line);padding:12px 0 14px;}
@media (min-width:1080px){.rels{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:0 28px;}
  .rels h2{grid-column:1/-1;}}
.rels .rel h3{font-size:13px;font-weight:600;color:var(--fg-2);margin:0 0 8px;}
.rels .rel p{margin:0;color:var(--fg-2);font-size:14px;}
a.cx{font-family:var(--mono);font-size:11px;color:var(--fg-2);background:var(--raised);
  border-radius:var(--r-md);padding:5px 10px;}
a.cx:hover{color:var(--fg);}
.dfoot{border-top:1px solid var(--line);margin-top:50px;padding-top:20px;display:flex;
  gap:22px;flex-wrap:wrap;font-family:var(--mono);font-size:11.5px;}
.dfoot a{color:var(--turq);}
.pvbanner{max-width:1560px;margin:0 auto;padding:14px 32px 0;}
/* A preview notice, not a feature: one muted line, right-aligned, and a text
   button. Planned rows are hidden by default now that most of the corpus is
   written (Eric, 2026-09-02); the plate and the switch went with the old
   default, because a control this quiet should not look like a setting. */
.pvbanner .pvb{display:flex;align-items:center;justify-content:flex-start;gap:14px;
  flex-wrap:wrap;font-size:12.5px;color:var(--fg-muted);}
.pvbanner b{color:var(--fg);font-weight:500;font-variant-numeric:tabular-nums;}
.pvtog{font-family:var(--body);font-size:12.5px;color:var(--fg);cursor:pointer;
  background:transparent;border:0;padding:4px 0;
  text-decoration:underline;text-underline-offset:3px;text-decoration-color:var(--line-3);}
.pvtog:hover{color:var(--fg);text-decoration-color:currentColor;}
.pvtog:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}
[data-view][hidden]{display:none;}

/* collapsed category still shows its shape: name, count, task groups */
details.cat{border-bottom:1px solid var(--line);}
details.cat[open]{padding-bottom:34px;}
/* a landmark reads as one: an open category lifts off the page ground */
details.cat[open]>summary.cat-h{background:linear-gradient(
  to bottom,rgba(255,255,255,.045),rgba(255,255,255,0));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06);}
summary.cat-h{transition:background 140ms ease;border-radius:var(--r-md) var(--r-md) 0 0;
  padding-left:10px;padding-right:10px;margin-left:-10px;margin-right:-10px;}
summary.cat-h:hover{background:rgba(255,255,255,.03);}
.cat-h .n{font-family:var(--mono);font-size:11px;color:var(--fg-2);
  background:rgba(255,255,255,.06);border-radius:var(--r-sm);padding:2px 6px;
  margin-left:2px;}
summary.cat-h{list-style:none;cursor:pointer;display:flex;align-items:baseline;
  gap:14px;padding:22px 10px;flex-wrap:wrap;}
summary.cat-h::-webkit-details-marker{display:none;}
summary.cat-h::before{content:"+";font-family:var(--mono);font-size:13px;
  color:var(--fg-subtle);width:12px;}
details.cat[open]>summary.cat-h::before{content:"-";}
summary.cat-h:hover .ct2{color:var(--fg-2);}
summary.cat-h:focus-visible{outline:2px solid var(--fuchsia);outline-offset:3px;}
.ct2{font-family:var(--head);font-weight:600;font-size:23px;letter-spacing:-.03em;}
.cat-h .n{font-family:var(--mono);font-size:11.5px;color:var(--fg-subtle);}
/* Task groups. These were a run-on of grey text that looked like navigation
   and was not; now they are buttons that open the category and go to the
   group, so the affordance and the behaviour agree. */
.tgs{display:flex;gap:5px;flex-wrap:wrap;margin-left:auto;justify-content:flex-end;
  max-width:70%;row-gap:5px;}
.tg{display:inline-flex;align-items:center;gap:6px;font-family:var(--body);
  font-size:11.5px;line-height:1;color:var(--fg-muted);cursor:pointer;
  padding:5px 8px;border-radius:var(--r-sm);border:1px solid transparent;
  background:rgba(255,255,255,.035);
  transition:background 130ms ease,color 130ms ease,border-color 130ms ease;}
.tg:hover{background:rgba(255,255,255,.07);color:var(--fg);
  border-color:var(--line-2);}
.tg:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}
.tg .cn{font-family:var(--mono);font-size:10px;color:var(--fg-subtle);
  background:rgba(0,0,0,.35);border-radius:var(--r-sm);padding:2px 5px;}
.tg:hover .cn{color:var(--fg-2);}
/* the count is a pill, the same object the task-group strip uses, centred on
   the label's box. A bare numeral on the baseline read as too low and a
   numeral raised 1px read as an exponent (Eric, 2026-09-02); a pill has its
   own edges, so where it sits is not a question. */
.chip .cn{font-family:var(--mono);font-size:10.5px;color:var(--fg-subtle);line-height:1.4;
  background:rgba(0,0,0,.35);border-radius:var(--r-sm);padding:1px 5px;}
.catbody{padding-top:4px;}
.tgroup{margin-top:22px;}
.tgh{font-family:var(--body);font-weight:500;font-size:12.5px;color:var(--fg-muted);
  letter-spacing:0;margin:0 0 10px;}

/* a build card spans two recipe columns, so two sit in one recipe row */
.bgrid{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);
  border-radius:var(--r-lg);overflow:hidden;margin:20px 0 4px;
  grid-template-columns:repeat(auto-fill,minmax(518px,1fr));}
.buildcard{display:flex;flex-direction:column;gap:7px;min-width:0;scroll-margin-top:86px;
  background:var(--page);padding:17px 19px 18px;color:inherit;
  box-shadow:inset 2px 0 0 var(--fuchsia),inset 0 0 0 1px var(--line-2);
  transition:background 140ms ease;}
.buildcard:hover{background:var(--surface);}
.buildcard:focus-visible{outline:2px solid var(--fuchsia);outline-offset:-2px;}
/* builds sit under the recipes they are assembled from, so the neutral rule
   opens the block rather than closing it. full-width is deliberate: it
   separates two blocks, not two cells */
/* No rule of its own. The Builds heading already draws one the way every
   task group in the category does, and two lines 29px apart for one
   boundary is one too many. The block still reads as different: its
   cards are wider and carry the build rail. */
.bsec{margin-top:34px;padding-top:6px;}
.buildcard.planned{cursor:default;box-shadow:none;}
.buildcard.planned:hover{background:var(--page);}
.buildcard.planned .bt,.buildcard.planned .bs{color:var(--fg-subtle);}
.buildcard.planned .part.state{background:transparent;border:1px solid var(--line);color:var(--fg-subtle);}
.buildcard .lab{font-family:var(--mono);font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--fg-subtle);}
.buildcard .bt{font-family:var(--head);font-weight:600;font-size:16px;
  letter-spacing:-.02em;line-height:1.25;}
.buildcard .bs{font-size:12.5px;color:var(--fg-muted);line-height:1.55;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.buildcard .parts{display:flex;gap:5px;flex-wrap:wrap;margin-top:2px;}
.buildcard .part{font-family:var(--mono);font-size:10px;color:var(--fg-subtle);background:var(--raised);border-radius:var(--r-sm);padding:2px 6px;}
.buildcard .part.more{color:var(--fg-muted);}
.buildcard .also{color:var(--fg-subtle);margin-left:7px;text-transform:none;
  letter-spacing:0;}
.chip.kind[aria-pressed="true"]{color:var(--fuchsia);
  border-color:rgba(var(--fuchsia-rgb),.35);}

/* brand lockup */
.eyebrow{display:inline-flex;align-items:center;gap:9px;font-family:var(--body);
  font-size:13px;font-weight:500;letter-spacing:0;text-transform:none;
  color:var(--fg-muted);}
.eyebrow::before{content:none;}
.eyebrow .mk{width:15px;height:auto;display:block;}

/* task groups: enough contrast and air to separate on first glance */
.tgroup{margin-top:38px;scroll-margin-top:120px;}
.tgroup:first-child{margin-top:22px;}
.tgh{font-family:var(--head);font-weight:600;font-size:14px;color:var(--fg-2);
  letter-spacing:-.01em;margin:0 0 12px;display:flex;align-items:baseline;gap:9px;}
.tgh .cn{font-family:var(--mono);font-size:11px;color:var(--fg-subtle);font-weight:400;}
.tgh:focus-visible{outline:2px solid var(--fuchsia);outline-offset:4px;border-radius:var(--r-sm);}
.tgh::after{content:"";flex:1;height:1px;background:var(--line);}

/* separators live on the cards, so an unfilled cell is just background */
.grid,.bgrid{gap:0;background:transparent;border:none;
  border-left:1px solid var(--line);border-radius:0;}
.card,.buildcard{border-top:1px solid var(--line);
  border-right:1px solid var(--line);background:transparent;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.028);}
.card:hover,.buildcard:hover{background:var(--surface);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06);}
/* The build rail marks a build that exists. The shared rule above flattened
   every card onto --page and, being later, silently took the rail with it,
   so AI Call Center read like its planned siblings again. Restated after it,
   scoped to builds with a repository. */
.buildcard:not(.planned){box-shadow:inset 2px 0 0 var(--fuchsia),
  inset 0 1px 0 rgba(255,255,255,.028);}
.buildcard:not(.planned):hover{box-shadow:inset 2px 0 0 var(--fuchsia),
  inset 0 1px 0 rgba(255,255,255,.06);}

/* lockup: official mark carries the wordmark */
.eyebrow{display:inline-flex;align-items:center;gap:11px;}
.eyebrow .lg{height:25px;width:auto;display:block;}
.eyebrow .dot{width:4px;height:4px;border-radius:50%;background:var(--fg-subtle);}
.eyebrow{font-family:var(--head);font-weight:600;font-size:20px;
  letter-spacing:-.02em;color:var(--fg-2);}

/* the grid declares itself; the cards no longer repeat it */
.bhead{font-family:var(--head);font-weight:600;font-size:14px;color:var(--fg-2);
  letter-spacing:-.01em;margin:22px 0 12px;display:flex;align-items:baseline;gap:9px;}
.bhead::after{content:"";flex:1;height:1px;background:var(--line);}
.bhead .cn{font-family:var(--mono);font-size:11px;color:var(--fg-subtle);font-weight:400;}

/* the Builds filter is a different kind of thing */
/* .wrapped is set by the script when the chip starts a new flex row */
.chip.kind{margin-left:14px;position:relative;border-color:var(--line);}
/* -18, not -11: the preceding chip paints nothing over its 14px of
   padding, so the midpoint of the boxes is not the midpoint of the ink.
   A divider separates two things; when the strip wraps and Builds starts a
   row there is nothing on its left, so the rule goes. */
.chip.kind.wrapped::before{content:none;}
.chip.kind::before{content:"";position:absolute;left:-18px;top:50%;
  transform:translateY(-50%);width:1px;height:16px;background:var(--line);}
/* A filter state, not a call to action. The tint is the point: solid
   fuchsia here shouts louder than the thing it is filtering. */
.chip.kind[aria-pressed="true"]{color:var(--fuchsia);
  border-color:rgba(var(--fuchsia-rgb),.4);
  background:rgba(var(--fuchsia-rgb),.07);}
/* Featured: three cards with an arrow either side, and no container.
   A plate holding recessed cards is one frame inside another, which is what
   made it read as boxy. The band is the page now and the cards are the
   objects raised off it, so the depth lands on the thing you click. It
   borrows no fuchsia - that colour already has its four jobs. */
.feat{margin:30px 0 46px;}
/* the arrows sit outside the cards and the viewport takes the rest */
.frow{display:flex;align-items:center;gap:14px;}
.frow .fviewport{flex:1 1 auto;min-width:0;}
.frow .farrow{flex:0 0 auto;}
.feathead{display:flex;align-items:center;gap:14px;margin:0 0 14px;}
.feath{font-family:var(--head);font-weight:600;font-size:14px;color:var(--fg-2);
  letter-spacing:-.01em;margin:0;white-space:nowrap;}
/* the heading needs no trailing rule: the strip above already separates
   the band, and a rule running out of a heading is the generated tell */
.feathead::after{content:"";order:1;flex:1;}
.fnav{order:2;display:flex;align-items:center;gap:10px;}
/* A bare chevron, not a button in a ring: the circle read as a container
   around a container. Transparent padding keeps the hit box the ring used to
   provide, and the glyph grows into the accent on hover, on focus, and for a
   moment whenever the cards move, so the control answers them. */
.farrow{display:inline-flex;align-items:center;justify-content:center;
  width:24px;height:24px;padding:11px;box-sizing:content-box;
  border:none;background:none;border-radius:var(--r-sm);cursor:pointer;
  font-size:26px;line-height:1;color:#fff;
  transition:color 160ms ease,transform 220ms cubic-bezier(.34,1.4,.64,1);}
.farrow:hover,.farrow:focus-visible{color:var(--accent);transform:scale(1.45);}
/* A pulse must not shrink an arrow the pointer is already enlarging:
   these rules are equally specific, so the state is scoped instead. */
.farrow.pulse:not(:hover):not(:focus-visible){color:var(--accent);
  transform:scale(1.35);}
.farrow:active{transform:scale(1.1);}
.farrow:focus-visible{outline:2px solid var(--accent);outline-offset:1px;}
@media (prefers-reduced-motion:reduce){
  .farrow,.farrow:hover,.farrow.pulse,.farrow:active{transform:none;}}
.fdots{display:flex;gap:6px;}
.fdot{width:7px;height:7px;padding:0;border-radius:50%;cursor:pointer;
  background:rgba(255,255,255,.18);border:none;transition:background 130ms ease;}
.fdot:hover{background:rgba(255,255,255,.34);}
.fdot.on{background:var(--accent);}
.fdot:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}
.fviewport{overflow:hidden;}
/* --per is set by the script from the viewport, so a page is really a page */
.ftrack{display:flex;gap:10px;--per:3;
  transition:transform 420ms cubic-bezier(.4,0,.2,1);}
.ftrack>.fcard{flex:0 0 calc((100% - (var(--per) - 1) * 10px) / var(--per));}
.fstatus{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);
  white-space:nowrap;margin:0;}
.fplay{width:26px;height:26px;display:inline-flex;align-items:center;
  justify-content:center;border-radius:50%;cursor:pointer;font-size:9px;
  letter-spacing:1px;line-height:1;color:var(--accent);
  background:rgba(var(--accent-rgb),.09);border:1px solid rgba(var(--accent-rgb),.28);
  transition:background 130ms ease,border-color 130ms ease;}
.fplay:hover{background:rgba(var(--accent-rgb),.17);border-color:rgba(var(--accent-rgb),.5);}
.fplay:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}
@media (prefers-reduced-motion:reduce){.ftrack{transition:none;}}
/* With the plate gone the cards are the raised objects on the page. The
   rows below are flat on --page, so this is the level that separates them. */
.fcard{display:flex;flex-direction:column;gap:14px;
  min-height:150px;padding:18px 20px 16px;color:inherit;
  background:linear-gradient(to bottom,#1d1d23,#17171b);
  border:1px solid var(--line-2);border-radius:var(--r-lg);
  box-shadow:var(--lip),var(--lift);
  transition:border-color 140ms ease,transform 140ms ease,box-shadow 140ms ease;}
.fcard:hover{border-color:var(--line-3);transform:translateY(-2px);
  box-shadow:var(--lip),0 2px 4px rgba(0,0,0,.45),0 16px 34px -14px rgba(0,0,0,.8);}
/* The icon says which product line the card belongs to at a glance. It is
   one accent, not six: the page runs on two colours, and a third and fourth
   hue would undo that. The shape differentiates and the tile gives the card
   a focal point. */
.ftile{width:34px;height:34px;display:inline-flex;align-items:center;
  justify-content:center;border-radius:var(--r-md);color:var(--accent);
  background:rgba(255,255,255,.045);border:1px solid var(--line);}
/* An iconless category keeps the slot: display:none takes the 34px and
   the gap with it and drops that card's claim above its neighbours. */
.ftile:empty{visibility:hidden;}
.fico{width:17px;height:17px;display:block;}
.fcard:focus-visible{outline:2px solid var(--fuchsia);outline-offset:2px;}
.fcard .fl{font-family:var(--head);font-weight:600;font-size:19px;
  letter-spacing:-.03em;line-height:1.22;color:var(--fg);text-wrap:balance;}
.fcard .fm{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin-top:auto;}
.fcard .fn{font-family:var(--mono);font-size:11px;color:var(--fg-muted);}
.fcard .fc{font-size:11.5px;color:var(--fg-subtle);margin-left:auto;}
/* A planned card has nothing behind it, so it does not get the lift. */
.fcard.planned{cursor:default;background:var(--surface);box-shadow:none;
  border-color:var(--line);}
.fcard.planned:hover{transform:none;border-color:var(--line);box-shadow:none;}
.fcard.planned .fl{color:var(--fg-muted);}
.fcard.planned .ftile{color:var(--fg-subtle);background:rgba(255,255,255,.03);
  border-color:var(--line);}
@media (max-width:760px){.tgs{display:none;}}
/* The glyph may shrink at touch widths; the hit box may not. */
@media (max-width:760px){.frow{gap:2px;}
  .farrow{width:22px;height:22px;font-size:22px;padding:11px;}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;}}
"""

JS = """
const items=[...document.querySelectorAll('.card,.buildcard')];
const cats=[...document.querySelectorAll('details.cat')];
const q=document.getElementById('q');
const chips=[...document.querySelectorAll('.chip')];
const allChip=chips.find(c=>c.dataset.f==='all');
function active(){return chips.filter(c=>c.getAttribute('aria-pressed')==='true'
  &&c.dataset.f!=='all').map(c=>c.dataset.f);}
const tog=document.getElementById('pvtog');  // preview --all only
function apply(){
  const t=q.value.trim().toLowerCase();
  const on=active();
  const hideUnbuilt=!!tog&&tog.getAttribute('aria-pressed')==='true';
  const kinds=on.filter(f=>f.startsWith('kind:')).map(f=>f.slice(5));
  const cs=on.filter(f=>!f.startsWith('kind:'));
  let n=0;
  items.forEach(c=>{
    const okT=!t||c.dataset.hay.includes(t);
    const okC=!cs.length||cs.some(f=>c.dataset.cat.split(' ').includes(f));
    let okK=!kinds.length||kinds.includes(c.dataset.kind);
    if(kinds.includes('build')&&c.dataset.proj==='1')okK=false;
    const okB=!hideUnbuilt||!c.classList.contains('planned');
    c.hidden=!(okT&&okC&&okK&&okB); if(!c.hidden)n++;
  });
  cats.forEach(g=>{
    const vis=[...g.querySelectorAll('.card,.buildcard')].filter(c=>!c.hidden);
    g.hidden=vis.length===0;
    g.querySelectorAll('.tgroup').forEach(tg=>{
      tg.hidden=![...tg.querySelectorAll('.card')].some(c=>!c.hidden);
    });
    const bs=g.querySelector('.bsec'),bg=g.querySelector('.bgrid');
    const anyB=bg&&[...bg.querySelectorAll('.buildcard')].some(c=>!c.hidden);
    if(bs)bs.hidden=!anyB;
    if(t||on.length)g.open=true;
  });
  // headings count what is actually on screen
  cats.forEach(g=>{
    const shown=[...g.querySelectorAll('.card')].filter(c=>!c.hidden).length;
    const cn=g.querySelector('.cat-h .n'); if(cn)cn.textContent=shown;
    g.querySelectorAll('.tgroup').forEach(tg=>{
      const k=[...tg.querySelectorAll('.card')].filter(c=>!c.hidden).length;
      const c2=tg.querySelector('.tgh .cn'); if(c2)c2.textContent=k;
      // the strip in the category header mirrors the group beneath it
      const strip=g.querySelector('.tgs .tg[data-g="'+tg.dataset.g+'"]');
      if(strip){strip.hidden=k===0;const c3=strip.querySelector('.cn');if(c3)c3.textContent=k;}
    });
    const bh=g.querySelector('.bhead .cn'),bg2=g.querySelector('.bgrid');
    if(bh&&bg2)bh.textContent=[...bg2.querySelectorAll('.buildcard')].filter(c=>!c.hidden).length;
  });
  chips.forEach(ch=>{
    const cn=ch.querySelector('.cn'); if(!cn)return;
    const f=ch.dataset.f;
    cn.textContent=items.filter(c=>!c.classList.contains('planned')||!hideUnbuilt)
      .filter(c=>f==='kind:build'?(c.dataset.kind==='build'&&c.dataset.proj!=='1')
                                 :(c.dataset.kind==='recipe'&&c.dataset.cat.split(' ').includes(f))).length;
  });
  const feat=document.querySelector('.feat');
  if(feat){
    const fc=[...feat.querySelectorAll('.fcard')];
    fc.forEach(c=>{c.hidden=hideUnbuilt&&c.classList.contains('planned');});
    // the band is a front door, not a result: a search or a chip replaces it
    feat.hidden=!!(t||on.length)||fc.every(c=>c.hidden);
  }
  const band=document.querySelector('.feat');
  if(band)band.dispatchEvent(new Event('featured:relayout'));
  allChip.setAttribute('aria-pressed',on.length?'false':'true');
  const none=document.getElementById('none'); if(none)none.hidden=n>0;
  const u=new URL(location.href);
  t?u.searchParams.set('q',t):u.searchParams.delete('q');
  on.length?u.searchParams.set('c',on.join(',')):u.searchParams.delete('c');
  history.replaceState(null,'',u);
}

// --- the Builds divider only exists between two chips on one row ---------
(function(){
  const kind=document.querySelector('.chip.kind');
  if(!kind||!kind.previousElementSibling)return;
  function measure(){
    const a=kind.previousElementSibling.getBoundingClientRect();
    const b=kind.getBoundingClientRect();
    kind.classList.toggle('wrapped',Math.abs(a.top-b.top)>2);
  }
  // A ResizeObserver, not a resize listener batched through rAF: rAF does not
  // run while the tab is hidden, so a window resized in the background would
  // leave the divider stale until the next resize. An observer delivers on the
  // first render after the tab comes back.
  if(window.ResizeObserver){
    const ro=new ResizeObserver(measure);
    ro.observe(kind.parentElement);
  } else {
    window.addEventListener('resize',measure);
  }
  measure();
})();

// --- featured carousel -----------------------------------------------------
// The cards stay in one flat track and the script decides how many make a
// page, because that depends on the viewport and on which cards are filtered
// out. Every card stays in the DOM, so the filter counts and the unbuilt
// toggle still see all of them.
(function(){
  const feat=document.querySelector('.feat'); if(!feat)return;
  const track=feat.querySelector('.ftrack');
  const viewport=feat.querySelector('.fviewport');
  const GAP=10;   // matches the track's gap in the stylesheet
  const dotWrap=feat.querySelector('.fdots');
  const status=feat.querySelector('.fstatus');
  const playBtn=feat.querySelector('.fplay');
  const nav=feat.querySelector('.fnav');
  const arrows=[...feat.querySelectorAll('.farrow')];
  const all=[...feat.querySelectorAll('.fcard')];
  if(!track||!viewport||!all.length)return;
  const still=window.matchMedia('(prefers-reduced-motion: reduce)');
  const wide=window.matchMedia('(min-width: 1101px)');
  const mid=window.matchMedia('(min-width: 761px)');
  let at=0, timer=null, paused=false;

  // String, not Number: setProperty ignores a numeric value, and the cards
  // then keep the stylesheet's width while the script pages a different
  // number of them.
  const perPage=()=>{const n=wide.matches?3:(mid.matches?2:1);
    track.style.setProperty('--per',String(n)); return n;};
  // only cards a filter has left visible are worth paging through
  const shown=()=>all.filter(c=>!c.hidden);
  const pageCount=()=>Math.max(1,Math.ceil(shown().length/perPage()));

  function stop(){ if(timer){clearInterval(timer);timer=null;} }
  function start(){
    stop();
    // every reason to hold still, checked in one place: the arrows and the
    // dots used to restart the timer while the pointer was still inside
    if(paused||document.hidden||still.matches||pageCount()<2)return;
    if(feat.matches(':hover')||feat.contains(document.activeElement))return;
    timer=setInterval(()=>go(at+1,false,1),10000);
  }

  // the arrow the movement went towards grows for a beat, so the control
  // reads as the thing that moved the cards
  let pulseTimer=0;
  function pulse(dir){
    if(still.matches)return;
    const b=arrows.find(a=>Number(a.dataset.step)===dir);
    if(!b)return;
    arrows.forEach(a=>a.classList.remove('pulse'));
    void b.offsetWidth;
    b.classList.add('pulse');
    clearTimeout(pulseTimer);
    pulseTimer=setTimeout(()=>b.classList.remove('pulse'),420);
  }

  function go(i,announce,dir){
    const pages=pageCount();
    const from=at;
    at=(i+pages)%pages;
    const per=perPage();
    const visible=shown();
    // A page spans the viewport exactly, because the cards are sized to fill
    // it, so the offset is whole viewports plus one gap each. offsetLeft
    // cannot be used here: applying a transform makes the track the cards'
    // offsetParent, so the measurement changes meaning as soon as it is used.
    const vw=viewport.getBoundingClientRect().width;
    track.style.transform='translateX(-'+(at*(vw+GAP))+'px)';
    [...dotWrap.children].forEach((d,n)=>{
      d.classList.toggle('on',n===at);
      if(n===at)d.setAttribute('aria-current','page');
      else d.removeAttribute('aria-current');
    });
    // A card nobody can see should be reachable by neither tab nor a screen
    // reader's virtual cursor, so it leaves the accessibility tree too.
    const onPage=new Set(visible.slice(at*per,at*per+per));
    all.forEach(c=>{
      const off=!onPage.has(c);
      c.toggleAttribute('inert',off);
      if(off)c.setAttribute('aria-hidden','true');
      else c.removeAttribute('aria-hidden');
    });
    if(dir&&at!==from)pulse(dir);
    if(announce&&status)status.textContent='Featured page '+(at+1)+' of '+pages;
  }

  function dots(){
    const pages=pageCount();
    dotWrap.innerHTML='';
    for(let i=0;i<pages;i++){
      const d=document.createElement('button');
      d.type='button'; d.className='fdot'; d.dataset.page=i;
      d.setAttribute('aria-label','Featured page '+(i+1)+' of '+pages);
      d.addEventListener('click',()=>{ go(i,true,i>at?1:-1); start(); });
      dotWrap.appendChild(d);
    }
    if(nav)nav.hidden=pages<2;
    arrows.forEach(b=>{b.hidden=pages<2;});
  }

  // rebuilt whenever the page size or the visible set can have changed
  function layout(){ dots(); go(Math.min(at,pageCount()-1),false); start(); }
  feat.addEventListener('featured:relayout',layout);

  arrows.forEach(b=>b.addEventListener('click',()=>{
    const step=Number(b.dataset.step);
    go(at+step,true,step); start();
  }));
  playBtn&&playBtn.addEventListener('click',()=>{
    paused=!paused;
    playBtn.textContent=paused?'\u25B6':'\u2759\u2759';
    playBtn.setAttribute('aria-label',paused?'Play featured':'Pause featured');
    paused?stop():start();
  });
  feat.addEventListener('mouseenter',stop);
  feat.addEventListener('mouseleave',start);
  feat.addEventListener('focusin',stop);
  feat.addEventListener('focusout',e=>{ if(!feat.contains(e.relatedTarget))start(); });
  document.addEventListener('visibilitychange',()=>document.hidden?stop():start());
  [still,wide,mid].forEach(m=>m.addEventListener&&m.addEventListener('change',layout));
  // A resize is not a page change, so it must not animate: retargeting a
  // live transform transition on every resize event makes the cards lag
  // behind the window being dragged. Jump, then restore the transition.
  function place(){
    const prev=track.style.transition;
    clearTimeout(pulseTimer);
    arrows.forEach(a=>a.classList.remove('pulse'));
    track.style.transition='none';
    go(at,false);
    void track.offsetWidth;      // flush, or the restore is coalesced away
    track.style.transition=prev;
  }
  let lastPer=0, raf=0;
  window.addEventListener('resize',()=>{
    if(raf)return;
    raf=requestAnimationFrame(()=>{
      raf=0;
      const per=perPage();
      if(per!==lastPer){lastPer=per;dots();at=Math.min(at,pageCount()-1);
        place();start();return;}
      place();   // same page, new viewport width: re-place the track
    });
  });
  layout();
})();

// --- task groups go where they say they go ---------------------------------
// They used to be text that looked like navigation. Clicking one now opens its
// category and scrolls to the group.
document.querySelectorAll('.tg').forEach(chip=>{
  chip.addEventListener('click',()=>{
    const cat=chip.closest('details.cat'); if(!cat)return;
    cat.open=true;
    const group=document.getElementById(chip.getAttribute('aria-controls'));
    if(!group)return;
    // The cards carry content-visibility:auto, so their real heights replace
    // the estimates as they paint and a smooth scroll chases a moving target.
    // Jump, let layout settle, then correct. The offset clears the sticky
    // strip with room to spare: settling shifts the landing by ~20px.
    const where=()=>group.getBoundingClientRect().top+window.scrollY-120;
    window.scrollTo({top:where(),behavior:'auto'});
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      const target=where();
      if(Math.abs(target-window.scrollY)>4)
        window.scrollTo({top:target,behavior:'auto'});
      // move focus with the viewport, or a keyboard user is still up in the
      // category header with no idea the page went somewhere
      const heading=group.querySelector('.tgh');
      if(heading)heading.focus({preventScroll:true});
    }));
  });
});

q.addEventListener('input',apply);
if(tog)tog.addEventListener('click',()=>{
  const was=tog.getAttribute('aria-pressed')==='true';
  tog.setAttribute('aria-pressed',was?'false':'true');
  const lab=tog.querySelector('.pvl');
  if(lab)lab.textContent=was?'Hide planned':'Show '+tog.dataset.n+' planned';
  apply();
});
chips.forEach(c=>c.addEventListener('click',()=>{
  const was=c.getAttribute('aria-pressed')==='true';
  chips.forEach(o=>o.setAttribute('aria-pressed','false'));
  // clicking All, or clicking the already-active filter, returns to everything
  if(c.dataset.f!=='all'&&!was)c.setAttribute('aria-pressed','true');
  apply();
}));
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus();}
  else if(e.key==='Escape'&&document.activeElement===q){q.value='';apply();q.blur();}
});
(function(){const u=new URL(location.href);const t=u.searchParams.get('q');if(t)q.value=t;
 const c=(u.searchParams.get('c')||'').split(',').filter(Boolean);
 chips.forEach(x=>x.setAttribute('aria-pressed',c.includes(x.dataset.f)?'true':'false'));
 apply();})();
"""


def esc(s):
    return html.escape(str(s), quote=True)


def smart_typography(t):
    """Curly quotes and a real ellipsis in prose. Backtick spans are code and
    are left exactly as the author wrote them."""
    parts = t.split("`")
    for i in range(0, len(parts), 2):  # even segments are outside code
        seg = parts[i].replace("...", "\u2026")
        seg = re.sub(r'(?<![A-Za-z0-9])"', "\u201c", seg)
        seg = seg.replace('"', "\u201d")
        seg = re.sub(r"(?<![A-Za-z0-9])'", "\u2018", seg)
        seg = seg.replace("'", "\u2019")
        parts[i] = seg
    return "`".join(parts)


def md_inline(t):
    t = esc(smart_typography(t))
    t = re.sub(r"`([^`]+)`", r'<code translate="no">\1</code>', t)
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
        blocks, text, code, lang = [], [], None, ""

        def end_text():
            for para in "\n".join(text).split("\n\n"):
                if para.strip():
                    blocks.append(md_inline(" ".join(para.split())))
            text.clear()

        for line in buf:
            if line.startswith("```"):
                if code is None:
                    end_text()
                    code, lang = [], line[3:].strip()
                else:
                    blocks.append(PRE_MARK + esc("\n".join(code)))
                    code = None
                continue
            (code if code is not None else text).append(line)
        end_text()
        out[cur] = blocks

    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            flush()
            cur, buf = line[3:].strip(), []
        elif cur is not None:
            buf.append(line)
    flush()
    return out


PRE_MARK = "\x00pre:"


def blocks_html(blocks):
    """Paragraph strings become <p>; fenced code (PRE_MARK-prefixed) becomes <pre>."""
    return "".join(
        '<pre class="mdcode" translate="no">%s</pre>' % b[len(PRE_MARK):] if b.startswith(PRE_MARK)
        else "<p>%s</p>" % b
        for b in blocks
    )


def prose(blocks):
    return [b for b in blocks if not b.startswith(PRE_MARK)]


# One unknown lexer should not break a build; a missing Pygments should.
# Both used to take the same silent fallback, so a machine without the
# dependency produced a complete site with every code block unstyled.
_HL = {"ok": 0, "fell_back": 0}


def highlight_code(code, lexer_name):
    """Pygments at build time; the lexer comes from the surface's vocab entry.

    Falls back to escaped text when Pygments or the lexer is unavailable, and
    records which, so the build can refuse a site with no highlighting at all.
    """
    if not lexer_name:
        return esc(code)
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        out = highlight(code, get_lexer_by_name(lexer_name, stripnl=False),
                        HtmlFormatter(nowrap=True)).rstrip("\n")
        _HL["ok"] += 1
        return out
    except Exception:
        _HL["fell_back"] += 1
        return esc(code)


def check_advertised_urls():
    """Every URL the site advertises must resolve to a file it wrote.

    og:url and the sitemap both pointed at /<slug>, a clean-URL layout this
    site does not have, so all 56 advertised URLs 404'd. A link that unfurls
    to a dead page is worse than one that does not unfurl.
    """
    if not BASE:
        return
    sm = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    import re as _re
    bad = []
    for loc in _re.findall(r"<loc>([^<]+)</loc>", sm):
        rel = loc[len(BASE):].lstrip("/")
        target = SITE / (rel or "index.html")
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            bad.append(loc)
    if bad:
        raise SystemExit(
            "build: %d advertised URL(s) do not resolve to a written file, "
            "e.g. %s" % (len(bad), ", ".join(bad[:3]))
        )


def check_noindex():
    """Every emitted page must carry the tag while the site is a prototype.

    Checked against the files on disk rather than the code path that should
    have added it, because a page rendered without `page()` would otherwise
    ship indexable and silently.
    """
    if INDEXABLE:
        return
    bad = [f.relative_to(SITE).as_posix()
           for f in sorted(SITE.rglob("*.html"))
           if 'name="robots"' not in f.read_text(encoding="utf-8")]
    if bad:
        raise SystemExit(
            "build: site.config.json says indexable=false but %d page(s) "
            "carry no robots meta: %s" % (len(bad), ", ".join(bad[:5]))
        )


def check_highlighting():
    """Nothing highlighted anywhere is a missing dependency, not a bad lexer."""
    if _HL["fell_back"] and not _HL["ok"]:
        raise SystemExit(
            "build: %d code blocks rendered with no highlighting and none "
            "succeeded. Pygments is probably not installed; run "
            "pip install -r requirements.txt" % _HL["fell_back"]
        )


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
    slugs = {r.get("slug") for r in out}
    for r in out:
        for c in r.get("composes", []):
            if c not in slugs:
                errors.append(
                    "%s: dangling composition edge -> %s "
                    "(no such recipe)" % (r["slug"], c)
                )
        if r.get("kind") != "build" and not r.get("subcategory"):
            errors.append(
                "%s: no task group - navigation cannot rest on "
                "optional metadata" % r["slug"]
            )
        # typed relationships are authored edges; a dangling or self edge is a lie
        for key in ("prerequisites", "related", "next"):
            for c in r.get(key, []):
                if c not in slugs:
                    errors.append(
                        "%s: dangling %s edge -> %s (no such recipe)" % (r["slug"], key, c)
                    )
                elif c == r["slug"]:
                    errors.append("%s: %s edge points at itself" % (r["slug"], key))
    if errors:
        for e in errors:
            print(f"  ! {e}")
        raise SystemExit(
            f"{len(errors)} validation error(s) - build refused. "
            "Unknown values are errors, never silently skipped."
        )
    return out


# The official mark carries the wordmark, so the company name is never
# set as type. One constant: the index hero and every recipe header draw
# it, and two copies would drift.
LOGO = '<svg class="lg" viewBox="0 0 3804 825" aria-label="SignalWire"><path fill="#044ef4" d="M18.93 247.67C126.99 139.86 194.19 72.93 244.29 22.79Q254.73 12.33 268.2 6.71C284.47-.09 303.67 1.72 319.64 8.86C340.08 18.02 352.21 38.14 355.3 59.78c2.35 16.46-2.27 31.84-12.15 44.99q-2.9 3.86-10.63 11.66C258.58 191.04 180.32 268.66 109.87 337.87C88.91 358.47 58.5 363.09 32.96 348.7 10.51 336.04-.28 312.08.43 286.94.84 272.18 8.63 257.94 18.93 247.67Z"/><path fill="#f72a72" d="M665.26 449.81a.38.38 0 0 1-.33.61q-5.28-.39-9.67-.42c-21.47-.15-39.61 7.25-55.81 20.72q-4.62 3.84-14.06 13.94-14.09 15.07-32.69 32.81a.68.67 46.5 0 1-.96-.03q-.01-.02-2.83-2.79Q519.79 486.07 386.1 351.94q-9.76-9.79-12.89-14c-14.21-19.16-16.05-41.29-7.18-63.16q10.26-25.32 35.72-34.76c18.5-6.86 39.07-6.38 56.23 4.06q5.49 3.34 18.82 16.62Q619.85 403.22 662.07 445.95q.86.88 3.19 3.86Z"/><path fill="#f72a72" d="M52.59 370.92q3.38-.04 10.99-.25c16.25-.44 31.01-4.43 44.34-13.44q7.74-5.23 19.06-17.17 4.85-5.12 36.52-37.15a.55.55 0 0 1 .71-.06q2.76 2.01 9.24 8.48 94.27 94.2 160.71 160.72 7.6 7.6 11.85 14.08c11.97 18.22 13.81 40.35 4.98 60.87q-9.39 22.76-31.9 32.22c-18.98 7.97-40.82 8.52-58.7-2.18q-5.47-3.27-17.87-15.65Q128.29 448.23 52.34 371.53a.36.36 0 0 1 .25-.61Z"/><path fill="#044ef4" d="M510.7 577.7q45.26-44.89 96.59-95.41c25.64-25.23 63.88-24.74 90.15-.56q18.78 17.28 18.84 43.01c.04 18.39-5.51 35.18-18.57 48.22Q563.93 706.56 471.73 798.23q-11.12 11.05-26.46 16.48c-38.94 13.8-80.08-14.59-83.94-54.69c-1.87-19.32 5.41-38.1 19.11-52.09Q415.71 671.9 510.7 577.7Z"/><path fill="#fff" d="M960.39 446.64c3.15 5.6 6.52 12.5 10.1 17.7c23.44 34.02 62.95 51.01 103.48 44.09 19.88-3.39 39.82-12.72 49.83-30.59q7.03-12.55 7.43-29 .53-21.78-13.99-37.62-7.2-7.86-23.38-16.91c-25.46-14.23-49.86-24.54-79.55-37.12-11.8-5-27.46-12.12-37.54-17.96q-17.7-10.26-28.74-22.23-20.05-21.74-25.06-51.22c-6.98-41.03 2.74-83.4 34.13-112.11c20.59-18.84 46.37-28.85 74.15-32.68 51.58-7.1 96.22 9.63 133.51 44.51q6.12 5.72 10.94 12.38a.64.63 50.8 0 1-.08.84l-46.34 42.35a.75.75 0 0 1-1.08-.06c-26.9-31.1-60.5-45.81-101.75-34.37-33.86 9.39-49.63 46.92-30.45 76.9c8.7 13.61 25.7 24.03 40.76 31.46 34.23 16.88 68.78 27.65 97.48 43.48c25.61 14.13 46.5 35.09 56.58 62.64 18.14 49.58 7.48 104.38-33.28 139.58c-21.62 18.68-48.41 29.13-76.98 32.4-41.14 4.72-81.88-1.28-116.65-23.25q-25.06-15.83-45.67-42.18c-5.89-7.53-11.51-17.8-16.2-25.76a.36.36 0 0 1 .12-.49l57.23-35.04a.72.71-30.2 0 1 1 .26Z"/><circle fill="#fff" cx="1281.63" cy="159.44" r="40.07"/><circle fill="#fff" cx="3203.24" cy="159.48" r="40.08"/><rect fill="#fff" x="2411.92" y="125.9" width="64" height="442.06" rx=".62"/><path fill="#fff" d="M3000.98 568a.61.59-81.4 0 1-.57.43h-75.36a.36.36 0 0 1-.35-.27l-99.38-356.08a1.48 1.48 0 0 0-2.85 0l-98.14 355.79a.44.44 0 0 1-.42.32h-75.44a.58.58 0 0 1-.56-.42L2516.73 126.49a.43.43 0 0 1 .41-.56h71.1a.82.81 81.9 0 1 .78.59l97.69 332.36a1.25 1.25 0 0 0 2.4-.02l94.25-332.59a.5.5 0 0 1 .48-.37h79.88a.77.77 0 0 1 .74.56l95.09 331.47a1.54 1.54 0 0 0 2.96.01l97.45-331.57a.66.66 0 0 1 .63-.47h70.79a.31.31 0 0 1 .3.4L3000.98 568Z"/><path fill="#fff" d="M1923.39 567.55q-.11-78.78-.03-182.53 .01-7.92-2.97-18.43c-5.86-20.62-21.62-34.85-42.8-38.33-34.61-5.7-65.04 14.17-70.31 49.65q-.71 4.78-.74 16.72-.14 69.6-.04 172.72a.58.58 0 0 1-.58.58h-63.86a.34.34 0 0 1-.34-.34V274.34a.47.47 0 0 1 .47-.47h63.67a.41.4-90 0 1 .4.41v21.29a.44.44 0 0 0 .68.36q11.25-7.6 15.34-10.37 12.85-8.69 28.78-13.93c33.51-11.05 69.24-2.55 97.25 18.31c27.03 20.12 39.97 49.98 40.44 83.31.78 54.7.61 104.95.34 190.01q-.01 1.03-.55 4.47a.66.65-85.3 0 1-.64.55h-63.78a.73.73 0 0 1-.73-.73Z"/><path fill="#fff" d="M3779.14 492.97a.68.68 0 0 1 .37.9c-24.13 56.01-86.6 84.75-145.08 80.76-37.88-2.59-73.01-15.76-100.4-42.07c-44.27-42.51-57.25-106.7-37.05-163.87 14.31-40.53 43.73-72.12 83.22-88.95c33.03-14.07 72.3-16.17 106.68-7.08 70.37 18.59 116.11 87.8 108.25 159.68a.53.53 0 0 1-.53.47h-237.15a.61.59-86.1 0 0-.59.53c-1.35 10.6 1.42 22.1 6.15 31.34q17.33 33.95 51.37 46.34c44 16.01 83.15-5.05 110.45-39.08a.73.72-59.8 0 1 .84-.23l53.47 21.26ZM3722 381.39c-7.73-35.69-45.03-56.53-79.02-56.44c-36.03.1-68.65 21.71-80.38 56.19a.52.51 9.3 0 0 .49.68h158.56a.36.35-6.4 0 0 .35-.43Z"/><path fill="#fff" d="M1612.18 540.9a.23.23 0 0 0-.37-.14c-50.69 40.47-117.4 44.93-172.95 12.9q-30.88-17.81-49.37-47.1c-40.34-63.92-31.02-150.48 25.96-201.44 37.26-33.33 91.07-45.62 139.09-32.27q32.81 9.12 58.75 31.31a.35.34 20.2 0 0 .57-.26v-29.33a.54.54 0 0 1 .54-.54h65.35a.56.56 0 0 1 .56.56q.12 193.45-.08 293.13-.06 28-11.2 56.1c-17.72 44.7-55.44 78.55-101.92 91.23-69.03 18.82-149.45-9.14-188.28-70.38a.84.83-37.1 0 1 .15-1.06l43.99-38.91a.53.53 0 0 1 .8.12c21.22 33.44 53.61 55.69 93.93 56.71 21.03.53 39.7-5.27 56.94-17.11c21.06-14.46 34.12-35.32 37.88-60.47q3.13-20.95-.34-43.06ZM1613.83 420.99a91.72 91.72 0 0 0-91.72-91.72 91.72 91.72 0 0 0-91.72 91.72a91.72 91.72 0 0 0 91.72 91.72 91.72 91.72 0 0 0 91.72-91.72Z"/><path fill="#fff" d="M2283.91 567.65v-34.67a.33.33 0 0 0-.56-.23c-26.5 26.86-60.21 42.26-98.35 42.05-37.01-.21-70.66-11.91-98.08-37.21c-57.54-53.08-67.12-140.42-24-205.45 8.61-13 19.19-24.83 31.95-34.38c43.12-32.26 101.65-40.32 150.69-16.35q20.53 10.04 37.26 25.86a.34.34 0 0 0 .57-.25v-32.4a.59.58 0 0 1 .59-.58h64.85a.74.74 0 0 1 .74.74v292.91a.59.59 0 0 1-.59.59h-64.43a.64.63 0 0 1-.64-.63ZM2101.79 418.15a91.85 91.67-178.2 0 0 88.92 94.51 91.85 91.67-178.2 0 0 94.69-88.74a91.85 91.67-178.2 0 0-88.93-94.51 91.85 91.67-178.2 0 0-94.68 88.74Z"/><path fill="#fff" d="M3364.06 316.07a.25.25 0 0 0 .46.14q5.41-7.82 10.03-14.15c20.14-27.58 52.15-40.62 85.63-31q2.89.83 5.73 2.54a.41.41 0 0 1 .2.35v56.88a.51.51 0 0 1-.53.51c-9.19-.28-21-1.01-29.26-.73c-38.7 1.28-64.56 29.5-70.45 66.84q-1.12 7.06-1.24 21.19c-.31 35.17-.24 74.64-.15 148.75a.61.61 0 0 1-.61.61h-63.97a.25.25 0 0 1-.25-.25V274.38a.48.47 0 0 1 .48-.47h63.28a.65.65 0 0 1 .65.65v41.51Z"/><rect fill="#fff" x="1249.36" y="273.86" width="64.6" height="294.26" rx=".42"/><rect fill="#fff" x="3171.11" y="273.94" width="64.7" height="294.22" rx=".66"/></svg>'


def social(title, desc, path=None):
    """Open Graph and Twitter tags, so a shared link unfurls.

    `og:url` needs a real base to be worth emitting; without one the card
    would point at a domain that does not serve the page.
    """
    out = []
    if desc:
        out.append('<meta name="description" content="%s">' % esc(desc))
        out.append('<meta property="og:description" content="%s">' % esc(desc))
        out.append('<meta name="twitter:description" content="%s">' % esc(desc))
    out.append('<meta property="og:title" content="%s">' % esc(title))
    out.append('<meta name="twitter:title" content="%s">' % esc(title))
    out.append('<meta property="og:type" content="website">')
    out.append('<meta property="og:site_name" content="SignalWire Recipes">')
    out.append('<meta name="twitter:card" content="summary">')
    if BASE and path is not None:
        out.append('<meta property="og:url" content="%s">'
                   % esc(BASE.rstrip("/") + path))
    return "\n".join(out) + "\n"


def page(title, body, favicon_title=None, desc=None, path=None):
    return (
        '<meta charset="utf-8">\n'
        # without this every page renders at 980px on a phone and zooms out,
        # so none of the responsive CSS applies on a real device
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>" + esc(title) + "</title>\n"
        # A prototype host must not become a competing source for a site whose
        # whole point is being retrieved. robots.txt asks; this tells, and it
        # travels with the page if the file is ever missed.
        + ('' if INDEXABLE else
           '<meta name="robots" content="noindex,nofollow">\n')
        + social(title, desc, path)
        + '<meta name="theme-color" content="#0f0f12">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        "family=Instrument+Sans:wght@400;500;600;700&family=Lexend:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&"
        'display=swap">\n'
        "<style>" + CSS + "</style>\n"
        '<a class="skip" href="#main">Skip to content</a>\n'
        '<div id="main">' + body + "</div>"
    )


def badges(r):
    """Public pages carry no internal metadata. Kept as a hook for real facets."""
    return ""



def written_surfaces(r):
    """Only surfaces with code actually on disk. Never advertise an empty one."""
    d = RECIPES / r["slug"]
    return [
        x for x in r.get("surfaces", [])
        if isinstance(x, str) and read_code(d, x, V)
    ]



def used_in(recipes):
    """slug -> [builds that compose it]. Computed, so it cannot go stale."""
    out = {}
    for b in recipes:
        if b.get("kind") != "build":
            continue
        if not b.get("repo"):
            # a build with no repository is a stub; a public page must not
            # claim a pattern is "seen in" something that does not exist yet
            continue
        for slug in b.get("composes", []):
            out.setdefault(slug, []).append(b)
    return out


def category_icon(key):
    """A category's glyph, from its vocabulary file.

    The path lives in vocab/categories/<key>.json so a new category ships its
    own icon without touching this file. A category with no `icon_path` simply
    renders no tile.
    """
    for c in V["categories"]:
        if c["key"] == key and c.get("icon_path"):
            return ('<svg class="fico" viewBox="0 0 640 640" aria-hidden="true" '
                    'focusable="false"><path fill="currentColor" d="%s"/></svg>'
                    % c["icon_path"])
    return ""


def build_index(recipes, body_only=False):
    subs = V.get("subcategories", {})
    cat_of = {r["slug"]: r.get("category") for r in recipes}
    cat_label = {c["key"]: c["label"] for c in V["categories"]}

    builds = [r for r in recipes if r.get("kind") == "build"]
    plain = [r for r in recipes if r.get("kind") != "build"]

    def touches(b):
        """Every category this build's composition reaches. Association, not
        ownership - a build that spans two categories appears in both."""
        out = {cat_of.get(x) for x in b.get("composes", []) if cat_of.get(x)}
        out.add(b.get("category"))
        return {c for c in out if c}

    by_cat = {}
    for b in builds:
        for c in touches(b):
            by_cat.setdefault(c, []).append(b)

    # foundational -> common -> advanced -> alphabetical
    RANK = {"starter": 0, "intermediate": 1, "advanced": 2}

    def rank(r):
        return (RANK.get(r.get("difficulty"), 1), r["slug"])

    def hay(r):
        return " ".join([r["slug"], r["title"], r.get("alias", ""),
                         r.get("summary", ""), r.get("scenario", ""),
                         " ".join(r.get("capabilities", []))]).lower()

    def band(b, ctx=None):
        """ctx names the category we are projecting into, when not its home."""
        home = ctx is None or ctx == b.get("category")
        others = sorted(touches(b) - {ctx}) if ctx else []
        also = ""
        if others and not home:
            also = ('<span class="also">also in %s</span>'
                    % esc(", ".join(cat_label.get(o, o) for o in others)))
        parts = "".join('<span class="part">%s</span>' % esc(x)
                        for x in b.get("composes", [])[:3])
        more = len(b.get("composes", [])) - 3
        if more > 0:
            parts += '<span class="part more">+%d</span>' % more
        planned = b.get("_planned")  # preview --all only
        if planned:
            parts += '<span class="part state">%s</span>' % (
                "no repository yet" if planned == "folder" else "planned")
        return (
            '<a class="buildcard%s"%s data-kind="build" data-slug="%s" data-proj="%d" '
            'data-cat="%s" data-hay="%s"%s>'
            '%s'
            '<span class="bt">%s</span><span class="bs">%s</span>'
            '<span class="parts">%s</span></a>'
            % (" planned" if planned else "",
               "" if planned else ' href="r/%s.html"' % esc(b["slug"]),
               esc(b["slug"]), 0 if home else 1,
               " ".join(sorted(touches(b))), esc(hay(b)),
               ' aria-disabled="true"' if planned else "",
               ('<span class="lab">%s</span>' % also) if also else "",
               esc(b["title"]), esc(b.get("summary", "")), parts)
        )


    def card(r):
        surf = " ".join(SURFACE_ABBR.get(x, x) for x in written_surfaces(r))
        planned = r.get("_planned")  # preview --all only: greyed, not yet written
        if planned:
            surf = "not written yet" if planned == "folder" else "planned"
        return (
            '<a class="card%s" data-kind="recipe"%s data-slug="%s" data-cat="%s" data-hay="%s"%s>'
            '<span class="ct">%s</span><span class="cs">%s</span>'
            '<span class="cd">%s</span>'
            '<span class="cf"><span class="sp"></span><span class="surf">%s</span></span>'
            "</a>"
            % (" planned" if planned else "",
               "" if planned else ' href="r/%s.html"' % esc(r["slug"]),
               esc(r["slug"]), esc(r["category"]), esc(hay(r)),
               ' aria-disabled="true"' if planned else "", esc(r["title"]),
               esc(r.get("alias") or r["slug"]), esc(r.get("summary", "")), esc(surf))
        )

    chips = ('<button type="button" class="chip" data-f="all" aria-pressed="true">All</button>'
    ) + "".join(
        '<button type="button" class="chip" data-f="%s" aria-pressed="false">%s '
        '<span class="cn">%d</span></button>'
        % (c["key"], esc(c["label"]),
           sum(1 for r in plain if r.get("category") == c["key"]))
        for c in V["categories"]
        if any(r.get("category") == c["key"] for r in plain)
    )
    if builds:
        chips += (
            '<button type="button" class="chip kind" data-f="kind:build" '
            'aria-pressed="false">Builds <span class="cn">%d</span></button>'
            % len(builds)
        )

    feat_items = sorted(
        (r for r in recipes if r.get("featured") and r.get("feature_line")),
        key=lambda r: (r.get("feature_rank", 99), r["slug"]),
    )

    def fcard(r):
        planned = r.get("_planned")
        return (
            '<a class="fcard%s"%s data-slug="%s" data-hay="%s"%s>'
            '<span class="ftile">%s</span>'
            '<span class="fl">%s</span>'
            '<span class="fm"><span class="fn">%s</span>'
            '<span class="fc">%s</span></span></a>'
            % (" planned" if planned else "",
               "" if planned else ' href="r/%s.html"' % esc(r["slug"]),
               esc(r["slug"]), esc(hay(r)),
               ' aria-disabled="true"' if planned else "",
               category_icon(r.get("category", "")),
               esc(r["feature_line"]), esc(r["title"]),
               esc("planned" if planned else
                   cat_label.get(r.get("category"), r.get("category", ""))))
        )

    featured = ""
    if feat_items:
        # One flat track. How many fit a page is a runtime question, because
        # it changes with the viewport and with which cards are filtered out,
        # so the dots are built in JS rather than baked here.
        # Arrows flank the cards. The dots and the pause sit up in the
        # heading line, quiet, so the card row stays a card row.
        nav = ('<div class="fnav">'
               '<div class="fdots"></div>'
               '<button type="button" class="fplay" aria-label="Pause featured">'
               '&#10073;&#10073;</button></div>')
        featured = (
            '<section class="feat" id="feat" aria-labelledby="feath">'
            '<div class="feathead"><h2 class="feath" id="feath">Featured</h2>%s</div>'
            '<div class="frow">'
            '<button type="button" class="farrow" data-step="-1" '
            'aria-label="Previous featured">&#8249;</button>'
            '<div class="fviewport"><div class="ftrack">%s</div></div>'
            '<button type="button" class="farrow" data-step="1" '
            'aria-label="Next featured">&#8250;</button>'
            '</div>'
            '<p class="fstatus" role="status" aria-live="polite"></p>'
            '</section>'
            % (nav, "".join(fcard(r) for r in feat_items))
        )

    def group_id(cat_key, group_key):
        """One spelling of a group's id, used by the anchor and its button."""
        return esc("g-%s-%s" % (cat_key, group_key))

    sections = []
    for c in V["categories"]:
        items = [r for r in plain if r.get("category") == c["key"]]
        cb = by_cat.get(c["key"], [])
        if not items and not cb:
            continue

        # task groups, ordered by size so the biggest neighbourhood leads
        groups = {}
        for r in items:
            groups.setdefault(r.get("subcategory", "other"), []).append(r)
        ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))

        tabs = "".join(
            '<button type="button" class="tg" data-g="%s" aria-controls="%s">'
            '%s<span class="cn">%d</span></button>'
            % (esc(k), group_id(c["key"], k),
               esc(subs.get(k, {}).get("label", k)), len(v))
            for k, v in ordered
        )

        blocks = "".join(
            '<div class="tgroup" id="%s" data-g="%s">'
            '<h3 class="tgh" tabindex="-1">%s <span class="cn">%d</span></h3>'
            '<div class="grid">%s</div></div>'
            % (group_id(c["key"], k), esc(k),
               esc(subs.get(k, {}).get("label", k)), len(v),
               "".join(card(r) for r in sorted(v, key=rank)))
            for k, v in ordered
        )

        sections.append(
            '<details class="cat"><summary class="cat-h">'
            '<h2 class="ct2">%s</h2><span class="n">%d</span>'
            '<span class="tgs">%s</span></summary>'
            '<div class="catbody">%s%s</div></details>'
            % (esc(c["label"]), len(items), tabs,
               blocks,
               ('<div class="bsec"><div class="bhead">Builds <span class="cn">%d</span></div>'
                '<div class="bgrid">%s</div></div>'
                % (len(cb), "".join(band(b, c["key"]) for b in cb))) if cb else "")
        )

    hero_cta = ('<a class="btn" href="%s">Browse the repository</a>'
                % esc(repo_url()) if repo_url() else
                '<a class="btn" href="https://signalwire.com/docs">Read the docs</a>')
    body = """<div class="wrap">
<header class="hero">
  <p class="eyebrow">%s<span class="dot"></span>Recipes</p>
  <h1>Working code for every part of a call</h1>
  <p>Clone a folder, add your credentials, and it runs. Most are under two hundred
  lines. The builds show what they look like assembled.</p>
  <div class="cta">%s
  <a class="btn ghost" href="https://signalwire.com/docs">Read the docs</a></div>
</header>
<div class="controls">
  <input id="q" type="search" name="q" autocomplete="off" spellcheck="false"
    placeholder="filter by name, capability, or language&hellip;" aria-label="Filter recipes">
  %s
</div>
%s
%s
<p class="empty" id="none" hidden>Nothing matches that filter.</p>
<p class="hint"><kbd>/</kbd> to search &middot; <kbd>Esc</kbd> to clear</p>
</div>
<script>%s</script>""" % (LOGO, hero_cta, chips, featured,
                          "".join(sections), JS)
    return body if body_only else page(
        "SignalWire Recipes", body,
        desc=("Working code for every part of a call. Clone a folder, add your "
              "credentials, and it runs. Each recipe proves one claim about the "
              "platform, checked against the document the platform receives."),
        path="",
    )



_USED_IN = {}
_TITLES = {}

DETAIL_JS = """
document.querySelectorAll('.stabs').forEach(function(bar){
  var cw=bar.closest('.cw');  // the tab bar sits inside the header, the panes beside it
  bar.addEventListener('click',function(e){
    var t=e.target.closest('.stab'); if(!t) return;
    bar.querySelectorAll('.stab').forEach(function(b){b.setAttribute('aria-selected',b===t?'true':'false');});
    cw.querySelectorAll('pre.src,.fn').forEach(function(p){p.hidden=p.dataset.pane!==t.dataset.pane;});
  });
});
document.querySelectorAll('.cw .copy').forEach(function(b){
  b.addEventListener('click',function(){
    var pre=b.closest('.cw').querySelector('pre.src:not([hidden])'); if(!pre) return;
    var text=pre.textContent, done=function(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy';},1400);};
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done,function(){sel();});}
    else{sel();}
    function sel(){var r=document.createRange();r.selectNodeContents(pre);var g=getSelection();g.removeAllRanges();g.addRange(r);b.textContent='Selected';setTimeout(function(){b.textContent='Copy';},1400);}
  });
});

// --- transcript replay -----------------------------------------------------
// The transcript is the asset no other developer docs have, and it was a
// static wall of text. Replaying it shows the exchange arriving the way it
// does on a call.
//
// Pacing is computed here from the length of each turn rather than stored in
// transcript.json. A transcript is a specimen of what the code does, and a
// stored duration would be a measurement nobody took.
//
// The reveal is opacity, never display. An unrevealed turn stays in the
// layout and in the accessibility tree, so a screen reader has the whole
// transcript whatever the player is doing, and nothing shifts. The button
// ships `hidden disabled` and is unhidden here, so a reader without
// JavaScript is never shown a control that cannot work.
document.querySelectorAll('[data-demo-slot]').forEach(function(slot){
  var btn=slot.querySelector('.trplay');
  var tr=slot.querySelector('.tr');
  if(!btn||!tr) return;
  var turns=[].slice.call(tr.querySelectorAll('.l,.sys'));
  if(!turns.length) return;
  var label=btn.querySelector('.tl');
  var timer=null, at=0;

  // Reading pace, floored so a two-word turn still registers and capped so a
  // long one does not stall. Reduced motion keeps this pace and only drops
  // the animation: collapsing it turned the replay into rapid flashing.
  function delay(el){
    var n=parseInt(el.dataset.n,10)||20;
    return Math.max(320,Math.min(2200,260+n*26));
  }

  function clear(){
    if(timer){clearTimeout(timer);timer=null;}
    turns.forEach(function(t){t.classList.remove('on');t.classList.remove('tip');});
    at=0;
  }

  function stop(){
    clear();
    tr.classList.remove('replay');
    btn.dataset.state='';
    label.textContent='Replay';
    btn.setAttribute('aria-label','Replay the transcript');
  }

  function step(){
    if(at>=turns.length){
      timer=setTimeout(stop,600);   // settle on the full transcript
      return;
    }
    var el=turns[at++];
    turns.forEach(function(t){t.classList.remove('tip');});
    el.classList.add('on');
    if(at<turns.length) el.classList.add('tip');
    timer=setTimeout(step,delay(el));
  }

  function play(){
    clear();
    tr.classList.add('replay');
    btn.dataset.state='playing';
    label.textContent='Stop';
    btn.setAttribute('aria-label','Stop the replay');
    step();
  }

  btn.hidden=false;
  btn.disabled=false;
  btn.setAttribute('aria-label','Replay the transcript');
  btn.addEventListener('click',function(){
    if(btn.dataset.state==='playing') stop(); else play();
  });
  // a replay running in a tab nobody is looking at is just a timer
  document.addEventListener('visibilitychange',function(){
    if(document.hidden&&btn.dataset.state==='playing') stop();
  });
});
""".strip()


def gh_cta(r):
    """The page's primary action, as a button rather than a footnote.

    A build points at its own repository; a recipe points at its folder.
    Neither falls back to a dead anchor.
    """
    target = r.get("repo") or folder_url(r["slug"])
    if not target:
        return ""
    label = "View the repository" if r.get("repo") else "View on GitHub"
    return ('<a class="ghcta" href="%s">'
            '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
            '<path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 '
            '6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37'
            '-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-'
            '.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87'
            '.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2'
            '-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.'
            '09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.'
            '82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0'
            ' 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-'
            '4.42-3.58-8-8-8z"/></svg>'
            '<span>%s</span></a>' % (esc(target), esc(label)))


def build_detail(r, body_only=False):
    d = RECIPES / r["slug"]
    sections = read_sections(d)
    surfaces = written_surfaces(r) or [
        x for x in r.get("surfaces", []) if isinstance(x, str)
    ]
    spec, edata, ehtml = read_evidence(d, V)
    modeinfo = V["demo_modes"].get(r.get("demo", "none"), {})

    demo_blocks = sections.get("What this demonstrates", [])
    demo_paras = prose(demo_blocks)
    claim = demo_paras[0] if demo_paras else esc(r.get("summary", ""))

    out = [
        '<div class="wrap"><div class="detail%s">' % ("" if surfaces else " solo"),
        # Every page carries the mark. The lockup is the home link, which
        # is what a logo is for; the explicit back link stays beside it
        # because this is documentation and people navigate it that way.
        # The mark sits on its own line and the way back sits under it, where
        # a breadcrumb goes. Pushed to the far right it read as detached from
        # both the header and the page.
        '<header class="shead">'
        '<a class="slock" href="../index.html" data-home '
        'aria-label="SignalWire Recipes, back to all recipes">'
        + LOGO + '<span class="dot" aria-hidden="true"></span>'
        '<span class="sname">Recipes</span></a>'
        '<a class="sback" href="../index.html" data-home>&larr; all recipes</a>'
        + gh_cta(r)
        + '</header>',
        '<div class="dh"><h1>%s</h1>' % esc(r["title"]),
    ]
    # One line of identity under the title: what product line this belongs to,
    # then the thing you would actually type, behind the same dot the header
    # lockup uses.
    ident = ['<span class="kcat">%s</span>'
             % esc(CAT_LABEL.get(r.get("category"), ""))]
    if r.get("alias"):
        ident.append('<span class="dot" aria-hidden="true"></span>'
                     '<span class="tech" translate="no">%s</span>' % esc(r["alias"]))
    out.append('<div class="kicker">%s</div>' % "".join(ident))
    out.append('<p class="sub">%s</p>' % esc(r.get("summary", "")))
    # nothing internal on a public page
    meta = "".join(
        '<span class="b">%s</span>' % esc(x) for x in r.get("capabilities", [])[:4]
    )
    out.append('<div class="meta">%s</div></div><div class="drule"></div>' % meta)
    out.append('<div class="dgrid"><div class="dmain">')
    grid_open = len(out) - 1
    out.append('<div class="claim"><h2>The claim</h2><p>%s</p></div>' % claim)

    if ehtml:
        # The panel is a slot. Today it holds a replay of the specimen; a live
        # runtime can occupy the same markup later. `data-demo-mode` says what
        # this recipe would host, so the slot knows what to build.
        replayable = bool(spec.get("replayable"))
        out.append(
            '<div class="ev" data-demo-slot data-demo-mode="%s">'
            '<div class="ev-h"><span class="dot" aria-hidden="true"></span>'
            "Evidence &middot; %s" % (esc(r.get("demo", "none")), esc(spec["label"]))
        )
        if replayable:
            # Rendered disabled and enabled by the script, so a reader without
            # JavaScript is never offered a control that cannot work.
            out.append(
                '<button type="button" class="trplay" hidden disabled '
                'aria-describedby="ev-note-%s">'
                '<span class="ti" aria-hidden="true"></span>'
                '<span class="tl">Replay</span></button>' % esc(r["slug"])
            )
        out.append('</div><div class="ev-b">%s' % ehtml)
        if edata.get("caption"):
            out.append("<cite>%s</cite>" % esc(edata["caption"]))
        if replayable:
            # Only what the page actually does. The demo mode's copy describes
            # a runtime that does not exist yet, and printing it here promises
            # the reader something they cannot do.
            out.append(
                '<p class="evnote" id="ev-note-%s">A specimen of this exchange, '
                'replayed at reading pace.</p>' % esc(r["slug"])
            )
        out.append("</div></div>")

    rest = [b for b in demo_blocks if b != claim]
    if rest:
        out.append('<div class="sec arg"><h2>Why it holds</h2>%s</div>' % blocks_html(rest))

    for h in ("How it works", "Limitations"):
        if h in sections:
            out.append('<div class="sec arg"><h2>%s</h2>%s</div>' % (esc(h), blocks_html(sections[h])))

    code_html = ""
    if surfaces:
        tabs = "".join(
            '<button type="button" role="tab" class="stab" data-pane="%d" aria-selected="%s">'
            '%s</button>'
            % (i, "true" if i == 0 else "false", esc(V["surfaces"][x]["label"]))
            for i, x in enumerate(surfaces)
            if x in V["surfaces"]
        )
        panes, names = [], []
        for i, x in enumerate(surfaces):
            sv = V["surfaces"].get(x, {})
            code = read_code(d, x, V)
            body = highlight_code(code, sv.get("lexer")) if code else esc(
                "# not written yet - recipes/%s/%s/%s" % (r["slug"], x, sv.get("entry", "?")))
            hid = "" if i == 0 else " hidden"
            panes.append('<pre class="src" data-pane="%d"%s translate="no"><code>%s</code></pre>'
                         % (i, hid, body))
            names.append('<span class="fn" data-pane="%d"%s>%s/%s</span>'
                         % (i, hid, esc(x), esc(sv.get("entry", ""))))
        code_html = (
            '<div class="cw"><div class="cwh"><div class="stabs" role="tablist">%s</div>'
            '<div class="cwr">%s<button type="button" class="copy" aria-live="polite">Copy</button></div></div>%s</div>'
            % (tabs, "".join(names), "".join(panes))
        )

        if "Run it" in sections:
            code_html += '<div class="sec proc"><h2>Run it</h2>%s</div>' % blocks_html(sections["Run it"])
        else:
            sv = V["surfaces"].get(surfaces[0], {})
            run = ["git clone &hellip; &amp;&amp; cd %s/%s" % (esc(r["slug"]), esc(surfaces[0])),
                   "cp .env.example .env"]
            if sv.get("install"):
                run.append(esc(sv["install"]))
            if sv.get("run"):
                run.append(esc(sv["run"]))
            code_html += (
                '<div class="sec proc"><h2>Run it</h2><div class="steps">%s</div></div>'
                % "".join('<span class="cl">%s</span>' % x for x in run)
            )
        if "Verify it" in sections:
            code_html += '<div class="sec proc"><h2>Verify it</h2>%s</div>' % blocks_html(sections["Verify it"])

    if "What to change first" in sections:
        out.append('<div class="sec proc"><h2>What to change first</h2>%s</div>'
                   % blocks_html(sections["What to change first"]))
    def link(slug):
        return '<a class="cx" href="%s.html">%s</a>' % (esc(slug), esc(_TITLES.get(slug, slug)))

    # Typed relationships: authored forward edges (recipe -> prerequisite,
    # sibling, next) and the build edges in both directions. One block, so the
    # reader sees where the recipe sits in one glance.
    rels = []
    for key, title in (("prerequisites", "Before this"), ("related", "Related"), ("next", "Next")):
        targets = [x for x in r.get(key, []) if x in _TITLES]
        if targets:
            rels.append(
                '<div class="rel"><h3>%s</h3><div class="cxlist">%s</div></div>'
                % (title, "".join(link(x) for x in targets))
            )
    if r.get("kind") == "build" and r.get("composes"):
        rels.append(
            '<div class="rel"><h3>Recipes this composes</h3><div class="cxlist">%s</div></div>'
            % "".join(link(x) for x in r["composes"])
        )
    for b in _USED_IN.get(r["slug"], []):
        rels.append(
            '<div class="rel"><h3>Seen in a build</h3><p>One of %d recipes composed by %s.</p></div>'
            % (len(b.get("composes", [])), link(b["slug"]))
        )
    if rels:
        out.append('<div class="sec rels"><h2>Where this sits</h2>%s</div>' % "".join(rels))
    # the reading column closes here; the aside holds the code and what to do with it
    if code_html:
        out.append('</div><aside class="dside">%s</aside></div>' % code_html)
    else:
        out[grid_open] = '<div class="dgrid solo"><div class="dmain">'
        out.append('</div></div>')
    # A build points at its own repository; a recipe points at its folder.
    # Neither may fall back to '#': a dead link here is the one control that
    # hands the reader from the page to the code.
    # The GitHub link is a button in the header now. Repeating it here would
    # be two controls with one destination on a single page.
    links = []
    issues = repo_url("issues", "new")
    if issues:
        links.append('<a href="%s">Report an issue</a>' % esc(issues))
    out.append('<div class="dfoot">%s</div></div></div>' % "".join(links))
    if not body_only:
        out.append("<script>%s</script>" % DETAIL_JS)
    body = "".join(out)
    return body if body_only else page(
        r["title"] + " - SignalWire Recipes", body,
        desc=r.get("summary") or "",
        path=recipe_path(r["slug"]),
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
    ]
    # typed relationships, as links a crawler or a model can follow
    for key, title in (("prerequisites", "Prerequisites"), ("related", "Related"),
                       ("next", "Next"), ("composes", "Composes")):
        if r.get(key):
            lines.append(f"- **{title}:** " + ", ".join(
                f"[{_TITLES.get(x, x)}]({BASE}/{x})" for x in r[key]))
    lines += ["", f"Canonical: {BASE}/{r['slug']}", ""]
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


def build_404():
    """Vercel serves this for any unmatched path on a static build."""
    body = (
        '<div class="wrap"><div class="detail solo">'
        '<header class="shead"><a class="slock" href="/" '
        'aria-label="SignalWire Recipes, back to all recipes">'
        + LOGO + '<span class="dot" aria-hidden="true"></span>'
        '<span class="sname">Recipes</span></a></header>'
        '<div class="dh"><h1>No recipe at this address</h1></div>'
        '<div class="drule"></div>'
        '<div class="dmain"><div class="sec arg">'
        '<p>The page you asked for is not here. It may have been renamed, or '
        'it may be one of the recipes still to be written.</p>'
        '<p><a href="/">Browse every recipe</a></p>'
        '</div></div></div></div>'
    )
    return page("Not found - SignalWire Recipes", body)


def build_robots():
    """Open the site to crawlers only when it is the real one.

    While `indexable` is false this disallows everything, because an
    incomplete corpus indexed as the SignalWire recipes source would have to
    be de-indexed later.
    """
    if not INDEXABLE:
        return ("# Prototype host. Set indexable=true in site.config.json when\n"
                "# this becomes the public site.\n"
                "User-agent: *\nDisallow: /\n")
    return "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % BASE


def recipe_path(slug):
    """Where a recipe is actually served, which is where the file is written.

    og:url and the sitemap both read this, so neither can drift from the
    other or from the build. It was /<slug>, a clean-URL layout the site does
    not have, so every advertised URL 404'd.
    """
    return "/r/%s.html" % slug


def build_sitemap(recipes):
    urls = "".join(
        f"<url><loc>{BASE}{recipe_path(r['slug'])}</loc></url>"
        for r in sorted(recipes, key=lambda r: r["slug"])
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{BASE}</loc></url>{urls}</urlset>\n"
    )



def site_config():
    """Where the site points, and how it presents itself to crawlers."""
    f = ROOT / "site.config.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


CFG = site_config()
BASE = CFG.get("base_url") or BASE
INDEXABLE = bool(CFG.get("indexable"))


def repo_url(*parts):
    """A URL into the repository, or None when no repository is configured."""
    base = (CFG.get("repo") or "").rstrip("/")
    if not base:
        return None
    return "/".join([base] + [str(x).strip("/") for x in parts if x])


def folder_url(slug):
    """The recipe's own directory, which is what a reader wants next."""
    return repo_url("tree", CFG.get("branch", "master"), "recipes", slug)


def has_content(r):
    """Showable when someone has actually written it."""
    d = RECIPES / r["slug"]
    readme = d / "README.md"
    if not readme.exists() or "_TODO" in readme.read_text(encoding="utf-8"):
        return False
    if not read_sections(d).get("What this demonstrates"):
        return False
    if r.get("kind") == "build":
        # a build is an application; its artefact is the repo, not a code file
        return bool(r.get("repo") and r.get("composes"))
    for surface in r.get("surfaces", []):
        if isinstance(surface, str) and read_code(d, surface, V):
            return True
    return False


PREVIEW_JS = """
var views = document.querySelectorAll('[data-view]');
var lastY = 0;  // returning to a 121-item index at the top loses your place
var banner = document.querySelector('.pvbanner');
function show(id){
  if (!document.querySelector('[data-view="' + id + '"]')) id = 'index';  // unknown hash: never a blank page
  views.forEach(function(v){ v.hidden = (v.dataset.view !== id); });
  if (banner) banner.hidden = (id !== 'index');  // a preview notice, not part of a recipe page
  if (id === 'index'){
    history.replaceState(null, '', location.pathname);
    window.scrollTo(0, lastY);
  } else {
    history.replaceState(null, '', '#' + id);
    window.scrollTo(0, 0);
  }
}
document.addEventListener('click', function(e){
  // the cards carry a real href to r/<slug>.html; here the detail is inline
  var card = e.target.closest('a.card, a.buildcard');
  if (card && card.dataset.slug){
    var slug = card.dataset.slug;  // slugs are [a-z0-9-]; safe in a selector
    if (document.querySelector('[data-view="' + slug + '"]')){
      e.preventDefault(); lastY = window.scrollY; show(slug); return;
    }
  }
  var back = e.target.closest('[data-home]');
  if (back) { e.preventDefault(); show('index'); }
});
window.addEventListener('hashchange', function(){
  show(location.hash ? location.hash.slice(1) : 'index');
});
document.addEventListener('keydown', function(e){
  var onDetail = document.querySelector('[data-view]:not([hidden])');
  if (e.key === 'Escape' && onDetail && onDetail.dataset.view !== 'index') show('index');
});
show(location.hash ? location.hash.slice(1) : 'index');
"""

PREVIEW_CSS = ""


def build_preview(recipes):
    """One file, index plus every showable recipe, navigable without a server."""
    written = [r for r in recipes if has_content(r)]
    if "--all" in sys.argv:
        # Everything the directory will carry: written folders in full, folders
        # not yet written greyed, and inventory rows with no folder yet greyed
        # further. The public build never sees the synthetic rows.
        live = list(recipes)
        for r in live:
            if not has_content(r):
                r["_planned"] = "folder"
        have = {r["slug"] for r in recipes}
        plan = ROOT / "docs" / "enum" / "inventory.json"
        if plan.exists():
            for row in json.loads(plan.read_text(encoding="utf-8"))["rows"]:
                if row["slug"] in have:
                    continue
                acr = {"pii", "sms", "mms", "otp", "pbx", "ivr", "sip", "dtmf", "mcp", "api",
                       "rtmp", "e911", "10dlc", "crm", "sdk", "ani", "twiml", "pstn", "webrtc",
                       "pubsub", "relay", "ai"}  # no vocab keys here (LEAK guard)
                words = [w.upper() if w in acr else w for w in row["slug"].split("-")]
                words[0] = words[0] if words[0].isupper() else words[0].capitalize()
                live.append({
                    "slug": row["slug"],
                    "title": " ".join(words),
                    "alias": "", "summary": row["claim"], "scenario": "",
                    "category": row["products"][0], "products": row["products"],
                    "subcategory": row.get("task_group") or "other",
                    "capabilities": row.get("capabilities", []), "surfaces": [],
                    "kind": "build" if row["kind"] == "build" else "recipe",
                    "tier": "launch" if row.get("launch") else "next",
                    "featured": bool(row.get("featured")),
                    "feature_line": row.get("feature_line", ""),
                    "feature_rank": row.get("feature_rank", 99),
                    "_surfaces_on_disk": [], "_planned": "planned",
                })
        _TITLES.update({r["slug"]: r["title"] for r in live})
    else:
        live = written
    if not live:
        raise SystemExit("no recipe has content yet - nothing to preview")

    n_planned = sum(1 for r in live if r.get("_planned"))
    parts = [
        '<div class="pvbanner"><div class="pvb"><span class="pvt">'
        "<b>%d</b> of <b>%d</b> recipes are written."
        "</span>"
        '<button type="button" class="pvtog" id="pvtog" aria-pressed="true" '
        'data-n="%d"><span class="pvl">Show %d planned</span></button>'
        "</div></div>" % (len(written), len(live), n_planned, n_planned),
        '<div data-view="index">%s</div>' % build_index(live, body_only=True),
    ]
    for r in live:
        if r.get("_planned"):
            continue
        parts.append(
            '<div data-view="%s" hidden>%s</div>'
            % (esc(r["slug"]), build_detail(r, body_only=True))
        )
    body = "".join(parts) + "<script>%s</script><script>%s</script>" % (DETAIL_JS, PREVIEW_JS)
    html_doc = page("SignalWire Recipes - preview", body)
    return html_doc.replace("</style>", PREVIEW_CSS + "</style>", 1)


def main():
    if not RECIPES.exists():
        print("no recipes/ dir — run scaffold.py first")
        return 1
    recipes = load()
    global _USED_IN, _TITLES
    _USED_IN = used_in(recipes)
    _TITLES = {r["slug"]: r["title"] for r in recipes}
    if "--preview" in sys.argv:
        SITE.mkdir(parents=True, exist_ok=True)
        out = SITE / "preview.html"
        out.write_text(build_preview(recipes), encoding="utf-8")
        live = recipes if "--all" in sys.argv else [
            r for r in recipes if has_content(r)
        ]
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
    (SITE / "robots.txt").write_text(build_robots(), encoding="utf-8")
    (SITE / "404.html").write_text(build_404(), encoding="utf-8")

    launch = sum(1 for r in recipes if r.get("tier") == "launch")
    check_highlighting()
    check_noindex()
    check_advertised_urls()
    print(
        f"build: {len(recipes)} recipes -> site/  "
        f"({launch} launch tier, {len(recipes)*2+3} files)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
