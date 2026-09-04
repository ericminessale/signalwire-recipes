#!/usr/bin/env python3
"""Proves extensibility mechanically instead of promising it.

Two guards:

  1. LEAK   - no domain vocabulary value appears anywhere in generator source.
              If someone writes `if cat == "governance"`, this fails.

  2. SYNTH  - invent a brand-new category, a brand-new surface and a recipe
              using both, then build. If the build succeeds and the new things
              render, "adding is adding a file" is true. If it needs a code
              change, this fails.

Run in CI on every PR. Cheap, and it is the only thing standing between the
contract and good intentions.
"""
import json
import pathlib
import shutil
import subprocess
import re
import sys

ROOT = pathlib.Path(__file__).parent
GENERATOR_SRC = ["build.py", "vocab.py"]

sys.path.insert(0, str(ROOT))
import vocab  # noqa: E402


def guard_leak():
    """Generator source must not contain any vocabulary key or label."""
    V = vocab.load()
    banned = {}
    for c in V["categories"]:
        banned[c["key"]] = f"vocab/categories/{c['key']}.json"
        banned[c["label"]] = f"vocab/categories/{c['key']}.json (label)"
    for k, s in V["surfaces"].items():
        banned[k] = f"vocab/surfaces/{k}.json"
    for k in V["evidence"]:
        banned[k] = f"vocab/evidence/{k}.json"

    fails = []
    for name in GENERATOR_SRC:
        f = ROOT / name
        if not f.exists():
            continue
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            # the vocab loader legitimately names the directories it reads
            if name == "vocab.py":
                continue
            if stripped.startswith("#"):
                continue
            for value, origin in banned.items():
                for quoted in (f'"{value}"', f"'{value}'"):
                    if quoted in line:
                        fails.append(
                            f"{name}:{lineno} hardcodes {quoted} "
                            f"(belongs to {origin})\n      {stripped[:88]}"
                        )
    return fails


def guard_synthetic():
    """Add an unknown category + surface + recipe. Build must succeed unchanged."""
    made = []
    try:
        cat = ROOT / "vocab" / "categories" / "zz-synthetic.json"
        cat.write_text(
            json.dumps({"label": "Synthetic Probe", "order": 999, "blurb": "CI only."}),
            encoding="utf-8",
        )
        made.append(cat)

        surf = ROOT / "vocab" / "surfaces" / "zzlang.json"
        surf.write_text(
            json.dumps(
                {
                    "label": "ZZLang",
                    "abbr": "zz",
                    "entry": "main.zz",
                    "deps": "zz.lock",
                    "install": "zz install",
                    "run": "zz run main.zz",
                    "verify": "true",
                }
            ),
            encoding="utf-8",
        )
        made.append(surf)

        rdir = ROOT / "recipes" / "zz-synthetic-probe"
        (rdir / "zzlang").mkdir(parents=True, exist_ok=True)
        made.append(rdir)
        # This fixture is the definition of what a new folder must contain. A
        # folder is written, and gets a page, when its README carries the claim
        # section and its declared surface has a non-empty entry file; anything
        # less is a planned row, greyed on the index (build.has_content).
        (rdir / "README.md").write_text(
            "# Synthetic probe\n\n## What this demonstrates\n\n"
            "A never-before-seen category and surface render with no generator "
            "change.\n",
            encoding="utf-8",
        )
        (rdir / "zzlang" / "main.zz").write_text("probe = true\n", encoding="utf-8")
        (rdir / "recipe.json").write_text(
            json.dumps(
                {
                    "slug": "zz-synthetic-probe",
                    "title": "Synthetic probe",
                    "alias": "ci only",
                    "summary": "Proves a never-before-seen category and surface render.",
                    "scenario": "CI",
                    "category": "zz-synthetic",
                    "products": ["voice"],
                    "capabilities": ["ci"],
                    "subcategory": "other",
                    "surfaces": ["zzlang"],
                    "demo": "none",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return [
                "build failed with a new category/surface present:\n"
                + (proc.stdout + proc.stderr).strip()[:600]
            ]

        idx = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        page = ROOT / "site" / "r" / "zz-synthetic-probe.html"
        fails = []
        if "Synthetic Probe" not in idx:
            fails.append("new category label absent from the generated index")
        if "Synthetic probe" not in idx:
            fails.append("new recipe absent from the generated index")
        if not page.exists():
            fails.append("no page generated for the new recipe")
        elif "zz" not in page.read_text(encoding="utf-8"):
            fails.append("new surface abbreviation absent from the recipe page")
        if "zz-synthetic-probe" not in (ROOT / "site" / "llms.txt").read_text(
            encoding="utf-8"
        ):
            fails.append("new recipe absent from llms.txt")
        return fails
    finally:
        for p in made:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
        subprocess.run(
            [sys.executable, "build.py"], cwd=ROOT, capture_output=True, text=True
        )


def guard_radius_scale():
    """Every corner is a token, a shape, or zero.

    Shapes (50%, 999px) are exempt: they are not steps on a scale, they are
    a circle and a pill. Everything else must name --r-sm / --r-md / --r-lg,
    so the page has one radius system instead of fifteen.
    """
    src = (ROOT / "build.py").read_text(encoding="utf-8")
    allowed = ("var(--r-", "50%", "999px", "0")
    bad = []
    for m in re.finditer(r"border-radius:([^;}]+)", src):
        value = m.group(1).strip()
        if any(tok in value for tok in ("var(--r-", "50%", "999px")):
            continue
        if value == "0":
            continue
        line = src[:m.start()].count("\n") + 1
        bad.append('build.py:%d uses a raw radius "%s"; the scale is '
                   "--r-sm / --r-md / --r-lg" % (line, value))
    return bad


def guard_solid_fuchsia():
    """Fuchsia is a fill, a rule, a keyline or a dot. Never a wash.

    Any rgba() carrying the fuchsia triple with an alpha below 1 fails.
    Periwinkle is the register for tinted surfaces, where the composite of a
    low alpha stays true to the hue.
    """
    src = (ROOT / "build.py").read_text(encoding="utf-8")

    # The rule is about surfaces: a large fuchsia wash on this ground reads as
    # a dull violet. A small control may carry a tint as a state, because at
    # that size it reads as a tint. Exceptions are named so that adding one is
    # a decision rather than a habit.
    allowed = (
        '.chip.kind[aria-pressed="true"]',   # a filter state, not a CTA
        "::selection",                       # text must read through it
    )
    bad = []
    pattern = r"rgba\(\s*(?:247\s*,\s*42\s*,\s*114|var\(--fuchsia-rgb\))\s*,\s*([0-9.]+)\s*\)"
    for m in re.finditer(pattern, src):
        alpha = float(m.group(1))
        if alpha >= 1:
            continue
        # the selector this declaration belongs to
        open_brace = src.rfind("{", 0, m.start())
        prev_close = max(src.rfind("}", 0, open_brace),
                         src.rfind(";", 0, open_brace))
        selector = src[prev_close + 1:open_brace].strip().splitlines()[-1].strip()
        if any(a in selector for a in allowed):
            continue
        line = src[:m.start()].count("\n") + 1
        bad.append('build.py:%d paints fuchsia at alpha %s on "%s"; it '
                   "composites to a dull violet on this ground. Fuchsia is "
                   "solid on a surface, or use the periwinkle accent for a "
                   "wash" % (line, m.group(1), selector[:40]))
    return bad


def main():
    bad = 0
    for name, fn in (("LEAK", guard_leak), ("SYNTH", guard_synthetic),
                     ("SCALE", guard_radius_scale),
                     ("SOLID", guard_solid_fuchsia)):
        fails = fn()
        if fails:
            bad += len(fails)
            print(f"[{name}] FAIL ({len(fails)})")
            for f in fails:
                print(f"    - {f}")
        else:
            print(f"[{name}] pass")
    if bad:
        print(f"\n{bad} failure(s). The extensibility contract is broken.")
        return 1
    print("\nContracts hold: a new category, surface and recipe render with")
    print("zero generator changes, every corner is on the radius scale, and")
    print("fuchsia is never painted at partial opacity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
