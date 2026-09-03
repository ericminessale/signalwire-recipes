"""Shared helpers for recipes/*/verify.py.

Everything here runs offline. A verifier proves a recipe's claim in the artifact
the platform would receive: a SWML document (validated against the SDK's bundled
schema), a REST request (checked against the OpenAPI specs in tools/openapi/),
or a webhook reply.
"""
import json
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OPENAPI = ROOT / "tools" / "openapi"


def sdk_banner():
    import signalwire
    print(f"sdk {signalwire.__version__} at {signalwire.__file__}")
    return signalwire


# ---- SWML -----------------------------------------------------------------

def validate_swml(doc):
    """Raise AssertionError unless `doc` validates against the SDK's schema."""
    from signalwire.utils.schema_utils import SchemaUtils
    ok, errors = SchemaUtils().validate_document(doc)
    assert ok, "SWML does not validate:\n  " + "\n  ".join(errors)
    return doc


def swml_schema():
    """The SDK's bundled SWML schema as a dict, for reading ranges and enums."""
    import json
    import pathlib
    import signalwire
    path = next(pathlib.Path(signalwire.__file__).parent.rglob("schema.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def verbs(doc, section="main"):
    """[(verb_name, params), ...] for a section."""
    out = []
    for item in doc["sections"][section]:
        if isinstance(item, dict):
            (k, v), = item.items()
            out.append((k, v))
        else:
            out.append((item, None))
    return out


def verb_names(doc, section="main"):
    return [k for k, _ in verbs(doc, section)]


def first(doc, verb, section="main"):
    for k, v in verbs(doc, section):
        if k == verb:
            return v
    raise AssertionError(f"no {verb} verb in section {section}: {verb_names(doc, section)}")


# ---- REST -----------------------------------------------------------------

class Recorder:
    """Stands in for RestClient's HttpClient and records every request."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [])

    def _record(self, method, path, body=None, params=None):
        self.calls.append({"method": method, "path": path, "body": body, "params": params})
        return self.responses.pop(0) if self.responses else {}

    def get(self, path, params=None):
        return self._record("GET", path, None, params)

    def post(self, path, body=None, params=None):
        return self._record("POST", path, body, params)

    def put(self, path, body=None):
        return self._record("PUT", path, body)

    def patch(self, path, body=None):
        return self._record("PATCH", path, body)

    def delete(self, path):
        return self._record("DELETE", path)


def record_everything(client, recorder):
    """Point every namespace/resource hanging off a RestClient at the recorder."""
    seen = set()

    def walk(obj, depth=0):
        if id(obj) in seen or depth > 3:
            return
        seen.add(id(obj))
        if hasattr(obj, "_http"):
            obj._http = recorder
        for name, val in vars(obj).items():
            if name.startswith("__") or isinstance(val, (str, int, float, list, dict, tuple, set)):
                continue
            if hasattr(val, "__dict__"):
                walk(val, depth + 1)

    walk(client)
    return recorder


_SPECS = {}


def spec(kind):
    """'rest' (native) or 'compat'."""
    if kind not in _SPECS:
        _SPECS[kind] = json.loads((OPENAPI / f"{kind}.json").read_text(encoding="utf-8"))
    return _SPECS[kind]


def _deref(s, node):
    while isinstance(node, dict) and "$ref" in node:
        target = s
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    if isinstance(node, dict) and "allOf" in node:
        merged = {"required": [], "properties": {}}
        for part in node["allOf"]:
            part = _deref(s, part)
            merged["required"] += part.get("required", [])
            merged["properties"].update(part.get("properties", {}))
        node = merged
    return node


def _match_path(template, path):
    pattern = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", template) + "$"
    return re.match(pattern, path) is not None


def assert_documented(kind, method, path, body=None, params=None):
    """The request must exist in the OpenAPI spec; body keys must be documented
    properties and every documented required field must be present. Returns the
    operation object."""
    s = spec(kind)
    if kind == "compat":
        path = re.sub(r"^/api/laml/2010-04-01", "", path)
    hits = [(t, ops) for t, ops in s["paths"].items() if _match_path(t, path)]
    assert hits, f"{method} {path} is not a documented {kind} path"
    # A literal segment beats a placeholder: /documents/search must not be
    # swallowed by /documents/{id}.
    hits.sort(key=lambda h: h[0].count("{"))
    template, ops = hits[0]
    op = ops.get(method.lower())
    assert op, f"{method} not documented for {template} (has {list(ops)})"
    if body is not None:
        content = op.get("requestBody", {}).get("content", {})
        schema = {}
        for ct in ("application/json", "application/x-www-form-urlencoded"):
            if ct in content:
                schema = _deref(s, content[ct].get("schema", {}))
                break
        props = set(schema.get("properties", {}))
        if props:  # some spec entries carry no body schema; then only the path is checked
            unknown = set(body) - props
            assert not unknown, f"undocumented field(s) for {template}: {sorted(unknown)}"
            for req in schema.get("required", []):
                assert req in body, f"{template} requires {req}"
    if params:
        documented = {q["name"] for q in op.get("parameters", []) if q.get("in") == "query"}
        if documented:
            unknown = set(params) - documented
            assert not unknown, f"undocumented query param(s) for {template}: {sorted(unknown)}"
    return op


def type_check_typescript(here, what="the installed types"):
    """Run tsc --noEmit on a recipe's typescript/ directory.

    Returns the sentence a verifier prints. With no node_modules there is
    nothing to run, which is fine on a machine without npm and is not fine
    where the dependency is supposed to be: SIGNALWIRE_REQUIRE_TSC=1 turns that
    case into a failure, and CI sets it. A check that quietly does not run is
    how three wrong member names would have shipped.
    """
    ts = pathlib.Path(here) / "typescript"
    tsc = ts / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
    if tsc.exists():
        subprocess.run([str(tsc), "--noEmit"], cwd=ts, check=True)
        return f"typescript type-checked against {what}"
    if os.environ.get("SIGNALWIRE_REQUIRE_TSC"):
        raise AssertionError(
            f"SIGNALWIRE_REQUIRE_TSC is set and {tsc} is missing: "
            f"run npm ci in {ts} before verifying")
    return "typescript not type-checked (run npm ci in typescript/ first)"


def assert_basic_auth_from_env(agent):
    """An AgentBase serves its SWML behind basic auth.

    With no credentials in the environment the SDK generates a password that
    exists only in the running process, so the number's webhook gets a 401 and
    the password changes on every restart. The SDK says so on startup. Every
    agent recipe asserts the credentials came from the environment instead.
    """
    user, password, source = agent.get_basic_auth_credentials(include_source=True)
    # The SDK reports "generated" only for usernames shaped user_*, and it
    # generates "signalwire", so an auto-generated password reports as
    # "provided". Require "environment" rather than trusting the label.
    assert source == "environment", (
        f"basic auth did not come from the environment (source={source!r}); "
        f"set SWML_BASIC_AUTH_USER and SWML_BASIC_AUTH_PASSWORD, or the SDK "
        f"invents a password that exists only in this process and the "
        f"number's webhook gets a 401"
    )
    assert user and password, (user, bool(password))
    return user
