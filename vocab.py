#!/usr/bin/env python3
"""The vocabulary layer.

The generator holds no domain values. Everything it needs to know about
categories, surfaces and evidence types is discovered from vocab/ at build time,
and every renderer is discovered from renderers/ by filename.

So:
  add a category      -> drop a file in vocab/categories/
  add a language      -> drop a file in vocab/surfaces/
  add an evidence type-> drop a file in vocab/evidence/ + renderers/<name>.py
  add a recipe        -> drop a folder in recipes/

None of those touch build.py. check_extensible.py enforces that mechanically.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
VOCAB = ROOT / "vocab"
RENDERERS = ROOT / "renderers"


def _load_dir(name, required):
    """Every *.json in vocab/<name>/ becomes an entry keyed by filename stem."""
    d = VOCAB / name
    if not d.is_dir():
        raise SystemExit(f"vocab/{name}/ is missing")
    out = {}
    for f in sorted(d.glob("*.json")):
        try:
            v = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"vocab/{name}/{f.name}: invalid JSON — {e}")
        missing = [k for k in required if k not in v]
        if missing:
            raise SystemExit(
                f"vocab/{name}/{f.name}: missing required key(s) {missing}"
            )
        v["key"] = f.stem
        out[f.stem] = v
    if not out:
        raise SystemExit(f"vocab/{name}/ has no entries")
    return out


def categories():
    """Ordered list. `order` decides gallery sequence; ties fall back to label."""
    c = _load_dir("categories", ["label", "order"])
    return sorted(c.values(), key=lambda v: (v["order"], v["label"]))


def surfaces():
    return _load_dir("surfaces", ["label", "abbr", "entry"])


def evidence():
    return _load_dir("evidence", ["label", "renderer"])


def subcategories():
    d = VOCAB / "subcategories"
    if not d.is_dir():
        return {}
    return _load_dir("subcategories", ["label"])


def demo_modes():
    return _load_dir("demo-modes", ["label", "copy"])


def renderers():
    """Discovered by filename. renderers/foo.py must expose render(data) -> str."""
    out = {}
    if not RENDERERS.is_dir():
        return out
    for f in sorted(RENDERERS.glob("*.py")):
        if f.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"renderers.{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "render", None)
        if not callable(fn):
            raise SystemExit(f"renderers/{f.name}: must define render(data) -> str")
        out[f.stem] = fn
    return out


def load():
    """One call, everything the generator is allowed to know."""
    cats = categories()
    surf = surfaces()
    ev = evidence()
    rend = renderers()
    modes = demo_modes()
    subs = subcategories()

    # every declared evidence type must have a discovered renderer
    for k, v in ev.items():
        if v["renderer"] not in rend:
            raise SystemExit(
                f"vocab/evidence/{k}.json wants renderer '{v['renderer']}' "
                f"but renderers/{v['renderer']}.py does not exist"
            )

    return {
        "categories": cats,
        "category_keys": [c["key"] for c in cats],
        "category_label": {c["key"]: c["label"] for c in cats},
        "surfaces": surf,
        "surface_abbr": {k: v["abbr"] for k, v in surf.items()},
        "evidence": ev,
        "renderers": rend,
        "subcategories": subs,
        "demo_modes": modes,
        "demo_copy": {k: m["copy"] for k, m in modes.items()},
    }


def validate_recipe(r, V, where=""):
    """A recipe may only use vocabulary that exists. Unknown values are errors."""
    errs = []
    if r.get("category") not in V["category_label"]:
        errs.append(
            f"unknown category '{r.get('category')}' "
            f"(add vocab/categories/{r.get('category')}.json to introduce it)"
        )
    # CLAUDE.md hard rule 6: every recipe needs a real summary. The card and
    # the page description render it, and an empty one shipped as a blank card
    # description until this check existed (codex, 2026-09-02).
    if not str(r.get("summary") or "").strip():
        errs.append("missing summary (the one-line claim the card and the page carry)")
    for s in r.get("surfaces", []):
        name = s if isinstance(s, str) else s.get("lang")
        if name not in V["surfaces"]:
            errs.append(
                f"unknown surface '{name}' "
                f"(add vocab/surfaces/{name}.json to introduce it)"
            )
    return [f"{where}: {e}" for e in errs] if where else errs


if __name__ == "__main__":
    V = load()
    print(f"categories : {', '.join(V['category_keys'])}")
    print(f"surfaces   : {', '.join(V['surfaces'])}")
    print(f"evidence   : {', '.join(V['evidence'])}")
    print(f"renderers  : {', '.join(V['renderers'])}")
    print(f"demo modes : {', '.join(V['demo_modes'])}")
