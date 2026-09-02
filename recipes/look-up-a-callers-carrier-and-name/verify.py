"""Prove the claim without a network.

Claim: one GET to the lookup path returns a number's details, and
`include=carrier,cnam` is what asks for carrier and caller-ID name.

Proof: with the HTTP layer replaced by a recorder, `enrich` makes exactly one
GET to the documented lookup path for the number with `include` set to
`carrier,cnam`, and `check` makes one GET with no query at all. The path and
the `include` parameter are documented in the vendored spec, whose description
of `include` names exactly those two values. The spec's response schema
carries `carrier` and `cnam` objects. Expected values live here, not in
app.py.
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))
os.environ.update({
    "SIGNALWIRE_PROJECT_ID": "proj-1234",
    "SIGNALWIRE_API_TOKEN": "PT-test",
    "SIGNALWIRE_SPACE": "example.signalwire.com",
})

import verifylib as V  # noqa: E402

NUMBER = "+15557654321"
TEMPLATE = "/api/relay/rest/lookup/phone_number/{e164_number}"
PATH = TEMPLATE.replace("{e164_number}", NUMBER)


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder()
    recipe.client.lookup._http = rec

    recipe.enrich(NUMBER)
    recipe.check(NUMBER)
    assert len(rec.calls) == 2, rec.calls
    rich, plain = rec.calls

    assert (rich["method"], rich["path"]) == ("GET", PATH), rich
    assert rich["params"] == {"include": "carrier,cnam"}, rich
    V.assert_documented("rest", "GET", PATH, None, rich["params"])

    assert (plain["method"], plain["path"]) == ("GET", PATH), plain
    assert plain["params"] is None, plain

    # the spec's own words for include, and the response fields it promises
    op = V.spec("rest")["paths"][TEMPLATE]["get"]
    include = next(p for p in op["parameters"] if p["name"] == "include")
    assert "carrier" in include["description"] and "cnam" in include["description"]
    schemas = V.spec("rest")["components"]["schemas"]
    resp = op["responses"]["200"]["content"]["application/json"]["schema"]
    resp = schemas[resp["$ref"].split("/")[-1]] if "$ref" in resp else resp
    props = resp["properties"]
    assert {"carrier", "cnam", "valid_number", "e164", "number_type"} <= set(props), sorted(props)
    carrier = schemas[props["carrier"]["$ref"].split("/")[-1]] if "$ref" in props["carrier"] else props["carrier"]
    assert "linetype" in carrier["properties"], sorted(carrier["properties"])

    print(f"ok: GET {PATH}?include=carrier,cnam and once without a query; include is "
          f"documented with those two values; the response schema carries carrier "
          f"(with linetype) and cnam")


if __name__ == "__main__":
    main()
