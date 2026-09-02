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
  the answer is a neutral, or one of the other two signals below.
- **Two accents, not three (decided 2026-08-26).** Fuchsia `#F72A72` acts and
  marks builds; periwinkle `--accent #8B96FF` navigates and `--select-rgb`
  `#6E7BFF` selects. The page had fuchsia, SignalWire blue `#044EF4` and
  turquoise `#40E0D0` in its first three coloured elements - hues 340 / 222 /
  176, almost evenly spaced, which is the least cohesive arrangement three hues
  can take. Eric: "the sequential change from fuchsia to blue to cyan does not
  work visually. they are not cohesive." Warm against one cool now carries the
  contrast, and selection sharing navigation's hue is honest, since "where am
  I" and "where can I go" are the same question.
- **The SignalWire brand colour rules are not binding in this project.** Eric
  released it explicitly (2026-08-26): "the brand guidelines color wise from
  signalwire knowledge mcp are not a rule we have to follow in this project if
  its a limiting factor." They were the reason blue and turquoise were locked
  to their jobs, and that lock is what produced the incoherent triad. Consult
  `get_design('colors')`, then decide; do not treat it as a constraint.
- **Every accent job reads `--accent` / `--accent-rgb` / `--select-rgb`.** The
  `--turquoise` token was deleted rather than redefined, because a token named
  for a colour it no longer holds is a trap. A palette change is one edit.
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

### Index interaction (decided 2026-08-26)

- **A control that looks like navigation must navigate.** The task-group strip
  in each category header was grey text carrying counts, sitting where
  navigation sits, doing nothing. They are `<button>`s now: they open their
  category, scroll to the group and move focus to its heading. `tools/qc.py`
  fails the build if one is not a button, does not open its category, or points
  at a group that does not exist.
- **The featured band is a carousel**, three up at 1101px+, two at 761px+, one
  below. The track is **one flat list of cards**, not pre-baked pages: the
  script computes how many fit, sets `--per`, and rebuilds the dots, so paging
  follows the viewport and skips cards a filter has hidden.
- **Auto-advance carries obligations.** It pauses on hover, on focus within, on
  a hidden tab, under `prefers-reduced-motion`, and on a persistent
  pause/resume button. `start()` checks all of them in one place, because the
  first version restarted the timer from the arrow handlers while the pointer
  was still inside.
- **Offscreen cards leave the accessibility tree**, with `inert` and
  `aria-hidden`, not just `tabindex="-1"`. Tab order is not the only way in.
- **The featured band has no container.** A plate holding recessed cards is one
  frame inside another, and Eric read it as "very containerized/boxy"
  (2026-08-26). The band is the page now; the *cards* are the raised objects
  (gradient plus `--lip`/`--lift`), and because the category rows below are flat
  on `--page`, that elevation is what makes the row read first. The arrows moved
  out of the heading into `.frow` and flank the cards; dots and pause stay in the
  heading line so the card row stays a card row. Do not re-introduce the plate.
- **A rule trailing out of a heading is the generated-design tell** - already the
  rule for the recipe page, and `.feathead::after` was breaking it on the index.
  With the plate gone, the `.controls` border-bottom is the one separator the
  band needs. Two lines for one boundary is one too many.
- **Category icons live in `vocab/categories/<key>.json`** as `icon` and
  `icon_path`, never in `build.py`. The LEAK guard caught the first attempt
  within a minute of writing it, which is exactly its job: a new category ships
  its own glyph and the generator does not change. Icons come from the
  SignalWire library via the Knowledge MCP's `get_icons` (Font Awesome Pro
  7.2.0, `viewBox="0 0 640 640"`, `fill="currentColor"`), never from memory -
  SVG path data is not something to recall.
- **The icons are one accent, not six.** Eric floated per-category colour.
  `get_design('colors')` is explicit: blue `#044EF4` and fuchsia are **fills
  only, never text on dark**, and turquoise on dark is the sanctioned accent
  text. This page already spends blue on selection and fuchsia on builds, so a
  third and fourth hue would break "three signals, three meanings". The glyph
  *shape* differentiates and the tile gives the card a focal point. Per-category
  colour is still open if Eric wants it, but it has to arrive as filled tiles,
  not coloured glyphs.
- **A resize is not a page change, so it must not animate.** Calling `go()` from
  a resize handler retargeted a live `transform` transition on every event and
  the cards lagged behind the window being dragged (sol, 2026-08-26). `place()`
  drops the transition, jumps, flushes with `offsetWidth`, and restores it, and
  the handler is batched through one `requestAnimationFrame`.
- **A control may shrink at touch widths; its hit box may not.** The arrows
  paint at 32px under 760px and carry 6px of `content-box` padding with
  `background-clip:content-box`, so the target measures 46px and the circle
  still looks 32. Measured, not assumed.
- **Never collapse a slot with `display:none` to hide an optional ornament.**
  `.ftile:empty{display:none}` took the 34px and the gap with it, which would
  drop an iconless card's claim ~48px above its neighbours and undo the shared
  baseline. It is `visibility:hidden`.
- Round-2 review is `docs/UI_REVIEW_2026-08-26_featured.md`. Its P1 (arrows
  visible while `hidden`) was **refused**: `build.py:71` already carries
  `[hidden]{display:none!important}`, and a measurement confirmed
  `display:none` and a zero-width rect. Its turquoise finding was **taken in
  part**: the tile fill went neutral, the glyph kept the accent, because the
  design system's answer for turquoise on dark is "read this first" and a fully
  grey icon returns the flatness the pass exists to fix.

- **A divider between two chips sits at the midpoint of the gap.** The Builds
  divider was `left:-8px` against 22px of space (an 8px flex gap plus a 14px
  margin), so it hugged Builds and read as belonging to it (Eric, 2026-08-26).
  It is `-11px`. Measure the two rects and assert the midpoint; do not eyeball a
  negative offset.
- **Measure ink, not boxes.** The Builds divider was moved to the midpoint of
  the two chips' *bounding boxes* and Eric still read it as wrong, because the
  preceding chip has a transparent border and paints nothing over its 14px of
  padding: 25.7px from one chip's text, 11px from the other's border. Measured
  ink to ink (a `Range` over the chip's contents) the midpoint is `-18px`.
  A `getBoundingClientRect()` is not what a reader sees. `tools/qc.py` now
  asserts the two distances agree within 3px.
- **Look at the render with the browser, not only with a headless script.**
  Eric asked "are you not using that mcp that can properly view the render?"
  after two wrong divider fixes. The Chrome MCP's `zoom` on a 130px region
  showed the skew in one look; the numbers I had been printing hid it because
  I was measuring the wrong quantity. Zoom into the detail under discussion.
- **The carousel arrows are bare chevrons, not buttons in rings.** A circle
  around a control that already sits beside carded content is a container
  around a container (Eric, 2026-08-26). White glyph, no border, no background,
  transparent `content-box` padding for the 46px hit box, scaling into the
  accent on hover and focus, and a 420ms `.pulse` whenever the cards move so
  the control reads as the thing that moved them.
- **An interaction outranks a signal.** `.farrow.pulse` and the hover rule were
  equally specific, so an auto-advance pulse arriving under the pointer shrank
  the arrow from 1.45 to 1.35 and grew it back 420ms later (sol). The pulse is
  scoped `:not(:hover):not(:focus-visible)`.
- **A divider needs two things to divide.** When the chip strip wraps and
  Builds starts a row, the rule to its left has nothing on the other side, so
  `.chip.kind.wrapped::before{content:none}` removes it. The class is set by a
  **`ResizeObserver`, not a resize listener batched through `requestAnimationFrame`** -
  rAF does not run while the tab is hidden, so a window resized in the
  background left the divider stale until the next resize.
- **`tools/qc.py` runs a phone width (390x844) as of 2026-08-26.** It had four
  viewports and none was a phone, which is why the wrapped chip strip had never
  been exercised despite the viewport meta tag being fixed weeks earlier.
- **The no-overflow rule for code panes applies at 820 and up, not below.** At
  390px the pane is 324px, about 37 characters, and no real code line fits; the
  web guidelines call for wide content to scroll inside its own `overflow-x`
  container, which is what it does. What must hold at *every* width is that the
  **page** never scrolls sideways, and `qc.py` now asserts that separately.
- **A sabotage that changes nothing proves nothing.** The sidescroll guard was
  first "tested" by forcing `.dhead` - a class the page does not use - and the
  QC passed, which read as a broken guard. Check that the sabotage actually
  reaches the DOM before concluding anything about the check.
- **Pass a direction, never derive it from a modular delta.** The pulse chose
  its arrow with `(at-from+pages)%pages`, which cannot tell forward from back
  when `pages===2` - and six featured cards at three up is exactly two pages,
  so Previous lit Next in the common case. Callers know which way they went.
- **Never position a slide with `offsetLeft`.** Transforming the track makes it
  the cards' `offsetParent`, so `card.offsetLeft` changes coordinate space the
  moment the transform is applied and paging freezes after one step. Compute
  from the viewport width plus the gap.
- **`element.style.setProperty` ignores a Number.** `setProperty('--per', 3)`
  does nothing; it needs `String(3)`. The cards kept the stylesheet's width
  while the script paged a different number of them, and nothing errored.

### Index layout (decided 2026-08-25)

- **Builds sit at the bottom of a category, not the top.** A category is read
  for its recipes; a build is where they end up assembled, so it belongs after
  them.
- **`.bsec` has no rule of its own (revised 2026-08-27).** It used to carry a
  full-width `border-top`, which put two lines 29px apart around one boundary:
  that rule, then the hairline the `Builds` heading already trails like every
  task group in the category. Eric caught the pair and preferred keeping the
  heading's. The block still reads as different, because its cards are wider
  and carry the build rail. The earlier note calling the full-width rule
  deliberate is superseded.
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
  band earns its place with depth (`--plate`, `--lip`, `--lift`).

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

## The repository as a destination (decided 2026-08-26)

The site's whole job is to hand a reader to a folder they clone, so the repo is
the destination and had never been designed as one. Eric asked for it.

- **`README.md` is the front door.** It had none at all: a visitor arriving from
  a recipe page landed on a bare directory listing.
- **`recipes/README.md` is generated** by `tools/gen_index.py`, so the index
  cannot drift from the folders. It reuses `build.has_content()`, so "written"
  means there exactly what it means on the site. `--check` fails when stale and
  is part of the gate. It is not author-owned, and says so in its first line.
- **`CONTRIBUTING.md` is the authoring protocol for outsiders.** It carries the
  three verifier rules, the `load_dotenv` and basic-auth traps, and the gate.
- **The lint now covers `README.md` and `CONTRIBUTING.md`.** Holding 55 recipe
  READMEs to the writing guide while leaving the front door unchecked made no
  sense. It caught "declare the products honestly" on the first run.
- **Folders stay flat.** Eric floated `recipes/ai/<slug>/`. Category is
  *derived* from `products`, so a directory level would duplicate a fact that
  can then drift; slugs are globally unique and are the search query; and
  `composes` / `prerequisites` / `related` all reference bare slugs, so nesting
  breaks the graph and every URL. A categorised index gives the navigation
  without the coupling.
- **`site.config.json` holds the repo URL and branch**, not `build.py`, so
  moving to the SignalWire org is one edit outside the generator.
- **Every recipe page links to its own folder.** The footer's two links were
  `href="#"` on all 51 recipe pages: `repo` is only set on builds, so the
  fallback was a dead anchor, and "Report an issue" was hardcoded to `#`. The
  hero's "Browse the repository" was a `<button>` with no handler. This is the
  card-href rule again on a different element, so **`tools/qc.py` now refuses
  any `href="#"` anywhere in the document**, hidden panes included.
- **`design/` is untracked.** It held abandoned exploration artboards from an
  early session; the visual language came from the live site instead. The local
  files are kept, `git rm --cached` only.
- **MIT, `Copyright (c) 2026 SignalWire`** (Eric approved it 2026-08-26). The
  text is the vendored SDK's own LICENSE with the year changed, because every
  SignalWire repository on this machine carries that same file and wording.
  Do not hand-type a licence; copy the house one.

## The demo slot and transcript replay (decided 2026-08-26)

- **The artifact cannot host a live demo.** Its CSP blocks fetch, XHR and
  WebSockets to every external host, so click-to-call with a real media stream
  cannot run in the page Eric shows his boss. On real hosting it also needs a
  token-minting backend. Eric chose replay over live for that reason; do not
  re-propose a live demo for the artifact.
- **The demo scaffolding was 90% dead.** `demo` is set on all 55 recipes and
  `vocab/demo-modes/` defines five modes, but the affordance rendered only
  inside `if ehtml:`, so 27 of the 30 written interactive recipes showed
  nothing, and the 3 that did showed **a disabled button reading "Runtime not
  built yet"**. A control that admits it does not work is worse than no
  control on a page that exists to prove the platform is real. It is gone.
- **The evidence panel is a slot**: `[data-demo-slot][data-demo-mode=...]`. A
  live runtime can occupy the same markup later. sol asked for the slot to be
  emitted for the 27 recipes with no evidence; **refused**, because a mount
  point with nothing to mount renders an empty panel and the runtime cannot
  exist yet. Those 27 need transcripts first.
- **The transcript replays.** Turns arrive at reading pace, and a note lands
  at the moment it explains. **Pacing is computed in the browser from each
  turn's character count, never stored in `transcript.json`** - a transcript is
  a specimen of what the code does, and a stored duration would be a
  measurement nobody took.
- **Reveal with `opacity`, never `display` or `visibility`.** An element at
  zero opacity stays in the accessibility tree and is still read; `display:none`
  removes it. The first version hid turns with `display`, so pressing Replay
  made most of the transcript vanish for a screen reader (sol P1). Opacity also
  reserves the block's height, so nothing shifts.
- **The whole transcript is painted at rest, before any interaction.** The
  primary audience is an answer engine. `tools/qc.py` asserts it with
  `checkVisibility({checkOpacity:true})`, which walks ancestors;
  `getComputedStyle(el).display` is reported happily by a child of a hidden
  parent and proves nothing.
- **"Painted" and "in the accessibility tree" are different questions.** The QC
  asks the first with `checkOpacity:true` and the second with
  `checkOpacity:false`. Conflating them makes one of the two assertions vacuous.
- **A control that needs JavaScript ships `hidden disabled`** and is unhidden by
  the script, so it is never offered to a reader who cannot use it.
- **Reduced motion keeps the pace and drops the animation.** Collapsing the
  delay to 90ms turned a nine-turn replay into nine flashes in under a second,
  which is worse than the motion it avoided (sol P2).
- **A `::after` on a grid row becomes a third column.** The replay caret is on
  the turn's text span, not on `.l`, which is `display:grid`; on the row it
  wrapped to its own line. It rides a `.tip` class rather than being a moved
  node, so it cannot be orphaned or left mid-list.
- **`replayable` is a field of `vocab/evidence/*.json`.** The LEAK guard
  rejected `spec.get("renderer") == "transcript"` in generator source, which is
  its job: a new evidence type declares its own capabilities.
- **A QC check on the preview must scope to the visible pane.** The preview
  inlines every recipe, so `document.querySelector('[data-demo-slot]')` read a
  different and hidden recipe's transcript than the slug under test, and
  reported 6 turns for a 9-turn page. Scope to
  `[data-view]:not([hidden])`. **A missing feature must fail, not skip**:
  `REPLAY_SLUGS` names the slugs that must have a player.
- **A synthetic event does not exercise a guarded handler.** The
  `visibilitychange` test dispatched the event while the tab was visible, so
  the handler's `document.hidden` guard correctly did nothing and the test was
  asserting nothing. Redefine `document.hidden` before dispatching.
- Review: `docs/UI_REVIEW_2026-08-26_replay.md`.

**Next wave: evidence coverage.** Only 3 of the 30 written interactive recipes
carry a `transcript.json`, and the transcript is the asset no other developer
docs have. A transcript is evidence, so it must be derivable from the code it
sits beside; a plausible-looking conversation the code would never produce is a
fabricated record, not a specimen.

## Deployment (decided 2026-08-26)

- **This is a prototype host, not a launch.** Eric, 2026-08-26: "the proposal
  is not to deploy publically on vercel, just get away from the limitations of
  an artifact." Vercel runs it on his work account
  (`eric.minessale@signalwire.com`, `ericminessale` GitHub linked). The repo
  stays private and where it is; moving it to the `signalwire` org is a
  separate, later decision.
- **What escaping the artifact actually buys.** The CSP is only the visible
  limit. The bigger one is that the artifact is a single inlined
  `preview.html`, so `sitemap.xml`, `llms.txt`, per-recipe URLs and anything
  about retrieval cannot be exercised at all - and retrieval is audience #1.
  A real host also allows a real phone and a future token endpoint.
- **Vercel over GitHub Pages because of serverless functions.** A live in-page
  demo needs an endpoint that mints Browser SDK tokens, and Pages is static
  only. The demo slot on each recipe page exists to take that runtime.
- **The artifact stays the thing Eric shows his boss** until he says otherwise.
  Vercel is additive. Keep republishing the artifact after every wave.
- **`indexable` is false, and going public is that one boolean.** A prototype
  carrying 43 of 121 recipes, indexed as *the* SignalWire recipes source before
  the real one exists, becomes a competing result that has to be de-indexed
  later. While it is false every page carries
  `<meta name="robots" content="noindex,nofollow">` and `robots.txt` disallows
  everything; `build.py` walks the written files and **refuses** if a page
  escaped without the tag, because one path that skips `page()` would ship
  indexable in silence.
- **`BASE` was hardcoded to `https://signalwire.com/recipes`** and now comes
  from `site.config.json`. On a preview host the sitemap was advertising 56
  URLs that all 404.
- **The deploy builds; it does not serve committed files.** `site/` is
  gitignored. `vercel.json` runs
  `python3 -m pip install -r requirements.txt && python3 build.py` and serves
  `site/`. Use `python3`, not `python`: the build image is Node-first.
- **The gate belongs in CI, not in the deploy build.** `.github/workflows/gate.yml`
  has two jobs: `gate` (lint, index freshness, build, extensibility, verify) and
  `render` (the browser checks, which need Playwright and are slower). Until
  this existed nothing enforced the gate except someone remembering to run it.
- **CI installs `signalwire-sdk==3.0.1` from PyPI**, and `verify.py` wants the
  directory *containing* the package on `SIGNALWIRE_SDK_PATH`. Locally that is
  the vendored checkout; on a runner it is `sysconfig.get_paths()["purelib"]`.
  The vendored layout is `signalwire-sdk/signalwire/signalwire/`, which is why
  the local path ends one level above the package.
- **`requirements.txt` is the tooling, not the recipes**: Pygments and PyYAML.
  Each recipe pins its own dependencies. The render checks additionally need
  `playwright-cli`, which is npm rather than pip.

## The SDK pin (decided 2026-08-26)

- **Recipes pin `signalwire-sdk==3.0.1` exactly, never a range.** They pinned
  `>=3.0.1` while PyPI serves 3.4.0, so a developer cloning today got 3.4.0
  while every verifier asserts 3.0.1 behaviour. This repo has already lost a
  session to that shape of drift, where a newer SDK on the path shadowed the
  vendored one and a run reported "verified" against a version it never loaded.
- **Moving off the pin is a deliberate wave**: bump, run all 42 verifiers, fix
  what broke, commit. `tools/lint_recipes.py` refuses a range (`SDK_PIN`).
- **A silent fallback for a missing dependency is a deployment hazard.**
  `highlight_code()` caught every exception and returned escaped text, so a
  machine without Pygments built the whole site unhighlighted and said nothing.
  It counts its fallbacks now and refuses when none succeeded, which is the
  signature of an absent dependency rather than an odd lexer. The fallback for
  a genuinely unknown lexer stays.

## Colour and the design pass (decided 2026-08-27)

- **The brand guidelines are not a constraint here, and neither is a table I
  invent to replace them.** Eric released the project from `get_design` and
  then had to say it twice, because after his first correction I went back to
  the MCP and produced a fresh rigid assignment. The failure both times was
  the same shape: one prescriptive lock table.
- **The fault was exclusivity, not the hue.** Eric: "this branding is not
  reading signalwire at all... the fuchsia is nowhere to be seen. maybe in
  combination with variety it would work but you cant just use this purple."
  One token owned the claim, the identifier, the category dot, the evidence
  keyline and dot, the speaker labels, the replay control and the footer links,
  while code strings were a hardcoded turquoise fighting all of it. Nearly
  every fuchsia rule was on the index, so a recipe page had one small fuchsia
  tab underline against roughly 29 periwinkle jobs.
- **An alpha below about .1 is not a colour, it is a rumour.** The first
  attempt gave the claim a fuchsia wash at `.05` and borders at `.2`, which
  paint as nothing on this ground. Eric, looking at the render: "theres no
  fuchsia. like ltierally none. one tiny line." He was exactly right, and a
  measurement confirmed it: four fuchsia declarations on the whole reading
  column, all on `.claim`, three invisible, leaving a single 2px inset line.
  **Count what is painted, do not trust that a rule was written.**
- **The no-alpha rule is about surfaces, not every element.** Eric's rule came
  from a claim plate: a large fuchsia wash on this ground composites to a dull
  violet. Applying it to everything carrying the fuchsia triple swept up two
  small controls that were fine, and made both worse. The active Builds chip
  went from a tint with fuchsia text to a solid fuchsia block, far louder than
  a filter state should be and out of parity with the category chips.
  `::selection` went solid when it is conventionally translucent so the text
  reads through. Eric: "my issue was with containers and stuff not buttons."
  A small control may carry a tint as a state; a surface may not. The SOLID
  guard names its exceptions, so adding one is a decision rather than a habit.
- **Fuchsia is never painted at partial opacity on a surface.** Eric's rule,
  2026-08-27: "never use fuchsia in low opacity. you used it in this 'the
  claim section' as a see through background which just turns it into an ugly
  purple. its exclusively for solid colors." `#F72A72` over this ground at a
  low alpha composites to a dull violet, so a translucent fuchsia is not a
  softer fuchsia, it is a different and worse colour. **`check_extensible.py`
  has a fourth guard, SOLID**, which refuses any `rgba()` carrying the fuchsia
  triple below alpha 1. Six had accumulated before anyone said so, because
  each one looks reasonable while you are writing it.
- **One object, one accent.** The claim plate was given a periwinkle wash and
  a solid fuchsia keyline, as a neat illustration of the register split. Eric:
  "no one said to mix perrywinkle and fuchsia that looks bad." He is right, and
  nobody asked for it. The claim is periwinkle throughout. A rule that is
  elegant to explain is not thereby good to look at.
- **The two registers divide by material, across objects and not inside one.**
  Fuchsia is solid marks: a rule, a keyline, a dot, a fill. Periwinkle is
  tinted surfaces, where alpha is the point and the composite stays true.
- **Fuchsia gets the structure, not the decoration.** The rule under the
  header, the claim plate at an alpha that paints (`.11` fill, `.5` border,
  3px keyline), and the `border-top` that opens every argument section, so it
  recurs down the column. Procedure sections keep a neutral rule, so the
  existing two-tier hierarchy is what carries the colour.
- **Three registers, doing different work.** Fuchsia carries the claim, the
  category dot and the active tab, and it leads because the claim is the
  largest object on the page. Turquoise carries identifiers, code, commands
  and links: the things you type. Periwinkle carries the evidence and its
  replay. That is variety with the brand in front, not a tint.
- **Measure a colour rule before believing it.** A gold rule for code
  operators was added, looked plausible, and rendered *grey*: a later, more
  specific rule won. It was deleted rather than fought for, because a fourth
  colour the page did not need is exactly the vibe-coded addition this pass
  existed to remove.

### Sharing a link (added 2026-08-27)

- **Every page carries its own `description` and Open Graph tags.** There were
  none, so a URL pasted into Slack, Teams or an email unfurled as a bare link.
  A recipe's description is its `summary`, so each of the 55 links describes
  that recipe rather than the site.
- **`og:url` is emitted only when `indexable` is true.** `base_url` is where
  the site will live, not where a prototype host serves it, and a card
  pointing at a page that 404s is worse than a card without a URL.
- **`site/404.html`** exists; Vercel serves it for any unmatched path on a
  static build with no configuration.
- **There is no `og:image` yet.** A card renders on title and description
  alone. Generating one needs either a raster written at build time or
  `@vercel/og`, which is a Node function and would put npm in a repo that has
  none. Worth doing before any public launch, not before a private share.

### The header persists (decided 2026-08-27)

- **Every recipe page carries the SignalWire mark.** It was on the index and
  nowhere else: all 55 recipe pages had no brand mark at all, only a muted
  "all recipes" link. That was more of why a recipe page did not read as
  SignalWire than any accent colour was. A page with no logo is not branded,
  whatever its palette does. Eric asked for it directly.
- **The logo is a `LOGO` constant**, not a second inlined copy. It was pasted
  into the index hero; the hero now substitutes it like any other value.
- **The header is present, not sticky.** A sticky element on this page has
  painted over three sections before, and "persist on sub pages" is about
  presence rather than following the scroll.
- The lockup is the home link, because that is what a logo is for, and the
  explicit `all recipes` link stays beside it because this is documentation
  and people navigate it that way. Both carry `data-home`, so view switching
  in the single-file preview still works.

### The frontend stack, for the record

Plain HTML from a single-file Python generator. No framework, no bundler, no
npm for the site: `build.py` holds the CSS and JS as string constants and
writes `site/`. Pygments highlights at build time, PyYAML reads the swml
surface, and the only external request a page makes is Google Fonts.
`playwright-cli` is npm but it is the test harness, not the site. **The
frontend design skills assume React, Next, Tailwind and Motion throughout, so
only their audit protocol and AI-tell list transfer here.**

### Text contrast (fixed 2026-08-27)

- **The prose scale sits a step higher than it did.** Eric: "the meat and
  potatoes text is like hard to read cuz you made it grey on grey." Measuring
  agreed and went further. Body prose was `#8b8b96` at 5.68:1, technically AA
  but reading as grey on grey, and the step below it, `#63636e` at **3.23:1**,
  **failed AA outright** while carrying Run it, Verify it, every caption, the
  capability tags and the transcript speaker labels. `--fg-muted` is `#adadb8`
  and `--fg-subtle` is `#8b8b96`, so body prose is now 8.61:1.
- **`tools/qc.py` sweeps every text node for WCAG AA.** It composites
  translucent backgrounds against their ancestors and applies the large-text
  exemption, rather than assuming one page background. Nothing in the gate had
  an opinion about contrast before, which is why it drifted until someone
  squinted. On the old palette it catches 23 failing runs across a page.

### The design skills, and what they caught

- **Radius was a scale on paper and fifteen values in practice.** `--r-sm` 3 /
  `--r-md` 6 / `--r-lg` 10 were documented and then bypassed by raw `2px`,
  `3px`, `4px`, `6px`, `7px` and `8px`. Mixed radii are what separate a page
  that looks designed from one that looks assembled. Now nine values remain,
  all tokens, shapes (`50%`, `999px`) or zero, and **`check_extensible.py`
  has a third guard, SCALE**, that refuses a raw pixel radius.
- **`IntersectionObserver` cannot drive a scroll reveal safely.** It fires on
  threshold crossings, so a section that passes the viewport between two
  frames goes from ratio 0 below to ratio 0 above without ever crossing one.
  No callback arrives, and it stays at `opacity:0` permanently. A fast scroll
  stranded three sections; a `boundingClientRect.top < 0` check inside the
  callback does not help, because the callback is what never runs. **Use
  `animation-timeline: view()`**: it is a function of scroll position, holds
  its end state past the range, needs no JavaScript, and degrades to a fully
  visible page where unsupported. It also deleted about forty lines.
- **An entrance animation that can hide content is worse than none.** Verify a
  reveal by jumping the scroll, not by scrolling smoothly past it.

## QC gate — before any publish or commit that touches build.py

1. `python tools/lint_recipes.py && python tools/gen_index.py --check && python build.py && python check_extensible.py && python verify.py`
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
- **`enter_queue.transfer_after_bridge` is a string, not a boolean.** It holds
  a URL or inline SWML, and `"false"` is how you say "carry on in this
  document". A real boolean fails schema validation. It is also required.
- **`connect` takes a `confirm`**, run on the answering leg before the bridge
  completes, as a URL or inline SWML. That is the whisper-before-handoff
  mechanism. `FunctionResult.connect()` does not expose it, so build the verb
  and hand it over with `execute_swml`.
- **`add_mcp_server()` emits a key the bundled schema rejects.**
  `ai.SWAIG.mcp_servers` appears nowhere in 3.0.1's `schema.json`, whose SWAIG
  object sets `unevaluatedProperties: {not: {}}`, so a document configured that
  way fails `validate_swml()`. Unlike `enable_mcp_server()` the config does
  render; the recipe is on hold because it cannot be proven offline.
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

## Wave 1 of the fill-out (2026-09-01)

Interactive demos are paused; the priority is filling out the corpus without
phoning it in (Eric, 2026-09-01). Five recipes went end to end this wave, each
through verify, lint and two rounds of sol. Facts that cost a round:

- **`FunctionFillers` is a oneOf of single-language objects.** A `fillers` dict
  with two language keys fails `validate_swml`. One language per tool filler;
  language-wide pools go through `add_language(speech_fillers=,
  function_fillers=)`. Passing only one of the two writes the deprecated
  `fillers` key instead.
- **`wait_file` and `wait_file_loops` validate** on a SWAIG function and are
  emitted by `wait_file=`/`wait_file_loops=` on the tool decorator. A wait file
  the recipe does not serve is a claim the recipe cannot make, so it is
  optional via `WAIT_FILE_URL` and the verifier renders both ways.
- **`switch_context(system_prompt=...)` alone emits a bare string.** The schema
  documents `context_switch` as an object; pass `consolidate` or `full_reset`
  to get the object form. The wire key is `context_switch`, not the method name.
- **`gather_info` is absent from the 3.0.1 schema**, so a recipe cannot prove
  it offline. Ordered steps use contexts and steps with `set_functions` on
  every step, because a step without `functions` inherits the previous set.
- **The context builder's ValueError is swallowed at render.** A `valid_steps`
  entry naming a step that does not exist raises from
  `agent._contexts_builder.validate()`, but `_render_swml()` catches it, logs
  it, and fails on a missing `prompt` instead. Assert both, because the second
  is what a developer sees.
- **A per-call token is checked only when present.** The `/swaig` route checks
  basic auth first and validates `__token` only if the query carries one, so
  a client that strips the token bypasses the check. The recipe adds a FastAPI
  middleware on `agent.get_app()` that 403s a tool POST with no token, and the
  verifier drives the real app with `TestClient`, not the handler. `serve()`
  reuses the cached app, so the middleware is live.
- **`ReceptionistAgent` takes `voice` as a constructor argument** (default
  `rime.spore`); `SurveyAgent` has none. Do not write "changing the voice means
  subclassing" about a prefab without reading its `__init__`.
- **Substring asserts on a prefab's response are tautologies in waiting.**
  `"valid" in response` accepts "invalid". Compare the exact string.
- **`token_expiry_secs` defaults to 3600, not 900.** A README said fifteen
  minutes was the SDK default; `AgentBase.__init__` says an hour. Read the
  signature before stating a default. There is no `secret_key` argument on
  `AgentBase` either: the `SessionManager` is built with only the expiry, so
  replicas cannot share a signing key without subclassing.
- **A key check is not a value check.** `"__token" not in query_params` let
  `?__token=` through, and the SDK treats an empty token as absent, so the
  guard the recipe exists to add had a hole shaped exactly like the SDK's.
  Test `not params.get(key)`, and the verifier posts both the missing and the
  empty form.
- **The SDK's render-time error is capturable.** `_render_swml()` logs the
  swallowed ContextBuilder error through structlog as `ai_verb_config_error`;
  `structlog.testing.capture_logs()` returns it as a dict, so a verifier can
  assert the log line names the bad step and the raised
  `SchemaValidationError` says `Missing required field 'prompt'`. Redirecting
  stdout/stderr or a `logging` handler sees nothing.
- **`SurveyAgent` fills a missing rating `scale` with 5** and raises
  `ValueError` only for a multiple choice without `options` or an unknown
  type. A README claimed it raised for both; the verifier now asserts what it
  does.
- **Two redundant assertions are one assertion.** Exact adjacency
  (`valid_steps == [next]`) already rules out backward and skip edges; a
  second loop asserting those cannot fail once the first passes. Sol reads a
  verifier for what can fail, not for what it mentions.
- **Prose length ran 420-520 words this wave**, above the 230-380 guidance,
  because each *Verify it* carries a bulleted list of assertions and each
  *Run it* now carries the tunnel sentence. Sol did not object; the guidance
  stands as a target, not a gate, and a recipe that needs the words to state
  its proof keeps them.

## Wave 2 of the fill-out (2026-09-02)

Five more: text-the-caller-during-the-call, write-a-disposition-from-handler-
owned-data, stream-agent-debug-events, try-destinations-in-order and
configure-an-agent-per-request. Facts that would have cost a round:

- **An `AgentBase` root is registered only at `/route/`.** `include_router`
  with a prefix turns `@router.get("/")` into `/front-desk/`, and the app is
  built with `redirect_slashes=False`. `/front-desk` falls to a catch-all in
  `web_mixin.py` that returns `None`, so the platform gets `200 null` and no
  document. 33 READMEs said "point the webhook at `.../front-desk`" and every
  one was wrong for an agent. `SWMLService.serve()` has its own catch-all that
  handles the exact route, so plain SWML recipes were fine, but all URLs now
  carry the slash and the lint refuses one without it.
- **The verifier drives routes with `TestClient(agent.get_app())` and
  `agent.route + "/"`.** The SDK's webhook URLs (`post_prompt_url`,
  `debug_webhook_url`) end in a slash too; compare with `rstrip("/")`.
- **`_render_swml()` and the routes call the dynamic-config callback on an
  ephemeral copy** (`_create_ephemeral_copy`, deep-copies prompt, languages,
  params, global_data). The deployed agent is unchanged after a request, which
  the verifier proves by rendering it afterwards. The tool registry is not
  copied, so per-request tools would leak; the recipe does not do that.
- **The post-prompt POST carries `global_data`** when `action` is
  `post_conversation` (docs: ai-post-prompt-callback). `on_summary(summary,
  raw_data)` gets `post_prompt_data.parsed[0]`, or `raw` when parsed is
  empty, and the whole body. Drive it with a POST to `/route/post_prompt`
  behind basic auth; the response is `{"success": true}`.
- **Debug events:** `enable_debug_events(level)` writes
  `params.debug_webhook_url` (this agent's `/debug_events`) and
  `debug_webhook_level` at render. The route is POST only, basic auth, reads
  `label` or `action`, and calls the `on_debug_event` handler with
  `(event_type, body)`.
- **`caller_id_num` is in the SWAIG tool POST body** (docs:
  ai-swaig-tool-webhook), so a handler can text the caller without the model
  ever holding a number. `FunctionResult.send_sms` builds a one-verb SWML
  document and hands it to `execute_swml`, so the action key is `SWML`.
- **`connect` is a oneOf of four shapes**: single `to`, `serial`, `parallel`,
  `serial_parallel`. `result.case` switches on `connect_result`, which is
  `connected` or `failed` (docs: swml/reference/connect), and runs once the
  peer leg has ended.
- **Sol will ask for a citation on the `.env.example` basic-auth comment
  every time.** It is house boilerplate the lint requires, not a recipe
  claim. State that in the brief's platform facts rather than editing five
  copies of the same sentence.
- **Sol's date is a day behind this machine's** (it reported 2026-09-02
  verification stamps as future-dated). Say the date in the brief.
- **Heredocs ate a backslash again** (a `\` line continuation inside a quoted
  Python string) while patching a verifier. The Edit tool, or a script file
  written with Write, for anything containing one.

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
