# How we work a wave

A wave is five recipes taken from stub to shipped in one pass. This is the
protocol as it stood after eleven waves, with the reasons attached, because
every step exists to stop a mistake that shipped once.

## 0. Before writing

Pick rows from `docs/INVENTORY.md` that a verifier can prove offline against
what is vendored: the 3.0.1 SDK, its bundled SWML schema, and the two OpenAPI
specs in `tools/openapi/`. A claim with no entry in that list, or in a
`signalwire.com/docs` page you can cite by URL, is not ready to write. Mark
it NEEDS VERIFICATION in the inventory and move on.

Authority, in order: the `signalwire-agent-protocol` skill's references; the
vendored SDK read as code; the docs by URL (append `.md` to a docs path when
fetching, the bare path returns 404 to tools); the Knowledge MCP when
authenticated; the demos, excluding the seven on the legacy package. Never a
README in the SDK tree, never a name, never memory.

Gather the facts first, in one pass: dump the spec shapes, the schema
definitions, the SDK method signatures. Half the review rounds this project
has spent were on facts that a dump before writing would have settled.

## 1. Write

A folder is `recipe.json`, `README.md` with the six sections, `verify.py`,
`.env.example`, and one directory per declared surface. Write the verifier
against values you own, and make the README's *Verify it* a bulleted list of
what it asserts, one assertion per bullet. Keep code lines under 90 characters
and sentences under 26 words, because the lint will otherwise find them later
at a worse time.

Do not write into the tree while a gate-and-commit chain is running. The
index is regenerated at the start of the chain and `git add -A` runs at the
end; a folder written in between ships with an index that does not count it.
Draft in the scratchpad and copy in.

## 2. Verify and lint, locally, bare

```bash
python verify.py <slug>                 # the recipe's own proof
python tools/lint_recipes.py <slug>     # slugs, not paths; read the count
python tools/lint_recipes.py            # the whole corpus, exit code intact
```

`SIGNALWIRE_SDK_PATH` must point at the directory containing the vendored
package, absolutely. This machine also has `3.3.0.dev107` in site-packages,
which shadows the vendored 3.0.1 the moment the path is relative, and a run
that reports "verified" against the wrong SDK has happened.

## 3. Review with sol

Reviews go to sol through the codex CLI, one recipe per brief. Write the
brief to `docs/_sol_brief_r_<slug>.md` from the house template (the rules,
the files to read, and the platform facts the reviewer must not go looking
for, `requirements.txt` and `.env.example` included). Launch it backgrounded
with stdin redirected:

```bash
nohup codex exec --skip-git-repo-check "Read docs/_sol_brief_r_<slug>.md and follow it exactly." \
  < /dev/null > docs/_sol_r_<slug>.log 2>&1 &
```

The answer is after the last `codex` marker line, before `tokens used`. Save
it under `docs/RECIPE_REVIEW_<date>_*.md`. Apply the P1s. Take the P2s that
are cheap and refuse, in the brief for the next round, the ones that are
wrong: sol misreads two things every round (that `verifylib.spec("compat")`
is invalid, and that the compat voice callback has twelve required audio
fields), and will ask for "may send" wording on every callback because the
specs call them best-effort. Pre-empt both. Repeat until SHIP or only wording
P2s remain. Three to five rounds is normal.

Codex is a tool, not a gate. When it is down or rate-limited, note the debt
under *Open work* in `CLAUDE.md` and ship on the gate. When one invocation
fails, retry before concluding anything.

## 4. The gate, then commit

```bash
set -o pipefail
python tools/lint_recipes.py
python tools/gen_index.py --check || python tools/gen_index.py
python build.py
python check_extensible.py
python verify.py
python build.py --preview --all
python tools/qc.py
python tools/gen_index.py --check
git add -A && git commit && git push
```

Public build before preview. The order is the one above; a commit without the
render checks has shipped a page broken on first click twice. Commit with
`-c core.safecrlf=false`; the message ends with the Co-Authored-By line.

## 5. After the commit

Republish the artifact from `site/preview.html` to the same URL, always the
same URL. Run `codex review --commit <sha>`; address its findings before the
next wave, and carry unresolved ones faithfully. Write the facts that cost a
round into `CLAUDE.md` in the same session, under a *Wave N* heading, so the
next wave does not pay for them again.

## Things that are always true

- A verifier compares surfaces against a third thing it owns, never against
  each other.
- Exact bodies, whole. `assert body == {...}` catches what a subset check
  lets through.
- An AgentBase root answers only at `/route/`; Flask is strict the other way.
  The lint knows which is which.
- Patches with backslashes or long content go in a script file run with
  Python, never a shell heredoc. This rule has been broken and re-learned
  four times.
- Codex reviews a diff or a commit, never a working tree with `node_modules`
  in it.
