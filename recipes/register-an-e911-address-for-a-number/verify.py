"""Prove the claim without a network.

Claim: an emergency address is created with the fields the spec requires and
`emergency_enabled` on, then attached to a number by id, in two REST calls.

Proof: with the HTTP layer replaced by a recorder, `create_address` makes one
POST to the documented addresses path. Its body carries every field in the
spec's required list plus `emergency_enabled: true`. `attach` makes one POST
to the number's documented e911 path with exactly `e911_address_id`. The
verifier reads both required lists from the spec rather than assuming them,
and every field sent is a documented property. `number_id` makes one GET to
the numbers list and picks the matching id. Expected values live here, not in
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

ADDRESSES = "/api/relay/rest/addresses"
NUMBER_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
ADDRESS_ID = "9b2e4c1a-7d3f-4e8b-a1c2-5d6e7f8a9b0c"
E911 = f"/api/relay/rest/phone_numbers/{NUMBER_ID}/e911_address"
FIELDS = dict(label="Ridgeline Cycles workshop", first_name="Dana",
              last_name="Whitfield", street_number="1200", street_name="Harbor Way",
              city="Portland", state="OR", postal_code="97209")


def required_for(path, method):
    spec = V.spec("rest")
    schema = spec["paths"][path][method]["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    return set(schema.get("required", [])), set(schema.get("properties", {}))


def main():
    V.sdk_banner()
    import app as recipe

    rec = V.Recorder()
    recipe.client.addresses._http = rec

    recipe.create_address(**FIELDS, address_type="Suite", address_number="4")
    recipe.client.phone_numbers._http = V.Recorder(
        responses=[{"data": [{"id": "other", "number": "+15550000000"},
                             {"id": NUMBER_ID, "number": "+15557654321"}]}])
    assert recipe.number_id("+15557654321") == NUMBER_ID
    (listing,) = recipe.client.phone_numbers._http.calls
    assert (listing["method"], listing["path"]) == ("GET", "/api/relay/rest/phone_numbers"), listing
    V.assert_documented("rest", "GET", "/api/relay/rest/phone_numbers", None)
    recipe.attach(NUMBER_ID, ADDRESS_ID)
    assert len(rec.calls) == 2, rec.calls
    create, attach = rec.calls

    assert (create["method"], create["path"]) == ("POST", ADDRESSES), create
    body = create["body"]
    required, props = required_for(ADDRESSES, "post")
    assert required <= set(body), sorted(required - set(body))
    assert set(body) <= props, sorted(set(body) - props)
    assert body["emergency_enabled"] is True, body
    assert body["country"] == "US", body
    assert {k: body[k] for k in FIELDS} == FIELDS, body
    assert body["address_type"] == "Suite" and body["address_number"] == "4", body
    V.assert_documented("rest", "POST", ADDRESSES, body)

    assert (attach["method"], attach["path"]) == ("POST", E911), attach
    assert attach["body"] == {"e911_address_id": ADDRESS_ID}, attach
    template = "/api/relay/rest/phone_numbers/{id}/e911_address"
    required, props = required_for(template, "post")
    assert required == {"e911_address_id"} and set(attach["body"]) == props, (required, props)
    V.assert_documented("rest", "POST", E911, attach["body"])

    print(f"ok: POST {ADDRESSES} with the spec's {len(required_for(ADDRESSES, 'post')[0])} "
          f"required fields plus emergency_enabled; GET the numbers list for the id; "
          f"POST {template} with e911_address_id")


if __name__ == "__main__":
    main()
