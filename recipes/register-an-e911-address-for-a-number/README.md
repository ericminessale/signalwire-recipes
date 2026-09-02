# Register an E911 address for a number

> Two POSTs and one GET: create an emergency address with the nine fields the spec requires, look up the number's id, and attach the address to the number.

**Scenario:** a US workshop that puts its street address behind the number its staff dial out on

## What this demonstrates

`POST /api/relay/rest/addresses` creates the address. The vendored REST spec
requires `label`, `country`, `first_name`, `last_name`, `street_number`,
`street_name`, `city`, `state` and `postal_code`. It takes `emergency_enabled`,
`auto_correct_address`, `address_type` and `address_number` as options. `POST
/api/relay/rest/phone_numbers/{id}/e911_address` with `e911_address_id` attaches
the address to a number.

The SDK wraps the first call as `client.addresses.create`. It has no wrapper for
the second in 3.0.1. The recipe sends that request through the `HttpClient` that
`RestClient` builds once and hands to every namespace
(`signalwire/rest/client.py:74-85`).

## How it works

```python
def create_address(label, first_name, last_name, street_number, street_name,
                   city, state, postal_code, country="US", *, address_type=None,
                   address_number=None, auto_correct_address=None):
    body = dict(label=label, country=country, ..., emergency_enabled=True)
    return client.addresses.create(**body)

def number_id(e164):
    for item in client.phone_numbers.list().get("data", []):
        if item.get("number") == e164:
            return item["id"]

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

The spec lists `address_type` as an enum: Apartment, Basement, Building,
Department, Floor, Office, Penthouse, Suite, Trailer or Unit. The number id is
the `id` of the phone number resource, which `number_id` reads from
`GET /api/relay/rest/phone_numbers`, not the number itself.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: your project id, API token and space
python -c "import app; print(app.create_address('<label>', '<first name>', '<last name>', '<street number>', '<street name>', '<city>', '<state>', '<postal code>'))"
python app.py +1XXXXXXXXXX <address_id>
```

Fill every placeholder in the first command with your own dispatchable US
address, and use a US number on your project in the second. This creates an
emergency location on your account, and a wrong one is worse than none. The spec's response schema for the address carries an `id`; pass it
to the second command with a number on your project.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, calls the helpers, and
asserts the following.

- `create_address` makes one `POST` to the documented addresses path
- its body contains every field in the spec's required list, which the verifier reads from the spec, plus `emergency_enabled: true` and the two optional fields passed
- every field in that body is a documented property
- `number_id` makes one `GET` to the documented numbers list and returns the id whose `number` matches
- `attach` makes one `POST` to the number's documented e911 path with exactly `e911_address_id`, the spec's whole required list for that call

## Limitations

The verifier proves the requests. Address validation, and whether the platform
accepts the address as an emergency location, happen on the live call to the
API.

There is no SDK method for the attach call in 3.0.1, so the recipe reaches for
the shared HTTP client. A later SDK may add a wrapper.

This recipe is for US addresses and US numbers. `country` defaults to `US`, the
only value it was written and verified with; check the spec's
`emergency_enabled` behaviour before trying another.

## What to change first

Drop `postal_code` from the `create` body and run the verifier. The required-list
assertion fails, which is the point: the spec, not this recipe, decides what an
emergency address must carry.
