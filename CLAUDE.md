# CLAUDE.md — signalwire-recipes

Guidance for Claude Code working in this directory. **Keep this current.** When a
decision is made here — a protocol, a taxonomy rule, a visual rule — write it
down in this file in the same session it is decided.

## What this is

A **recipes directory**: many small, self-contained, clone-and-run examples on
the SignalWire platform, plus a static generator that turns them into a
browsable, crawlable site. Our answer to `telnyx.com/products/builds`.

Two audiences, in this order:
1. **Answer engines and coding assistants.** A developer asking a model "how do
   I transfer a call without losing context" should retrieve our page.
2. **Developers** who then clone the folder and run it.

## Where things are

This project lives at `C:\Projects\SignalWire\signalwire-recipes` — a peer of the
other projects under the SignalWire workspace root, NOT inside `AI Call Center/`.
It is independent of the call center and must not inherit that project's
CLAUDE.md.

The Agents SDK (3.0.1) is vendored next door and is importable:

```bash
PYTHONPATH="/c/Projects/SignalWire/AI Call Center/signalwire-call-center/ai-agents/signalwire-sdk/signalwire"
```

**Use the absolute path and print `signalwire.__version__, signalwire.__file__`
at the top of every verification run.** This machine has `signalwire-sdk
3.3.0.dev107` in site-packages; a relative `PYTHONPATH` silently falls back to
it after any `cd`, and one "verified against 3.0.1" run was not (2026-08-25).
The published version developers will `pip install` is 3.0.2.

The import is `from signalwire import AgentBase` — **not** `signalwire_agents`,
which is the 0.1.x/1.0.x name; it has no alias in 3.0.1 and seven of the 22
`signalwire-demos` repos still use it (listed in `docs/enum/demos.md` §1) — do
not quote those. The SDK's full surface, with file:line for every claim and an
explicit ABSENT list, is `docs/enum/sdk-surface.md`; §11 there is how to render
SWML and invoke a tool without a network (`agent._render_swml()`,
`agent._execute_swaig_function()`). The JSON key the platform receives is often
not the SDK method name (`update_global_data` → `set_global_data`,
`swml_change_step` → `change_step`) — assert the key, not the method.

## What this is NOT

- **Not the call center.** `../AI Call Center/signalwire-call-center` is a separate product that
  ships clone-and-own. It is a source of patterns and the anchor build, never a
  ready-made corpus — extraction claims must be verified against code.
- **Not a marketing site.** See the visual language section.

## The two kinds, and the test between them

| | Recipe | Build |
|---|---|---|
| Is | one idea, one claim | an application you deploy and operate |
| Size | usually under 200 lines | a repository |
| Field | `prerequisites` / `related` | `composes` |
| Test | "can I state its claim in one sentence?" | "is this a thing you run, not a thing you read?" |

**The test is not how many recipes it touches.** A chat-to-voice handoff draws on
two other recipes and is still one idea with one claim, so it is a RECIPE with
`prerequisites`. The call center is an application, so it is a BUILD with
`composes`. Do not let `composes` become "things this is related to" — that
collapses the distinction and the card contract then serves neither well.

## Taxonomy

- **Categories are SignalWire product lines**: the six the pricing page sells
  verbatim — **AI Agents, Voice, Messaging, MFA, Video, Fax** (decided
  2026-08-25 after sol's round-5 review; evidence `docs/enum/platform-docs.md`
  §A.1). SIP and the Browser SDK are *interfaces*, not product lines: SIP
  recipes live under Voice with `sip`/`byoc` capability tags; browser-only
  voice recipes live under Voice with `browser-sdk` as an interface tag. The
  earlier five (with "Browser & Video" and "SIP") are superseded;
  `vocab/categories/` still carries them until the phase-2 reseed. Never invent
  a parallel axis (an earlier pedagogical taxonomy — "governance", "handoff" as
  categories — was wrong and is gone).
- **The seven planning sections are a lens, not a public axis.** AI Agents &
  Automation · Voice & Call Control · Messaging & Realtime Chat · Video &
  WebRTC · Numbers, Identity & Trust · SIP, PBX & Migration · Fax exist as the
  `lens` column of the inventory and nowhere on the site.
- **Slugs name the mechanism, scenarios are tags.** The slug is the developer's
  search query (`require-verification-before-unlocking-tools`); "bank",
  "drive-thru", "movie showtimes" go in `scenario` and tags, never in the slug.
  One recipe per testable platform claim; a scenario is never a row.
- **Category is derived** from the recipe's declared `products`, not chosen
  independently.
- **Task groups** (`subcategory`) are a required field and the second level:
  Call control, Routing & queueing, Monitoring, Governance, Knowledge, Tools &
  integrations, Handoff, Other. They are cross-cutting — Governance appears
  under Voice as well as AI Agents.
- **Builds project, they do not own.** A build is associated with every category
  its composition touches, marked "also in X" where borrowed, and deduped to its
  home copy when the Builds filter is on.

## Hard rules

1. `recipes/<slug>/recipe.json` is the only metadata source. No central registry.
2. Never hand-edit anything under `site/`. Regenerate.
3. Never write to an author-owned `README.md` from a build step.
4. **One recipe, many surfaces** — language is a subdirectory and a tab, never a
   separate slug. Telnyx emitted `call-forwarding` seven times; that is how 36%
   of their entries ended up with no description.
5. `slug` must equal the directory name.
6. Every recipe needs a real `summary` and a task group. Both are enforced.
7. Public pages carry no internal metadata. `tier`, `provenance` and `governed`
   are planning state and must not render.
8. **Cards carry a real `href` to `r/<slug>.html`** — never a bare `#slug`. The
   public index has no router, so a fragment is a dead click, and it left all 55
   detail pages with zero inbound links, which is fatal for audience #1. The
   preview intercepts that href and swaps the inline `[data-view]`. Planned
   cards get no `href` at all, so they are inert rather than `aria-disabled`.
9. **Every selector the preview JS depends on is a contract.** Three had gone
   stale against a DOM the generator no longer emits (`.row`, `[data-slug]`,
   `[data-home]`) and every failure was silent — the hash changed, the view did
   not. Click a card and click back at the render before calling a change done.
10. **A toggle's knob is an element inside its track**, never a pseudo-element
    pulled into place with negative margins — that landed the knob on the label
    text in the artifact pane (2026-08-25).

## Validation (all of these refuse the build)

- unknown category / surface / evidence type
- **dangling composition edge** — a `composes` entry with no such recipe. Two
  builds shipped with fabricated edges before this existed; the counts were
  counting strings.
- missing task group on a recipe
- `check_extensible.py`: a LEAK guard (no vocabulary literal in generator
  source) and a SYNTH guard (invent a category, surface and recipe; the build
  must render them with zero code changes).

**Adding a required field narrows the "adding a folder" promise.** When you add
one, update the SYNTH fixture too — it is the definition of what a new folder
must contain.

## Visual language

Lifted from the live site (`signalwire.com/products/ai-agent`), not from the
brand cheatsheet's abstractions and not invented:

- ground `#0f0f12`; surfaces `#16161a` / `#1c1c21`. **Neutral, not blue-tinted.**
- Instrument Sans 600 at `-0.04em` / 1.1 for headings; Lexend body; JetBrains
  Mono for identifiers, with `tnum` and slashed zero
- the official logo SVG carries the wordmark — never set the company name as type
- **fuchsia `#F72A72` has exactly four jobs**: primary button, build rail, active
  Builds chip, selected surface tab. If you are reaching for it a fifth time,
  the answer is a neutral.
- **The build rail marks a build that exists.** A 2px fuchsia inset plus a
  brighter cell edge (`--line-2`) on a live build card; a planned build (no
  repository) gets neither, so in a mixed band the real one reads as real and
  the rest read as placeholders. A parallel session retired the rail on all
  builds on 2026-08-25 and moved the colour to a tick under the block; Eric
  reversed that the same day — the cards went flat and AI Call Center looked
  like its planned siblings. The rule under the builds block (`.bsec`) is
  neutral, full width on purpose: it separates two blocks, not two cells.
- turquoise for links and identifiers; no purple anywhere
- no glows, no gradients, no texture — the call center disables its own grain and
  dot-grid deliberately
- labels are sentence-case sans, **not uppercase mono** — weight does hierarchy
- horizontal separators are `border-top` on the card, so a rule stops where the
  cards stop. A `border-bottom` scheme draws a full-width line over cells that
  do not exist.

### Index layout (decided 2026-08-25)

- **Builds sit at the bottom of a category, not the top.** A category is read
  for its recipes; a build is where they end up assembled, so it belongs after
  them. Its separating rule is therefore a `border-top` on `.bsec`, opening the
  block rather than closing it.
- **A featured band sits above the first category**, carrying the standout
  capabilities by their one-line claim ("Two people, two languages, one call.")
  rather than their slug. It is driven entirely by data: `featured`,
  `feature_line` and `feature_rank` on the inventory row, synced to
  `recipe.json` by `scaffold.py`. Adding one is an inventory edit, never a
  generator edit.
- **The band is a front door, not a result.** Any search or category chip
  replaces it. With the unbuilt hidden, its planned cards go and the band stays.
- **Featured cards are `.fcard`, never `.card`.** They duplicate recipes that
  also appear below, so the moment they answer to `.card` the chip counts, the
  category counts and `tools/qc.py`'s own toggle check all inflate by six.
  `tools/qc.py` asserts `.fcard.card` is empty.
- The band **borrows no fuchsia**. That colour already has its four jobs; the
  band earns its place with depth (`--plate`, `--lip`, `--lift`). **`.bsec` is the one deliberate exception**: it separates
  two blocks rather than two cells, so full width is the point.

## Working method

- **Look at the render, not the code.** `playwright-cli` against a local
  `python -m http.server`. Every visual bug this session was found by looking:
  mojibake from an octal escape, a missing `<meta charset>`, a doubled CSS
  selector, unstyled chips, orphaned rules.
- **Design at real volume.** `python build.py --preview --all` renders every
  recipe. A layout that works at 5 items can be wrong at 55.
- **Build public first, preview second.** `python build.py` does
  `shutil.rmtree(site/)`, which deletes `site/preview.html`. Running preview
  first and the public build second silently destroys the artifact you were
  about to publish.
- **Serve from the repo root, not from `site/`.** A server whose cwd is inside
  `site/` holds a Windows lock on the directory, `rmtree` then fails, and it
  surfaces as a bogus `check_extensible.py` failure.
- **Verify replacements took.** `str.replace` fails silently; a "fixed" message
  proves nothing. Assert, then check the output.
- **Anchor deletions.** Cleanup regexes have twice eaten more than intended —
  the content readers (twice) and a nested CSS rule.
- **Heredocs eat backslashes.** For any patch containing them, write a script
  file and run it. This rule was broken twice in one session after being
  written down: a `\\n` inside a quoted heredoc reached the file as a real
  newline and left `tools/qc.py` and `tools/lint_recipes.py` unparseable. If a
  patch string contains a backslash, it goes in a file. No exceptions.
- **One recipe per codex brief.** A five-recipe brief (1,422 lines) killed
  codex three times with no verdict, and it also dies if invited to open SDK
  files mid-review. Splitting to one recipe per brief, with the house rules
  inlined and SDK excursions forbidden, returned a verdict every time. Inline
  what it must not go looking for, including the fact that `requirements.txt`
  and `.env.example` exist but are omitted from the excerpt, or it reports
  their absence as a finding.
- **Give codex a diff, not a tree.** Pointed at the working directory, one
  review spent its entire budget enumerating
  `recipes/create-a-video-room-and-join-from-the-browser/typescript/node_modules`
  and returned no verdict at all. Write `git diff` to a file, name the file in
  the brief, and say explicitly which directories not to open (`node_modules/`,
  `site/`, `.playwright-cli/`).
- **Round-trip a JSON file with the same formatting it had.** Rewriting
  `docs/enum/inventory.json` with `indent=1` and default `ensure_ascii` turned a
  24-line change into a 7,090-line diff and silently escaped a `§` to
  `\\u00a7`. It is `indent=2`, `ensure_ascii=False`, trailing newline.

## Review loop

Plans and output go to **sol via the codex CLI** before they are trusted:
`codex exec --skip-git-repo-check "<prompt>" < /dev/null > log 2>&1`, backgrounded.
Redirect stdin or it hangs waiting on it. Write the brief to a file and point at
the path rather than inlining it.

Write the brief to `docs/_sol_brief_<topic>.md`, log to `docs/_sol_<topic>.log`
(codex echoes every file it reads into the log — the answer is after the last
`codex` marker line, before `tokens used`), and save the answer verbatim as
`docs/<KIND>_REVIEW_<date>.md`.

Six reviews are preserved in `docs/`. Each one killed something real:
extraction estimates that were 2.4x optimistic, an architecture whose central
claim was unprotected, an IA that presented a growing graph as one ordered
list, a blocked list that was stale, and (round 5) five backlog items mapped to
the wrong mechanism plus a five-category taxonomy that contradicted this file's
own rule.

## The list (state as of 2026-08-25)

- `docs/enum/inventory.json` is the single source for the proposed list;
  `docs/enum/render_inventory.py` renders `docs/INVENTORY.md` and **refuses**
  on a duplicate slug, a bad category/task group, a build with a task group, a
  row without evidence, or a backlog ID (#1–#34) that is missing or appears in
  two rows. Edit the JSON, re-render; never edit `INVENTORY.md`.
- `docs/PROPOSED_LIST.md` is the narrative: principle, kinds, taxonomy
  decision, the 34-item verdict (22 Recipe · 6 Merge · 3 Kill · 2 Hold · 1
  Tool), the coverage record, the launch set (19).
- **The live artifact is the site preview, nothing else.**
  `python build.py --preview --all` renders `site/preview.html` in the site's
  own design: written recipes in full, folders not yet written greyed
  ("not written yet"), inventory rows with no folder greyed ("planned"). It is
  published at https://claude.ai/code/artifact/d8f9c247-3e3e-42b3-865a-7ddc8bca878f
  — the page Eric shows his boss and has refined by hand. **Republish that file
  to that URL after every wave; never replace it with a different page.** (A
  separate "progress board" UI was built and reverted on 2026-08-25 for exactly
  that reason.)
- Enumeration outputs live in `docs/enum/` (SDK surface, platform docs, demos,
  Telnyx stems).
- **`docs/` is local-only except `INVENTORY.md`, `enum/inventory.json` and
  `enum/render_inventory.py`** (`.gitignore`; history was purged of the rest
  on 2026-08-25 before the repo was shared). Briefs, reviews, handoffs, the
  marketing inputs and the competitive enumeration exist only on this machine
  — they are not backed up by git. The remote is
  `github.com/ericminessale/signalwire-recipes` (private, default `master`). Marketing's backlog is verbatim in `docs/MARKETING_BACKLOG.md`
  — a resource, not a build order.
- Corpus reality (end of 2026-08-25): 55 folders (51 recipes, 4 builds), the
  20 launch-set recipes written and verified (`python verify.py` → 20/20), 34
  recipe folders still stubs, 3 builds without a repo. Six categories in
  `vocab/categories/`. The four recipes the previous session had written were
  all wrong against 3.0.1 (`signalwire_agents`, `self.result_data`,
  `signalwire.rest.Client`, a bare `connect` action); all four were rewritten.

## Where authority comes from

In this order. Never invent, never infer from a name, never trust prose in a
repo over the code next to it.

1. **The `signalwire-agent-protocol` skill.** Its `references/` are pre-extracted
   and distilled and are the house patterns: `pgi-rules.md` (prompts propose,
   code decides, which is the thesis of every governance recipe),
   `sdk-quick-reference.md`, `best-practices.md`, `common-mistakes.md`,
   `decision-trees.md` (POM vs Contexts/Steps, DataMap vs webhook),
   `voice-tuning.md`, `lessons-learned.md`. Read the relevant ones before
   writing an agent recipe. Its non-negotiables are ours.
2. **The vendored SDK, read as code** (`docs/enum/sdk-surface.md` is the map;
   the source is the authority). A README in that tree is stale by default.
3. **`signalwire.com/docs`, cited by URL** for anything the SDK does not wrap:
   SWML verbs, REST, cXML, Browser SDK, Call Flow Builder. `docs/enum/platform-docs.md`
   is the standing extract. Two OpenAPI specs are vendored in `tools/openapi/`
   and `verifylib.assert_documented()` checks requests against them.
4. **The SignalWire Knowledge MCP** (`mcp__claude_ai_SignalWire_Knowledge__*`),
   when authenticated. Ask Eric to authorise it once per machine; it is the
   company's own knowledge base and outranks a web search.
5. **`signalwire-demos`** for how a pattern is really used
   (`docs/enum/demos.md`). Seven of the 22 repos are on the legacy
   `signalwire_agents` package. Never quote those.

A claim with no entry from this list is not ready to write; mark it
NEEDS VERIFICATION in the inventory and move on.

## Writing

Recipes are engineering writing. The reader is a developer deciding whether the
platform does the thing, and an answer engine deciding whether to cite us.

- **Length**: 230-380 words of prose, median 300, excluding code. If it runs
  longer the recipe is doing two things; split it. If it runs shorter the claim
  is probably unproven.
- **The first paragraph of *What this demonstrates* is the claim.** It renders
  as the claim plate and is the sentence the page is judged on. One idea,
  stated flatly, no throat-clearing.
- **Say the mechanism, not the marketing.** Name the verb, the field, the
  action key. "`record_call` before `connect`, so the bridged leg is inside the
  recording" beats "seamlessly capture your conversations".
- **Prefer the shorter word and the active voice.** Second person. No first
  person plural.
- **`tools/lint_recipes.py` enforces the prose tells mechanically** - em dashes
  first among them, plus delve / leverage / seamless / robust / it's worth
  noting / dive in / not only X but also / whether you're / game-changer and
  the rest. An em dash is a comma, a colon, parentheses, or a full stop; pick
  one. The list grows the first time a tell survives review.
- **Sentences stay under 26 words.** The SignalWire writing guide's cap, and
  the lint counts them. The fix is almost never a comma: a verifier's
  comma-chain of assertions wants to be a short lead plus a bulleted list, and
  a prose run-on wants to be two sentences. 39 sentences were rewritten the day
  the rule went in.
- **The authority is the SignalWire writing guide**, fetched from the Knowledge
  MCP (`get_writing_guide`), not a list I assembled from taste. It is where the
  em-dash ban, the dismissive-language ban (just / simply / easy /
  straightforward) and "do not claim the virtue, demonstrate it" (honest,
  transparent, candid) come from. Re-read it before a wave; fold anything new
  into the lint rather than into a reviewer's head.
- Every claim in the prose is either proven by `verify.py` or attributed to a
  cited doc. No third category.

## Authoring protocol (established 2026-08-25 from 20 recipes taken end-to-end)

A recipe folder is done when **`python verify.py <slug>` passes**, not when it
compiles. The folder contains:

- `recipe.json` — metadata; `plan` holds the planning state (never rendered).
- `README.md` with these `##` sections: *What this demonstrates* (first
  paragraph is the claim the page shows), *How it works* (the mechanism with
  the JSON/YAML the platform receives), *Run it*, *Verify it*, *Limitations*,
  *What to change first*. Fenced code blocks render as code.
- one directory per declared surface (`python/app.py` + `requirements.txt`
  pinning `signalwire-sdk>=3.0.1`; `swml/agent.yaml`; `typescript/index.ts` +
  `package.json` + `tsconfig.json` + committed `package-lock.json`). Declare
  only surfaces that are written — an empty entry file renders as a lie.
- `verify.py` — proves the claim offline in the artifact the platform receives.
  Helpers in `tools/verifylib.py`: `validate_swml()` (SDK schema),
  `Recorder` + `record_everything()` (swap the REST client's HTTP layer),
  `assert_documented(kind, method, path, body, params)` (path, documented
  fields and required fields against `tools/openapi/{rest,compat}.json`),
  `load_yaml`, `verb_names`, `first`. Agents: `agent._render_swml()` and
  `agent._execute_swaig_function()`. **Assert the JSON keys the platform
  receives, never the SDK method names** (`update_global_data` →
  `set_global_data`; `execute_swml(transfer=True)` puts the flag inside the
  document — build the documented sibling `"transfer": "true"` by hand).
  TypeScript is type-checked against the installed `@signalwire/js` when
  `typescript/node_modules` exists; that caught three wrong member names.
- **A verifier must not import its expected values from the recipe.** Sol
  caught `switch-language-mid-call` importing `LANGUAGES` from `app.py` and
  comparing it to the rendered document: swapping both surfaces to unrelated
  languages would still have passed. Expected values live in the verifier, and
  two surfaces are compared against that third thing rather than each other.
- `python verify.py` at the root runs every recipe's verifier with the SDK
  path resolved absolutely (`SIGNALWIRE_SDK_PATH` overrides).

`scaffold.py` seeds folders from `docs/enum/inventory.json` (launch rows by
default, `--all` for everything) and syncs planning fields; it never deletes.
Retiring a folder is a deliberate `git rm`.

## Typed relationships and the detail page (decided 2026-08-25)

- Three **authored** forward edges on a recipe: `prerequisites` (run these
  first), `related` (siblings), `next` (where to go after). Builds keep
  `composes`. Reverse edges are computed: recipe→build ("Seen in a build") only
  from builds that have a `repo`. Dangling or self edges refuse the build.
  Never generate neighbour lists — Telnyx's alphabetical "related" is the
  anti-pattern.
- They render as one block, **Where this sits**, at the end of the detail page,
  and as link lines in the `.md` for answer engines.
- Detail page rules from the visual pass: labels are sentence-case sans
  (`The claim`, `Evidence · …`), footer links turquoise, fenced README code in
  `pre.mdcode`, every written surface in its own pane with working tabs, README
  *Run it* replaces the generated steps when present, *Verify it* renders after
  the code. Look at `site/r/<slug>.html` through `python -m http.server` and
  `playwright-cli` before calling a change done.
## Recipe page design (pass of 2026-08-25)

The page is **an argument with an exhibit**: a claim, the evidence it is true,
and the code that does it. Depth carries the hierarchy, so the design spends no
new colour and fuchsia keeps its four jobs. **One depth channel per element,
never reused** — this is the rule, because flatness is caused by the count of
identical frames, not by their quality (7 boxes once shared one background,
one border value and zero shadows; 7 headings were byte-identical).

| element | treatment | why |
|---|---|---|
| the claim | turquoise wash 4.5% / border 19% / `inset 2px 0 0` keyline + a top-lit plate | the one thing the page asserts, and the only tinted object |
| the transcript | **not a box**: no fill, no border, an 18px turquoise keyline, mono | evidence is quoted, not framed; it is the asset no other developer docs have |
| the code | a window: `#131316` chrome over a `#0a0a0c` well, `--line-2` border, restrained lift | the artifact |
| commands | a terminal: well fill, turquoise keyline, no card | you type into it |
| illustrative code in prose | 2.5% white, hairline left rule, no radius, muted | quieter than both |
| relationships | border-top only | navigation, lowest weight |

- **Borders are a ladder**: `--line` .11 inside a panel, `--line-2` .17 around
  one, `--line-3` .24 for an edge being pointed at. 8% white on this ground is
  below the threshold where a border reads as a border — one weak channel looks
  like a failed attempt. Radius is a scale too: `--r-lg` 10 / `--r-md` 6 /
  `--r-sm` 3, never one value for a 700px window and a 24px chip.
- **Turquoise ranks by strength**: the claim's keyline is full, evidence .42,
  commands .48. The signal colour ranks things rather than merely marking them.
- **Two heading tiers** matching the two kinds of section: argument sections
  (Why it holds / How it works / Limitations) open on a `border-top` and run
  21px; procedure sections (Run it / Verify it / What to change first) are
  13.5px and quiet. **A rule that trails out of a heading, and little square
  bullet markers, are the generated-design tell** — sol named both; a
  structural `border-top` says the same thing and is the house separator.
- Layout: *Run it* and *Verify it* sit under the code they belong to; *Where
  this sits* closes the reading column so it ends on a terminus. A page with no
  code (a build) is **one centred 900px column**, never a 2fr strip against an
  empty 3fr.
- Research: `docs/enum/design-research.md` (~30 dark dev-doc sites, values read
  from served CSS). Review: `docs/DESIGN_REVIEW_2026-08-25.md`. Two research
  recommendations were refused: a *fuchsia* claim wash (fuchsia's four jobs are
  spent) and a sticky section index (all sticky is banned after one covered
  three sections).

## Web Interface Guidelines

Vercel's guidelines (the `web-design-guidelines` skill, fetched live) are part
of the QC gate for anything that changes markup. The audit of 2026-08-25 found
one thing worth more than the rest: **the site had no `<meta name="viewport">`
at all**, so every page rendered at 980px on a phone and none of the responsive
CSS ever applied — invisible for weeks because the artifact wrapper injects its
own viewport tag and nobody opened the site on a phone. Also fixed: `theme-color`
did not match the page, no skip link, no `translate="no"` on code and
identifiers (Chrome auto-translate garbles them), the Copy result was not
announced, decorative dots were not `aria-hidden`, the index skipped h2,
`fonts.gstatic.com` was not preconnected, `#q` used `outline:none`, focused
cards could sit under the sticky filter strip, 113 cards had no
`content-visibility`, and prose carried straight quotes and `...`.

- **The recipe page uses the index's 1180px frame, not a 760px reading
  column.** A centred 760px column left 60% of a 1920px screen empty (Eric,
  2026-08-25). From 1080px up it is two columns — claim, evidence and prose on
  the left; the code panes sticky on the right with Run it / Verify it / What to
  change first under them — so the prose sits beside the code it describes.
  Below 1080px it is one column filling the frame. Header and *Where this sits*
  span the frame. **Check every layout change at 1920, 1280 and 820** — the
  artifact pane is ~800px and Eric's monitor is 4K; a render that looks right
  at 1280 alone proves nothing.
- `[hidden]{display:none!important}` is in the reset because author `display`
  rules on `.card` beat the UA's `[hidden]`; the filters and the unbuilt toggle
  set the attribute and were hiding nothing. Counting attributes is not looking.
- **The code block** is highlighted at build time with Pygments; the lexer name
  is the `lexer` field of `vocab/surfaces/<x>.json` (python, typescript, yaml),
  never a literal in the generator. Header: language tabs left, `surface/entry`
  file name and a Copy button right; one `pre.src[data-pane]` per written
  surface. The tab script finds panes with `bar.closest('.cw')` — a wrapper
  inserted between the tabs and the panes once broke switching while the tab
  label and file name still changed, so **a tab test asserts the visible pane's
  text**, not the label. Palette is restrained: weight and the two greys do
  most of it, strings in a desaturated turquoise, comments recede, no purple.
  Copy uses the clipboard API and falls back to selecting the pane (the
  artifact iframe may refuse the API).
- The preview banner is a preview notice: shown on the index only, hidden on
  every recipe page.
- **The frame is 1560px, not 1180.** 1180 was a strip on a 4K monitor and left
  the code pane 80 characters wide, so a normal Python line grew a horizontal
  scrollbar (Eric caught it; the clipped line was visible in the 1920 render
  and was let through). At 1560 the pane is 860px and fits the longest recipe
  line (114ch) at 1920 with no scrollbar; below 1244px the viewport decides. The
  recipe page splits 2fr/3fr, code on the larger side. **Recipe code lines stay
  at or under 90 characters** — at 1280 the pane holds 91 (sol measured it; a
  100-character rule left one overflow, a 92 rule was one too permissive).
  `tools/qc.py`'s overflow check is the authority, not the count.
  README fenced code (`pre.mdcode`) is illustrative and wraps; it never
  scrolls. A scrollbar at the bottom of a code block is a layout bug, not a
  code-block feature.
- **A sticky element must have nothing below it in its own column.** The code
  block was made sticky with *Run it / Verify it / What to change first* beneath
  it; scrolled down, it painted over all three and they could not be read
  (Eric, 2026-08-25). Those sections live in the reading column; the aside is
  the code alone.

## QC gate — before any publish or commit that touches build.py

1. `python tools/lint_recipes.py && python build.py && python check_extensible.py && python verify.py`
   The lint is the authoring protocol made mechanical: required README sections,
   the prose tells, line length, `load_dotenv()` where the environment is read,
   no `signalwire_agents`, a `verify.py` per recipe. Every rule in it is a
   mistake that shipped once. **All 20 recipes shipped without `load_dotenv()`
   while pinning `python-dotenv`** - the README said `cp .env.example .env` and
   the app never read it, so every credentialed recipe failed from a clean
   clone. The verifiers missed it because they set the environment in-process.
   The same shape recurred with **basic auth**: an `AgentBase` serves its SWML
   behind it, and with no `SWML_BASIC_AUTH_USER` / `SWML_BASIC_AUTH_PASSWORD`
   the SDK invents a password that exists only in the running process, so the
   number's webhook 401s and the password changes on restart. The SDK prints
   the warning on startup; it was read and not acted on. Seven recipes shipped
   that way before sol caught it. The lint now refuses an `AgentBase` recipe
   whose `.env.example` omits them, and `verifylib.assert_basic_auth_from_env()`
   asserts the credentials came from the environment rather than being
   generated.
2. `python build.py --preview --all && python tools/qc.py` — the render QC:
   overflow, sticky overlap at six scroll offsets, card click and back with
   exactly one view visible, the unbuilt toggle by *painted* count with its
   switch element surviving and the category-header strips following, tab
   switching by pane *text*, banner placement — at 2560, 1920, 1280×720 (a
   laptop) and 820. It refuses on any failure. Every check in it is a bug that
   shipped because someone looked at a screenshot of the top of a page, or at
   an attribute, instead of using the page. `docs/UI_REVIEW_2026-08-25.md` is
   the first codex pass over this; it found two P1s the QC and the author both
   missed (the toggle deleting its own knob, stale header counts) and named the
   QC's blind spots, all now fixed or covered. Two of its fuchsia findings were
   *not* taken: `::selection` and focus outlines stay fuchsia as system
   affordances, and the hero eyebrow is Eric's design; hover states and the
   toggle's on-state went neutral.
3. **codex review of the diff** (`docs/_sol_brief_ui_<date>.md` → `codex exec`,
   answer saved under `docs/`) for anything that changes what a reader sees.
   Two sessions in one day published UI that was broken on first click; a
   second pair of eyes is not optional for the artifact Eric shows his boss.
4. Only then republish the artifact.

## Platform facts learned the hard way

These cost a review round each. They are not in any single doc.

- **A step is not a security boundary.** `valid_steps` shapes the `next_step`
  tool the model is offered, and `set_step_criteria()` is a sentence the model
  judges; the runtime advances on criteria (which is why
  `set_skip_to_next_step` exists to bypass them). Neither keeps a caller out of
  the next step. **The tool that acts is what checks**, and it checks
  `global_data` from `raw_data`, not its position in the flow. Two governance
  recipes claimed otherwise before sol caught it.
- **`connect` owns the bridge until the far leg ends.** Any verb after it runs
  only once the call is over. A `send_digits` after `connect` fires at nobody;
  DTMF for an external tree goes in `dial`'s `send_digits` parameter, sent
  after the call is answered. The same trap made a `live_translate` claim wrong.
- **`play` auto-answers** (`auto_answer`, default true), so `answer` is about
  *when* the call is picked up, not a prerequisite for audio.
- **`enable_mcp_server()` is broken** in 3.0.1 and 3.3.0.dev107:
  `mcp_server_mixin.py` reads `self._swaig_functions`, but tools live in
  `self._tool_registry._swaig_functions`, so `tools/list` returns `[]` and
  `tools/call` returns -32602. The row is on hold.
- **The chat-mode AI kernel is unreleased** (Knowledge MCP `get_doc('mary')`
  lists it under "Unreleased but functioning" and on the two-quarter roadmap).
  Both chat rows are on hold; chat is *not* the cheap path to an interactive
  demo.
- `prompt_value` holds a prompt's collected digits or utterance;
  `prompt_result` is the status enum (`match_digits`, `match_speech`,
  `no_input`). `detect_result` is lowercase `machine` / `human` / `fax` /
  `unknown` / `detecting` / `error`.
- **The bundled schema requires `play` to be an object** with a `url`. The
  `play: "say:..."` shorthand in the docs does not validate locally.
- **`join_conference` narrows two fields more than they look.** `beep` is one
  of `true` / `false` / `onEnter` / `onExit`, and `status_callback_event` takes
  a **single** event name, not a space-separated list. A list is the natural
  thing to write and fails schema validation.
- **`FunctionResult` helpers omit fields already at their schema default**, so
  an absent key is the assertion. `end_on_exit=False` never appears in the
  emitted document. Assert `"key" not in verb`, not `verb.get(key, default)`,
  which passes either way.
- **`add_skill` silently drops a duplicate instance.** The instance key is
  `SKILL_NAME + "_" + params["tool_name"]`, so adding one skill twice without
  distinct `tool_name` values keeps only the first. A warning in the log, no
  error, and one tool where you expected two. A multi-instance skill must also
  name its tool from `tool_name`, or the two instances collide.
- **`languages_enabled` gates the `languages` list.** Without it the platform
  ignores the list and answers in the first voice. Nothing errors.
- **Matching an utterance is substring-unsafe.** "yesterday" contains "yes"
  and "I can't say yes" contains it too. Normalise the whole answer (expand
  contractions before dropping apostrophes, strip politeness but never hedges
  like "perhaps") and compare against a set.

## Open work

- 34 launch-adjacent stubs still have folders with empty entry files (they
  render as "not written yet"); the 60 `proposed` inventory rows have no
  folder. Write them through the protocol above, launch set first
  (`docs/INVENTORY.md`).
- Three stub builds (`voice-support-line`, `sms-support-desk`,
  `governed-intake-agent`) need repositories or retirement; `ai-call-center`'s
  `composes` must be re-verified against its code.
- The nine NEEDS VERIFICATION rows in `docs/INVENTORY.md`.
- **Chat is absent from the corpus and stays absent for now.** It looked like
  the cheapest path to an interactive demo, but the chat-mode AI kernel is
  unreleased (see *Platform facts learned the hard way*), so both chat rows are
  on hold. Do not plan around it until it ships.
- The enumeration pass is done (`docs/enum/`); the remaining coverage debt is
  the nine NEEDS VERIFICATION rows listed at the end of `docs/INVENTORY.md`.
  sol round 6 (`docs/LIST_REVIEW_2026-08-25_round6.md`) cleared the list for
  phase 2.
