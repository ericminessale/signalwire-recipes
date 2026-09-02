# Start here

This directory is for the people who run the recipes project. It is tracked in
git, unlike the rest of `docs/`, and it is written for a colleague rather than
for a coding assistant. The public-facing documentation is elsewhere:

| You want to | Read |
|---|---|
| Clone a recipe and run it | [`README.md`](../../README.md) at the repository root |
| Write or change a recipe | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |
| Understand how the site is generated and checked | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Work a wave of recipes the way we do it, review loop included | [`WORKFLOW.md`](WORKFLOW.md) |
| See what is planned, written and on hold | [`../INVENTORY.md`](../INVENTORY.md) |
| Find the decisions and the platform facts learned the hard way | [`CLAUDE.md`](../../CLAUDE.md) |

## The one-sentence version

Each folder under `recipes/` is one testable claim about the SignalWire
platform, with the smallest code that proves it and a `verify.py` that proves
it offline. `build.py` turns those folders into a static site. The gate (lint,
index, build, guards, verifiers, render checks) is what "done" means.

## Two voices in one repository

The repository reads as if it were public, and the plan is that one day it is.
`README.md`, `CONTRIBUTING.md`, the recipe folders and `recipes/README.md` are
written in that voice and need no change to go public. This directory,
`docs/INVENTORY.md` and `CLAUDE.md` are internal. `CLAUDE.md` is the one file
that would need a pass before the repository is made public or moved to the
SignalWire organisation, because it quotes people and carries session
narrative. Treat that pass as part of the same decision as flipping
`indexable` in `site.config.json`.

## Where things live

- Repository: `github.com/ericminessale/signalwire-recipes`, private, default
  branch `master`.
- Preview host: Vercel on Eric's work account, building `site/` from source.
  Not indexed; every page carries `noindex` while `indexable` is false.
- The artifact: the single-file preview at
  `https://claude.ai/code/artifact/d8f9c247-3e3e-42b3-865a-7ddc8bca878f`,
  republished from `site/preview.html` after every wave. It is the page shown
  to leadership.
- The vendored SDK, 3.0.1, one directory over in the workspace. The
  verifiers need it on `SIGNALWIRE_SDK_PATH`; see `WORKFLOW.md`.

## The numbers, as of 2026-09-02

96 of 121 folders written and verified. The 25 that remain, and why each
waits, are listed under *Open work* in `CLAUDE.md`.
