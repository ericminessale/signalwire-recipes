# CLAUDE.md — signalwire-recipes

Guidance for Claude Code working in this directory.

## What this is

A **recipes directory**: many small, self-contained, clone-and-run examples on the
SignalWire platform, plus a static generator that turns them into a browsable,
crawlable site. Answer to Telnyx's `telnyx.com/products/builds`.

Two audiences, in this order:
1. **Answer engines and coding assistants.** A developer asking a model "how do I
   transfer a call without losing context" should retrieve our page.
2. **Developers** who then clone the folder and run it.

## What this is NOT

- **Not the call center.** `../signalwire-call-center` is a separate product that
  ships clone-and-own. Never add recipes-directory concerns to it, and never
  import from it.
- **Not a monolith.** A recipe that needs much more than ~200 lines of application
  code is probably two recipes.
- **Not a marketing site.** See the skill-routing rule below.

## Layout

```
signalwire-recipes/
  recipes.json          # seed list — the human-reviewable master list
  scaffold.py           # recipes.json -> recipes/<slug>/   (idempotent, never overwrites)
  build.py              # recipes/*/recipe.json -> site/    (globs; no registry)
  recipes/<slug>/
    recipe.json         # THE manifest. Only metadata source for this recipe.
    README.md           # author-owned prose
    .env.example
    python/ typescript/ swml/    # surfaces are SUBDIRS of one recipe
  site/                 # GENERATED — gitignored, never hand-edited
```

## Commands

```bash
python scaffold.py    # seed folders from recipes.json (safe to re-run)
python build.py       # regenerate site/ from the folders
```

## Hard rules

1. **`recipes/<slug>/recipe.json` is the only metadata source.** Do not add a
   central registry. `build.py` discovers by globbing, which is why there is no
   registry to drift.
2. **Never hand-edit anything under `site/`**, including `llms.txt` and
   `sitemap.xml`. Regenerate.
3. **Never rewrite an author-owned `README.md` from a build step.** Generated
   headers go into build output only.
4. **One recipe, many surfaces — never one recipe per language.** Language is a
   subdirectory and a tab on the page, not a separate slug. Telnyx emitted
   `call-forwarding` seven times; that is how they got 36% of entries with no
   description, and seven thin pages cannibalise one keyword.
5. **`slug` must equal the directory name.** `build.py` warns on mismatch.
6. **Every recipe needs a real `summary`.** An empty or placeholder summary is the
   single failure mode that made Telnyx's corpus look padded.

## Naming convention

Capability-first, dual-field. This is deliberate and was argued over — do not
drift back to scenario names like `holyguacamole` or `bobbystable`.

| Field | Job | Example |
|---|---|---|
| `slug` | search intent, URL | `whisper-to-an-agent-mid-call` |
| `title` | plain-language H1 | "Whisper to an agent mid-call" |
| `alias` | the technical term devs also search | `join_conference coach=` |
| `summary` | what it does, outcome-first | "One-way audio that only the agent's leg can hear." |
| `scenario` | the flavour / the demo you hear | "Coaching without the caller knowing" |

Do **not** apply a blanket "no SDK names" lint. Developers search for `tap`,
`post_prompt`, `live_translate`, `ai_sidecar`. Plain language goes in `title`,
the jargon goes in `alias`. Both are indexed.

## Provenance vocabulary — and the honesty rule

`provenance` in the manifest is a claim about cost, and it gets read as a
commitment. Values:

- `extract` — genuinely liftable from existing code into <200 lines
- `narrow` — the primitive is small, but the shipped product behaviour is bigger;
  the recipe must promise only the primitive
- `rewrite` — a capability exists somewhere but the recipe is new authorship
- `new` — nothing exists
- `blocked` — has an unresolved platform or policy dependency
- `demos` — a version exists in the `signalwire-demos` org

**Verify `extract` against code, never against prose.** A plan review on
2026-08-24 downgraded 26 claimed extractions to 11 clean, 3 narrowed, 7 rewrites
and 5 kills. The repo next door demonstrates why: its `ARCHITECTURE.md` documents
`/sales` and `/support` routes that 404, and its `CLAUDE.md` says install SDK
`0.1.55` while `ai-agents/requirements.txt` pins `signalwire-sdk>=3.0.1,<4`.
Feature docs describe intent; only code and a passing test describe behaviour.

## Corrections that already cost us — do not re-derive

- **`step_criteria` is not hard control.** Step advancement is model-evaluated.
  The real enforcement is per-step `set_functions` allowlists plus handlers that
  validate and force transitions. Never write "a step machine the agent cannot
  skip."
- **The call-center test harness is not a demo runtime.** `testing/run_scenario.py`
  places real PSTN calls from project-owned numbers, permits one run at a time
  because number binding is exclusive, runs up to 240s, and its synthetic agent
  leg is silent. A public gallery runner is new work.
- **Colocated manifests do not make drift impossible.** They reduce merge
  contention and clarify ownership. Drift still happens between manifest, README,
  entrypoints, and generated output — so validate, don't assert.
- **Live demo cost is not just PSTN.** WebRTC removes termination cost, not
  STT/LLM/TTS/translation. Any runtime needs atomic global admission, spend
  ceilings, per-leg bounds on duration *and* turns *and* tool calls, a
  least-privilege demo project, and server-side destination allowlists.
- **The `ai_sidecar` copilot tier is not shippable yet** — unverified suggestion
  stream, unresolved stop contract, broken mid-call mode switches, and it
  competes with live transcription for one transcriber slot.

## Competitive framing

Telnyx **co-locates** AI beside telephony; SignalWire **embeds** the AI kernel in
the media pipeline. Co-location reduces hops, embedding eliminates them for the
orchestration layer. Never write that Telnyx "bolts AI on from outside" — they
are a licensed carrier with a FreeSWITCH fork and their own TTS, and that framing
will not survive a technical reader.

## Skill routing — read before any UI work

Several installed skills all advertise "use me for UI" and auto-selection is
unreliable. For this project:

| Surface | Use | Do not use |
|---|---|---|
| The gallery shell / index | `minimalist-skill` | `taste-skill` |
| In-page demo widgets, dense panels | `minimalist-skill` | `taste-skill` |
| Accessibility / semantics audit | `web-design-guidelines` | — |
| Screenshot-and-iterate loop | `playwright-cli` | — |
| Long code generation | `output-skill` | — |

`taste-skill` is a marketing-site tool. Its rules — hero minimalism, "reduce
micro-UI clutter" — are actively wrong here, because on a dense technical index
and inside a live demo panel **the clutter is the product**. This page has no
hero and should not acquire one.

Register to aim for: Linear, Sentry, Vercel, Supabase. Dense rows, mono for
identifiers, keyboard navigation, semantic state colour.

`playwright-cli video-start` with `video-show-actions` annotates each action on a
recording — useful for generating demo clips from the same tool that tests the page.

## Known gaps

- `scaffold.py` writes **empty** surface files. A naive "surface exists" CI check
  would pass on an empty `app.py`. Validate in a clean environment using the
  declared dependency file and run command, not file existence or syntax alone.
- No `DESIGN.md` yet. That is the layer that keeps many recipe pages consistent.
- Detail pages carry a placeholder where the live demo goes, and a generated
  placeholder for "What this demonstrates". Both need per-recipe authorship.
- No CI. Gates still to write: manifest schema + version, slug/dirname match,
  summary length, clean-env surface validation, secret scan, generated-output
  staleness, immutable IDs with slug aliases for renames.

## Environment

Windows, PowerShell primary, Bash available. `core.autocrlf=true` on this machine
with mixed line endings in sibling repos — if this becomes a git repo, check
`git diff --numstat` against `--ignore-space-at-eol` before believing a
whole-file rewrite.
