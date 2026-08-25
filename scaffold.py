#!/usr/bin/env python3
"""Seed recipes/ from the plan in docs/enum/inventory.json.

Two jobs, both idempotent and both non-destructive:

  sync    every existing recipes/<slug>/recipe.json whose slug is an inventory
          row gets its planning-derived fields refreshed (category, products,
          task group, capabilities, tier, plan). Author-owned fields (title,
          alias, summary, scenario, surfaces, demo, repo, composes, README) are
          never overwritten once present.
  create  inventory rows in the launch set (or all rows with --all) that have
          no folder yet get one: recipe.json, a README skeleton, .env.example
          and empty entry files per surface.

It never deletes. Folding or retiring a folder is a deliberate `git rm`.
recipe.json remains the only metadata source the generator reads; the
inventory is the plan that seeds it.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
RECIPES = ROOT / "recipes"
PLAN = ROOT / "docs" / "enum" / "inventory.json"

import vocab

_V = vocab.load()
SURFACE_FILES = {
    k: (s.get("entry"), s.get("deps")) for k, s in _V["surfaces"].items()
}

# interface tag -> surface directory, declared by each vocab/surfaces/*.json
# in its `interfaces` list; the scaffolder holds no surface names of its own.
SURFACE_FOR = {
    iface: k
    for k, s in _V["surfaces"].items()
    for iface in s.get("interfaces", [])
}

README = """# {title}

> {summary}

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
"""

ENV = """SIGNALWIRE_SPACE=your-space.signalwire.com
SIGNALWIRE_PROJECT_ID=your_project_id_here
SIGNALWIRE_API_TOKEN=your_api_token_here
"""


def title_from_slug(slug):
    words = slug.split("-")
    return (words[0].capitalize() + " " + " ".join(words[1:])).strip()


def scenario_from_folds(folds):
    for f in folds:
        m = re.match(r"#\d+ \(canonical: ([^)]+)\)", f)
        if m:
            return m.group(1)
    return ""


def surfaces_from(row):
    out = []
    for i in row.get("interfaces", []):
        s = SURFACE_FOR.get(i)
        if s and s not in out and s in _V["surfaces"]:
            out.append(s)
    return out


def planning_fields(row):
    """Fields derived from the plan. Internal ones live under `plan` and must
    never render (CLAUDE.md hard rule 7)."""
    out = {
        "category": row["products"][0],
        "products": list(row["products"]),
        "capabilities": list(row.get("capabilities", [])),
        "tier": "launch" if row.get("launch") else "next",
        "plan": {
            "kind": row["kind"],
            "status": row["status"],
            "lens": row["lens"],
            "folds": list(row.get("folds", [])),
            "evidence": list(row.get("evidence", [])),
        },
    }
    if row["kind"] == "build":
        out["kind"] = "build"
    elif row.get("task_group"):
        out["subcategory"] = row["task_group"]
    return out


def fresh_manifest(row):
    m = {
        "slug": row["slug"],
        "title": title_from_slug(row["slug"]),
        "alias": "",
        "summary": row["claim"],
        "scenario": scenario_from_folds(row.get("folds", [])),
        "surfaces": [] if row["kind"] == "build" else surfaces_from(row),
        "governed": "governance" in row.get("capabilities", []),
        "demo": "none",
        "provenance": "new",
    }
    m.update(planning_fields(row))
    return m


def main():
    rows = json.loads(PLAN.read_text(encoding="utf-8"))["rows"]
    by_slug = {r["slug"]: r for r in rows}
    create_all = "--all" in sys.argv
    synced = created = skipped = 0

    for row in rows:
        d = RECIPES / row["slug"]
        manifest = d / "recipe.json"
        if manifest.exists():
            m = json.loads(manifest.read_text(encoding="utf-8"))
            m.update(planning_fields(row))
            if "kind" in m and row["kind"] != "build":
                m.pop("kind", None)
            manifest.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
            synced += 1
            continue
        if not (create_all or row.get("launch")):
            skipped += 1
            continue
        if row["kind"] in ("guide", "tool", "hold") and not create_all:
            skipped += 1
            continue
        d.mkdir(parents=True)
        m = fresh_manifest(row)
        manifest.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        (d / "README.md").write_text(
            README.format(
                title=m["title"], summary=m["summary"],
                scenario=m["scenario"] or "—",
                surfaces=", ".join(m["surfaces"]) or "none yet",
            ),
            encoding="utf-8",
        )
        (d / ".env.example").write_text(ENV, encoding="utf-8")
        for surface in m["surfaces"]:
            sd = d / surface
            sd.mkdir(exist_ok=True)
            for fname in SURFACE_FILES.get(surface, (None, None)):
                if fname and not (sd / fname).exists():
                    (sd / fname).write_text("", encoding="utf-8")
        created += 1

    orphans = sorted(
        p.name for p in RECIPES.iterdir()
        if p.is_dir() and p.name not in by_slug
    )
    print(f"scaffold: {synced} synced, {created} created, {skipped} left in the plan only")
    if orphans:
        print("folders with no inventory row (fold or retire deliberately):")
        for o in orphans:
            print(f"  - {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
