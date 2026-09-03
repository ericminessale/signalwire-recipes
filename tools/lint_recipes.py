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
# Every verifier asserts the behaviour of this exact SDK. An open
# range let a clone install a newer one and diverge from what was
# proved, silently. Moving off it is a deliberate wave: bump, re-run
# every verifier, fix, commit.
SDK_PIN = "signalwire-sdk==3.0.1"

MAX_SENTENCE = 26   # writing guide: keep sentences under 26 words


ENTRY = {"python": "python/app.py", "typescript": "typescript/index.ts",
         "swml": "swml/agent.yaml"}


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

    # A declared surface the folder does not carry is a claim of coverage the
    # recipe cannot meet. Three written recipes carried one for weeks: the
    # generator filters them out of the page, so only the manifest was wrong,
    # and `surfaces` is what the list review counts as language coverage.
    for surface in r.get("surfaces", []):
        entry = ENTRY.get(surface)
        if entry is None:
            continue  # an unknown surface is the vocabulary's business, not this rule's
        f = d / entry
        if not f.exists() or not f.stat().st_size:
            fail(slug, "recipe.json",
                 f"declares the {surface} surface, but {entry} is "
                 f"{'missing' if not f.exists() else 'empty'}")

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
    # An AgentBase in 3.0.1 registers its root only as /route/ and answers
    # 200 "null" to /route, so a webhook URL without the slash gets no
    # document. 33 READMEs shipped that way (2026-09-02). A Flask app is the
    # opposite: its route is strict and /route/ is a 404, which codex caught
    # after the first fix added the slash everywhere. SWMLService.serve()
    # answers both, so only the two strict kinds are checked.
    app_src = ""
    if (d / "python" / "app.py").exists():
        app_src = (d / "python" / "app.py").read_text(encoding="utf-8")
    is_agent = "AgentBase" in app_src or "signalwire.prefabs" in app_src
    is_flask = "Flask" in app_src and not is_agent
    if is_agent:
        for m in re.finditer(r"<your-host>/[a-z0-9-]+`", md):
            line = md[:m.start()].count("\n") + 1
            fail(slug, f"README.md:{line}",
                 f"webhook URL {m.group(0)[:-1]} needs a trailing slash: the SDK "
                 "registers the agent root only at /route/")
    if is_flask:
        for m in re.finditer(r"<your-host>/[a-z0-9-]+/`", md):
            line = md[:m.start()].count("\n") + 1
            fail(slug, f"README.md:{line}",
                 f"webhook URL {m.group(0)[:-1]} has a trailing slash a strict "
                 "Flask route answers with 404")
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
    req = d / "python" / "requirements.txt"
    if req.exists() and req.stat().st_size:
        rtxt = req.read_text(encoding="utf-8")
        if "signalwire-sdk" in rtxt and SDK_PIN not in rtxt:
            got = next((ln.strip() for ln in rtxt.splitlines()
                        if "signalwire-sdk" in ln), "?")
            fail(slug, "python/requirements.txt",
                 f"pins {got}; it must be {SDK_PIN}, the version the verifier "
                 "asserts. An open range installs a newer SDK on a clean clone")

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
            # SWMLService.serve() and AgentServer protect the document the
            # same way, which codex caught on a hunt recipe whose README URL
            # carried no credentials (2026-09-02).
            serves_agent = ("AgentBase" in src or "SWMLService" in src) and \
                (".serve(" in src or "AgentServer" in src)
            declared = env_example.read_text(encoding="utf-8")
            if serves_agent and "SWML_BASIC_AUTH_PASSWORD" not in declared:
                fail(slug, ".env.example",
                     "serves an AgentBase but never sets SWML_BASIC_AUTH_USER / "
                     "SWML_BASIC_AUTH_PASSWORD; the SDK then generates a password "
                     "that lives only in the process and the webhook gets a 401")


def check_repo_doc(path, fail):
    """The repository's own prose follows the guide the recipes follow.

    Checks the tells and the sentence cap. The required-section list is a
    recipe rule and does not apply here.
    """
    if not path.exists():
        return fail(path.name, "", "missing: it is the repository's front door")
    md = path.read_text(encoding="utf-8")
    prose = re.sub(r"```.*?```", "", md, flags=re.S)
    prose = re.sub(r"`[^`]*`", "", prose)
    for pat, msg in AI_TELLS:
        for m in re.finditer(pat, prose, re.I):
            fail(path.name, "~%d" % (prose[:m.start()].count(chr(10)) + 1), msg)
    body = re.sub(r"^[#>\-*|].*$", "", prose, flags=re.M)
    for sent in re.split(r"(?<=[.!?])\s+|\n\s*\n", body):
        n = len(re.findall(r"[A-Za-z0-9'\u2019]+", sent))
        if n > MAX_SENTENCE:
            at = prose.find(sent[:40])
            ln = prose[:at].count(chr(10)) + 1 if at > 0 else 0
            fail(path.name, "~%d" % ln,
                 "%d-word sentence; the guide caps them at %d" % (n, MAX_SENTENCE))


def main(argv):
    wanted = set(argv[1:])
    problems = []

    def fail(slug, where, msg):
        problems.append(f"  {slug}/{where}: {msg}" if where
                        else f"  {slug}: {msg}")

    dirs = sorted(p for p in RECIPES.iterdir()
                  if p.is_dir() and (not wanted or p.name in wanted))
    for d in dirs:
        check(d, fail)
    if not wanted:
        # the front door, checked only on a full run
        for doc in ("README.md", "CONTRIBUTING.md"):
            check_repo_doc(RECIPES.parent / doc, fail)
    if problems:
        print(f"lint: {len(problems)} problem(s)")
        print("\n".join(problems))
        return 1
    print(f"lint: {len(dirs)} recipe folders clean"
          + ("" if wanted else ", README and CONTRIBUTING clean"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
