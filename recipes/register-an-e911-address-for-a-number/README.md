# Register an E911 address for a number

> Two REST calls: create an emergency address with the nine fields the spec requires and `emergency_enabled` on, then attach it to a number by the address id.

**Scenario:** a workshop that puts its street address behind the number its staff dial out on

## What this demonstrates

`POST /api/relay/rest/addresses` creates the address. The vendored REST spec
requires `label`, `country`, `first_name`, `last_name`, `street_number`,
`street_name`, `city`, `state` and `postal_code`, and takes `emergency_enabled`,
`auto_correct_address`, `address_type` and `address_number` as options. `POST
/api/relay/rest/phone_numbers/{id}/e911_address` with `e911_address_id` attaches
the address to a number. The SDK wraps the first call as `client.addresses.create`.
It has no wrapper for the second in 3.0.1, so the recipe sends that request
through the HTTP client the namespaces share.

## How it works

```python
def create_address(label, first_name, last_name, street_number, street_name,
                   city, state, postal_code, country="US", **optional):
    return client.addresses.create(
        label=label, country=country, first_name=first_name, last_name=last_name,
        street_number=street_number, street_name=street_name, city=city,
        state=state, postal_code=postal_code, emergency_enabled=True, **optional)

def attach(phone_number_id, address_id):
    return client.addresses._http.post(
        f"/api/relay/rest/phone_numbers/{phone_number_id}/e911_address",
        body={"e911_address_id": address_id})
```

What the platform receives:

```json
POST /api/relay/rest/addresses
{"label": "Ridgeline Cycles workshop", "country": "US",
 "first_name": "Dana", "last_name": "Whitfield",
 "street_number": "1200", "street_name": "Harbor Way", "address_type": "Suite",
 "address_number": "4", "city": "Portland", "state": "OR", "postal_code": "97209",
 "emergency_enabled": true}

POST /api/relay/rest/phone_numbers/<number id>/e911_address
{"e911_address_id": "<address id>"}
```

`address_type` is an enum in the spec: Apartment, Basement, Building,
Department, Floor, Office, Penthouse, Suite, Trailer or Unit. The number id is
the `id` of the phone number resource, not the number itself.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # project id, API token, space
python -c "import app; print(app.create_address('Shop', 'Dana', 'Whitfield', '1200', 'Harbor Way', 'Portland', 'OR', '97209'))"
python app.py <phone_number_id> <address_id>
```

The first command prints the created address, including its `id`. There is no
server to expose; both commands speak to the REST API and exit.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, calls both helpers, and
asserts the following.

- `create_address` makes one `POST` to the documented addresses path
- its body contains every field in the spec's required list, read from the spec, plus `emergency_enabled: true` and the two optional fields passed
- every field in that body is a documented property
- `attach` makes one `POST` to the number's documented e911 path with exactly `e911_address_id`, which is the spec's whole required list for that call

## Limitations

The verifier proves the two requests. Address validation, and whether the
platform accepts the address as an emergency location, happen on the live call
to the API.

There is no SDK method for the attach call in 3.0.1, so the recipe reaches for
the namespaces' shared HTTP client. A later SDK may add a wrapper.

## What to change first

Drop `postal_code` from the `create` body and run the verifier. The required-list
assertion fails, which is the point: the spec, not this recipe, decides what an
emergency address must carry.
