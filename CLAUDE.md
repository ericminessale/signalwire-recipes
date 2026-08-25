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

## What this is NOT

- **Not the call center.** `../signalwire-call-center` is a separate product that
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

- **Categories are SignalWire product lines**: AI Agents, Voice, Messaging,
  Browser & Video, SIP. They mirror what the company sells. Never invent a
  parallel axis (an earlier pedagogical taxonomy — "governance", "handoff" as
  categories — was wrong and is gone).
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

Three reviews are preserved in `docs/`. Each one killed something real:
extraction estimates that were 2.4x optimistic, an architecture whose central
claim was unprotected, and an IA that presented a growing graph as one ordered
list.

## Open work

- **Protocol for authoring a new recipe** — to be established from one recipe
  taken genuinely end-to-end, not written in advance.
- **Typed relationships** (`prerequisites`, `related`, `next`) are specified here
  but not implemented. Recipe→build, recipe→prerequisite and build→composed
  navigation should be designed once, together.
- The **detail page** has not had the visual pass the index has.
- **Chat is absent from the corpus** and is the cheapest path to an interactive
  demo: text in, text out, no WebRTC, no PSTN, no media stack. Voice
  interactivity needs a runtime service and belongs behind it.
- The seed list needs an enumeration pass (SDK surface, FEATURES.md, the 22
  demos in `signalwire-demos`, Telnyx's stems as a coverage checklist) rather
  than a recall pass.
