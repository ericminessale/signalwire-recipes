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
- turquoise for links and identifiers; no purple anywhere
- no glows, no gradients, no texture — the call center disables its own grain and
  dot-grid deliberately
- labels are sentence-case sans, **not uppercase mono** — weight does hierarchy
- horizontal separators are `border-top` on the card, so a rule stops where the
  cards stop. A `border-bottom` scheme draws a full-width line over cells that
  do not exist.

## Working method

- **Look at the render, not the code.** `playwright-cli` against a local
  `python -m http.server`. Every visual bug this session was found by looking:
  mojibake from an octal escape, a missing `<meta charset>`, a doubled CSS
  selector, unstyled chips, orphaned rules.
- **Design at real volume.** `python build.py --preview --all` renders every
  recipe. A layout that works at 5 items can be wrong at 55.
- **Verify replacements took.** `str.replace` fails silently; a "fixed" message
  proves nothing. Assert, then check the output.
- **Anchor deletions.** Cleanup regexes have twice eaten more than intended —
  the content readers (twice) and a nested CSS rule.
- **Heredocs eat backslashes.** For any patch containing them, write a script
  file and run it.

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
  Telnyx stems). Marketing's backlog is verbatim in `docs/MARKETING_BACKLOG.md`
  — a resource, not a build order.
- Corpus reality (end of 2026-08-25): 55 folders (51 recipes, 4 builds), the
  20 launch-set recipes written and verified (`python verify.py` → 20/20), 34
  recipe folders still stubs, 3 builds without a repo. Six categories in
  `vocab/categories/`. The four recipes the previous session had written were
  all wrong against 3.0.1 (`signalwire_agents`, `self.result_data`,
  `signalwire.rest.Client`, a bare `connect` action); all four were rewritten.

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

## Open work

- 34 launch-adjacent stubs still have folders with empty entry files (they
  render as "not written yet"); the 60 `proposed` inventory rows have no
  folder. Write them through the protocol above, launch set first
  (`docs/INVENTORY.md`).
- Three stub builds (`voice-support-line`, `sms-support-desk`,
  `governed-intake-agent`) need repositories or retirement; `ai-call-center`'s
  `composes` must be re-verified against its code.
- The nine NEEDS VERIFICATION rows in `docs/INVENTORY.md`.
- **Chat is absent from the corpus** and is the cheapest path to an interactive
  demo: text in, text out, no WebRTC, no PSTN, no media stack. Voice
  interactivity needs a runtime service and belongs behind it.
- The enumeration pass is done (`docs/enum/`); the remaining coverage debt is
  the nine NEEDS VERIFICATION rows listed at the end of `docs/INVENTORY.md`.
  sol round 6 (`docs/LIST_REVIEW_2026-08-25_round6.md`) cleared the list for
  phase 2.
