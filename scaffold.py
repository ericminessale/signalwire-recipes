#!/usr/bin/env python3
"""Materialise recipes.json into one folder per recipe.

Idempotent: never overwrites an existing recipe.json or README.md, so a
hand-edited recipe survives a re-run. This script exists only to seed the
tree; after that, recipes are added by creating a folder.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
RECIPES = ROOT / "recipes"

import vocab

_V = vocab.load()
# file conventions per surface come from vocab/surfaces/, never from here
SURFACE_FILES = {
    k: (s.get("entry"), s.get("deps")) for k, s in _V["surfaces"].items()
}

README = """# {title}

> {summary}

**Technical:** `{alias}`
**Scenario:** {scenario}

## What this demonstrates

_TODO — the pattern, in two sentences. This is the part that carries the argument._

## Prerequisites

- A SignalWire account and API token
- A phone number on that account

## Setup

```bash
cp .env.example .env    # add your credentials
```

## Run it

_TODO per surface. Surfaces declared: {surfaces}_

## What to change first

_TODO_

## Related

_TODO_
"""

ENV = """SIGNALWIRE_SPACE=your-space.signalwire.com
SIGNALWIRE_PROJECT_ID=your_project_id_here
SIGNALWIRE_API_TOKEN=your_api_token_here
"""


def main():
    data = json.loads((ROOT / "recipes.json").read_text(encoding="utf-8"))
    created = kept = 0

    for r in data:
        d = RECIPES / r["slug"]
        d.mkdir(parents=True, exist_ok=True)

        manifest = d / "recipe.json"
        if manifest.exists():
            kept += 1
        else:
            manifest.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
            created += 1

        readme = d / "README.md"
        if not readme.exists():
            readme.write_text(
                README.format(
                    title=r["title"],
                    summary=r["summary"],
                    alias=r.get("alias", ""),
                    scenario=r.get("scenario", ""),
                    surfaces=", ".join(r.get("surfaces", [])),
                ),
                encoding="utf-8",
            )

        envf = d / ".env.example"
        if not envf.exists():
            envf.write_text(ENV, encoding="utf-8")

        for surface in r.get("surfaces", []):
            sd = d / surface
            sd.mkdir(exist_ok=True)
            code, dep = SURFACE_FILES.get(surface, (None, None))
            for fname in (code, dep):
                if fname and not (sd / fname).exists():
                    (sd / fname).write_text("", encoding="utf-8")

    print(f"scaffold: {created} created, {kept} already present, {len(data)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
