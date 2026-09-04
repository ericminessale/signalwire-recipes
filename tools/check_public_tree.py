#!/usr/bin/env python3
"""Refuse files and metadata that belong only in the local working copy."""

import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_FILES = {
    "AGENTS.md",
    "AGENTS.local.md",
    "CLAUDE.md",
    "CLAUDE.local.md",
    "GEMINI.md",
    ".mcp.json",
    "scaffold.py",
}
FORBIDDEN_PREFIXES = (
    ".aider",
    ".claude/",
    ".codex/",
    ".continue/",
    ".cursor/",
    "docs/",
)
PRIVATE_RECIPE_KEYS = {"governed", "plan", "provenance", "tier"}


def tracked_files():
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [path for path in proc.stdout.decode().split("\0") if path]


def main():
    failures = []
    tracked = tracked_files()
    forbidden_files = {item.casefold() for item in FORBIDDEN_FILES}
    forbidden_prefixes = tuple(item.casefold() for item in FORBIDDEN_PREFIXES)
    for path in tracked:
        folded = path.casefold()
        if folded in forbidden_files or folded.startswith(forbidden_prefixes):
            failures.append(f"tracked internal path: {path}")

    metadata_paths = sorted(
        path for path in tracked
        if path.startswith("recipes/") and path.endswith("/recipe.json")
    )
    for path in metadata_paths:
        metadata = ROOT / path
        data = json.loads(metadata.read_text(encoding="utf-8"))
        leaked = sorted(PRIVATE_RECIPE_KEYS.intersection(data))
        if leaked:
            failures.append(f"private metadata in {path}: {', '.join(leaked)}")

    if failures:
        print("public-tree check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("public-tree check: no internal files or recipe planning metadata tracked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
