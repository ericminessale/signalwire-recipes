# How the site is made

One Python script, `build.py`, reads the recipe folders and a small vocabulary
and writes a static site into `site/`. There is no framework, no bundler and no
npm for the site itself. This file explains what the script reads, what it
writes, and what stands guard over it.

## Inputs

**`recipes/<slug>/`** is the unit. Its `recipe.json` is the only metadata
source; there is no central registry, and adding a folder is the whole act of
adding a recipe. The fields that matter to the generator:

| Field | Meaning |
|---|---|
| `slug` | must equal the directory name |
| `kind` | `recipe` (default) or `build` |
| `summary` | the one-line claim; the build refuses a recipe without one; renders on the card and as the page description |
| `products` | the SignalWire product lines it touches |
| `category` | required, and must name a file in `vocab/categories/`; **derived from `products`, not chosen**: `scaffold.py` writes the first product line, and a folder added by hand must carry it or the build refuses |
| `subcategory` | the task group; required on recipes, absent on builds |
| `surfaces` | which of `python/`, `swml/`, `typescript/` are written; declare only what exists |
| `prerequisites`, `related`, `next` | authored forward edges, rendered as *Where this sits* |
| `composes` | builds only: the recipes the application assembles |
| `repo` | builds only: the repository; a build without one renders as planned |
| `former_slugs` | optional: slugs this folder used to have; each still answers at its old URL with a redirect page to the new one |
| `demo_url` | optional: where a build is deployed; renders "Try it live" as the page's primary action and the repository as a ghost button |
| `plan` | planning state (`status`, `evidence`, `folds`); **never rendered** |
| `tier`, `provenance`, `governed` | planning state; never rendered |

The README is the page. Its `##` sections are fixed (*What this demonstrates*,
*How it works*, *Run it*, *Verify it*, *Limitations*, *What to change first*),
the first paragraph of the first section is the claim plate, fenced code
renders as `pre.mdcode`, and *Run it* replaces the generated steps when present.

**`vocab/`** holds everything the generator would otherwise have to know:
`categories/<key>.json` (label, order, icon path), `surfaces/<key>.json`
(label, entry file, install and run commands, Pygments lexer),
`evidence/*.json` (evidence types, and whether one is `replayable`),
`demo-modes/*.json`. A new category or surface is a new JSON file and zero
Python changes. `check_extensible.py` enforces that with a LEAK guard (no
vocabulary literal in generator source) and a SYNTH guard (invent a category, a
surface and a recipe; the build must render them unchanged).

**`site.config.json`** holds the repository URL and branch, the `base_url`,
and `indexable`. While `indexable` is false every page carries
`<meta name="robots" content="noindex,nofollow">`, `robots.txt` disallows
everything, and the build refuses to finish if a page escaped without the tag.

## Outputs

`python build.py` deletes `site/` and writes: `index.html` (the directory,
with the featured band, category rows, task-group strips and the builds block
under each category), one `r/<slug>.html` per written folder, a `.md` twin per
recipe for answer engines, `sitemap.xml`, `llms.txt`, `robots.txt`, `404.html`.
Every card carries a real `href` to its page; planned cards carry none. Cards
for builds appear in every category their composition touches and dedupe to a
home copy when the Builds filter is on.

`python build.py --preview --all` writes `site/preview.html` instead: one file
with every recipe inlined and a `[data-view]` router, written recipes in full,
folders with no content greyed as "not written yet", inventory rows with no
folder greyed as "planned". That file is what gets published as the artifact.
Run the public build first and the preview second: the public build's `rmtree`
would otherwise delete the preview you were about to publish.

Code panes are highlighted at build time with Pygments; the lexer comes from the
surface's vocabulary entry. `has_content()` in `build.py` decides what counts as
written, and `tools/gen_index.py` reuses it so `recipes/README.md`, the
generated index, means the same thing as the site.

## What stands guard

| Check | What it refuses |
|---|---|
| `tools/lint_recipes.py` | missing README sections, the prose tells (em dashes, "seamless", "just", ...), sentences over 26 words, code lines over 90 characters, an SDK range instead of `==3.0.1`, no `load_dotenv()`, an AgentBase recipe whose `.env.example` omits the basic-auth pair, a webhook URL with the wrong trailing slash for its kind, `signalwire_agents` imports. Also lints the root `README.md` and `CONTRIBUTING.md`. **Takes slugs, not paths.** |
| `tools/gen_index.py --check` | a stale `recipes/README.md` |
| `build.py` | unknown category, surface or evidence type; a dangling `composes`, `prerequisites`, `related` or `next` edge; a recipe with no `summary` or task group; a page that escaped without `noindex`; a Pygments fallback on every pane, which means the dependency is missing |
| `check_extensible.py` | LEAK, SYNTH, SCALE (a raw pixel radius instead of a token) and SOLID (fuchsia at partial opacity on a surface) |
| `verify.py` | every recipe's own verifier, with the SDK resolved from `SIGNALWIRE_SDK_PATH` |
| `tools/qc.py` | the render, in a browser, at 2560, 1920, 1280x720, 820 and 390 wide: no horizontal page scroll, no sticky overlap, card click and back with one view visible, the unbuilt toggle by painted count, tab switching by pane text, no `href="#"` anywhere, the transcript painted at rest, WCAG AA on every text node |

The full order is in `WORKFLOW.md`. Run the lint bare, never through a pipe:
`python tools/lint_recipes.py | tail -1` reports `tail`'s exit code and let
twenty-two problems ship once.

## The verifiers

`tools/verifylib.py` is the shared kit. `validate_swml()` checks a document
against the schema bundled in the 3.0.1 SDK. `Recorder` stands in for the REST
client's HTTP layer and records every request; `Recorder(responses=[...])`
answers with fixtures in order. `assert_documented(kind, method, path, body,
params)` checks a request against the two vendored OpenAPI specs in
`tools/openapi/`. `spec("rest")` and `spec("compat")` return them for finer
assertions, and `swml_schema()` returns the bundled schema. Agents render with
`agent._render_swml()` and run tools with `agent._execute_swaig_function()`.

Three rules make a verifier worth having: assert the JSON keys the platform
receives, not the SDK method names; keep expected values in the verifier, never
imported from the code under test; and treat an absent key as an assertion,
because the SDK omits fields at their schema default.

## Design rules that are load-bearing

The visual language is lifted from the live SignalWire site and written down in
`CLAUDE.md` under *Visual language*, *Recipe page design* and *Colour and the
design pass*. The ones that break things when forgotten: fuchsia has four jobs
and is never painted translucent on a surface; radius comes from three tokens;
nothing is sticky except the code aside, which has nothing below it in its
column; every selector the preview script depends on is a contract, so click a
card and click back at the render before calling a change done.

## Deployment

`vercel.json` runs `bash tools/vercel_build.sh` and serves `site/`; the deploy
builds and never serves committed files. The script finds an interpreter,
creates a virtualenv (a modern system Python is externally managed under PEP
668, so a bare `pip install` is refused), installs the tooling and runs
`build.py`; read it before debugging a deploy. `.github/workflows/gate.yml` runs the gate in CI in two jobs, one for the
Python checks and one for the browser checks. `requirements.txt` at the root is
the tooling (Pygments, PyYAML); each recipe pins its own dependencies.
