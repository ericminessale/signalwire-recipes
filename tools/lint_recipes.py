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
# Prose rules. The SignalWire writing guide is the authority (Knowledge MCP:
# get_writing_guide); every entry either quotes it or is a tell that survived a
# review here. A recipe README is a Diataxis "how-to guide", so second person is
# correct and the no-addressing-the-reader rule does not apply to it.
AI_TELLS = (
    # --- verbatim rules from the writing guide ---
    ("\u2014|(?<![-\\w])--(?![-\\w])",
     "em dash or --: rewrite with a comma, colon, period, semicolon or parentheses"),
    (r"\b(just|simply|easy|easily|straightforward)\b",
     "dismissive language: it adds no information and dismisses difficulty"),
    (r"\b(honest|honestly|transparent|candid)\b|\bto be clear\b|\bthe truth is\b",
     "claims the virtue instead of demonstrating it; 'honest' is a reliable tell"),
    (r"\b(foo|bar|baz|qux)\b", "placeholder name: use a real-world scenario"),
    (r"\bplease\b", "procedural steps are imperatives, not requests"),
    (r"\bas (mentioned|described|noted) (above|earlier)\b|\bthe previous section\b|\bsee above\b",
     "a section must stand alone: retrieval delivers it without its neighbours"),
    # --- tells that survived a review in this repo ---
    (r"\bdelve\b", "delve"),
    (r"\bleverage\b", "leverage: use 'use'"),
    (r"\bseamless(ly)?\b", "seamless"),
    (r"\brobust\b", "robust"),
    (r"\bcutting[- ]edge\b", "cutting-edge"),
    (r"\bit'?s worth noting\b", "it's worth noting: say the thing"),
    (r"\bin today'?s\b", "in today's ..."),
    (r"\bunlock(s|ing)? the power\b", "unlock the power"),
    (r"\bdive (in|into)\b", "dive in"),
    (r"\bmoreover\b|\bfurthermore\b|\bin conclusion\b", "connective filler"),
    (r"\bnot only .{1,40}\bbut also\b", "not only ... but also"),
    (r"\bisn'?t just\b|\bis not just\b", "X isn't just Y"),
    (r"\bwhether you'?re\b", "whether you're a ... or a ..."),
    (r"\bwe'?ll explore\b|\blet'?s (dive|explore|take a look)\b", "tour-guide framing"),
    (r"\bgame[- ]chang(er|ing)\b", "game-changer"),
)
MAX_SENTENCE = 26   # writing guide: keep sentences under 26 words


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
    verifier = d / "verify.py"
    if not verifier.exists():
        fail(slug, "verify.py", "missing: a recipe is done when its claim is proven, not when it compiles")
    else:
        # A verifier's module docstring states the claim and the proof in
        # prose, so it is held to the prose rules. Sol found a 28-word
        # sentence sitting in one because the lint only read READMEs.
        try:
            doc = ast.get_docstring(ast.parse(verifier.read_text(encoding="utf-8")))
        except SyntaxError:
            doc = None
        if doc:
            for pat, msg in AI_TELLS:
                for m in re.finditer(pat, doc, re.I):
                    fail(slug, "verify.py docstring", msg)
            # The 26-word cap is deliberately not applied here. It is a rule
            # for prose a reader reads for meaning; a verifier docstring is
            # dense technical documentation, where one sentence listing four
            # assertions beats four fragments.

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
            fail(slug, f"README.md:~{line}", msg)
    body = re.sub(r"^[#>\-*|].*$", "", prose, flags=re.M)   # skip headings, lists, tables
    # A paragraph break ends a sentence even without a full stop, or a lead-in
    # like "Three requests in dependency order:" merges with the paragraph that
    # follows its code block and is counted as one 46-word run-on.
    for sent in re.split(r"(?<=[.!?])\s+|\n\s*\n", body):
        n = len(re.findall(r"[A-Za-z0-9'\u2019]+", sent))
        if n > MAX_SENTENCE:
            at = prose.find(sent[:40])
            ln = prose[:at].count("\n") + 1 if at > 0 else 0
            fail(slug, f"README.md:~{ln}", f"{n}-word sentence; the guide caps them at {MAX_SENTENCE}")
    env_example = d / ".env.example"
    if not env_example.exists():
        fail(slug, ".env.example", "missing")
    else:
        # An AgentBase serves its SWML behind basic auth. With nothing in the
        # environment the SDK invents a password that exists only in the
        # running process: the webhook 401s and it changes on every restart.
        app_py = d / "python" / "app.py"
        if app_py.exists() and app_py.stat().st_size:
            src = app_py.read_text(encoding="utf-8")
            serves_agent = "AgentBase" in src and ".serve(" in src
            declared = env_example.read_text(encoding="utf-8")
            if serves_agent and "SWML_BASIC_AUTH_PASSWORD" not in declared:
                fail(slug, ".env.example",
                     "serves an AgentBase but never sets SWML_BASIC_AUTH_USER / "
                     "SWML_BASIC_AUTH_PASSWORD; the SDK then generates a password "
                     "that lives only in the process and the webhook gets a 401")


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
