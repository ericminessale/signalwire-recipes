#!/usr/bin/env python3
"""Mechanical check of the recipe authoring rules. Refuses on any violation.

Every rule here is a mistake that shipped, or one the SignalWire agent protocol
skill names as a silent-failure mode. A rule belongs here rather than in a
reviewer's head as soon as it has been broken once.

    python tools/lint_recipes.py [slug ...]
"""
import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECIPES = ROOT / "recipes"
MAX_LINE = 90          # the code pane holds 91 characters at 1280px
REQUIRED_SECTIONS = ("What this demonstrates", "How it works", "Run it",
                     "Verify it", "What to change first")
# Prose tells. Written English on this site does not use these.
AI_TELLS = (
    (r"—", "em dash: use a comma, a colon, or two sentences"),
    (r"\bdelve\b", "delve"),
    (r"\bleverage\b", "leverage: use 'use'"),
    (r"\bseamless(ly)?\b", "seamless"),
    (r"\brobust\b", "robust"),
    (r"\bcutting[- ]edge\b", "cutting-edge"),
    (r"\bit'?s worth noting\b", "it's worth noting: just say it"),
    (r"\bin today'?s\b", "in today's ..."),
    (r"\bunlock(s|ing)? the power\b", "unlock the power"),
    (r"\bdive (in|into)\b", "dive in"),
    (r"\bthat said,", "that said"),
    (r"\bmoreover\b", "moreover"),
    (r"\bfurthermore\b", "furthermore"),
    (r"\bin conclusion\b", "in conclusion"),
    (r"\bnot only .{1,40}\bbut also\b", "not only ... but also"),
    (r"\bisn'?t just\b|\bis not just\b", "X isn't just Y"),
    (r"\bwhether you'?re\b", "whether you're a ... or a ..."),
    (r"\bwe'?ll explore\b", "we'll explore"),
    (r"\blet'?s (dive|explore|take a look)\b", "let's ..."),
    (r"\bgame[- ]chang(er|ing)\b", "game-changer"),
    (r":\s*$", None),  # placeholder, filtered below
)
AI_TELLS = tuple((p, m) for p, m in AI_TELLS if m)


def code_files(d):
    for sub, name in (("python", "app.py"), ("typescript", "index.ts"), ("swml", "agent.yaml")):
        f = d / sub / name
        if f.exists() and f.stat().st_size:
            yield f


def check(d, fail):
    slug = d.name
    manifest = d / "recipe.json"
    if not manifest.exists():
        return fail(slug, "recipe.json", "missing")
    r = json.loads(manifest.read_text(encoding="utf-8"))
    if r.get("slug") != slug:
        fail(slug, "recipe.json", f"slug {r.get('slug')!r} != directory name")

    written = list(code_files(d))
    if not written:
        return  # a stub: the generator already marks it "not written yet"

    # --- code -----------------------------------------------------------
    for f in written:
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding="utf-8")
        for i, line in enumerate(text.split("\n"), 1):
            if len(line) > MAX_LINE:
                fail(slug, f"{rel}:{i}", f"{len(line)} chars > {MAX_LINE}; the code pane scrolls")
        if "signalwire_agents" in text:
            fail(slug, rel, "imports signalwire_agents: the 3.x name is signalwire")
        if f.suffix == ".py":
            reads_env = re.search(r"os\.environ|os\.getenv|RestClient\(\s*\)", text)
            if reads_env and "load_dotenv()" not in text:
                fail(slug, rel, "reads the environment but never calls load_dotenv(); "
                                "the SDK does not read .env, so `cp .env.example .env` does nothing")
            try:
                ast.parse(text)
            except SyntaxError as e:
                fail(slug, rel, f"syntax error line {e.lineno}: {e.msg}")

    req = d / "python" / "requirements.txt"
    if (d / "python" / "app.py").exists() and (d / "python" / "app.py").stat().st_size:
        if not req.exists() or not req.stat().st_size:
            fail(slug, "python/requirements.txt", "missing")
        else:
            body = req.read_text(encoding="utf-8")
            if "signalwire-agents" in body:
                fail(slug, "python/requirements.txt", "pins signalwire-agents (0.1/1.0 name)")
            if "load_dotenv" in (d / "python" / "app.py").read_text(encoding="utf-8") \
                    and "python-dotenv" not in body:
                fail(slug, "python/requirements.txt", "app.py calls load_dotenv but dotenv is not pinned")

    # --- the claim has to be provable ------------------------------------
    if not (d / "verify.py").exists():
        fail(slug, "verify.py", "missing: a recipe is done when its claim is proven, not when it compiles")

    # --- README -----------------------------------------------------------
    readme = d / "README.md"
    if not readme.exists():
        return fail(slug, "README.md", "missing")
    md = readme.read_text(encoding="utf-8")
    heads = re.findall(r"^## (.+)$", md, re.M)
    for want in REQUIRED_SECTIONS:
        if want not in heads:
            fail(slug, "README.md", f"no '## {want}' section")
    if "_TODO" in md:
        fail(slug, "README.md", "still contains _TODO")
    # prose only: fenced code and inline code are the author's, not prose
    prose = re.sub(r"```.*?```", "", md, flags=re.S)
    prose = re.sub(r"`[^`]*`", "", prose)
    for pat, msg in AI_TELLS:
        for m in re.finditer(pat, prose, re.I):
            line = prose[:m.start()].count("\n") + 1
            fail(slug, f"README.md:~{line}", f"reads as generated: {msg}")
    if not (d / ".env.example").exists():
        fail(slug, ".env.example", "missing")


def main(argv):
    wanted = set(argv[1:])
    problems = []

    def fail(slug, where, msg):
        problems.append(f"  {slug}/{where}: {msg}")

    dirs = sorted(p for p in RECIPES.iterdir()
                  if p.is_dir() and (not wanted or p.name in wanted))
    for d in dirs:
        check(d, fail)
    if problems:
        print(f"lint: {len(problems)} problem(s)")
        print("\n".join(problems))
        return 1
    print(f"lint: {len(dirs)} recipe folders clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
