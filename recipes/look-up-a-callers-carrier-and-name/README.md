# Look up a caller's carrier and name

> One GET returns a number's validity, formatting, country and type. `include=carrier,cnam` adds the carrier record and the caller-ID name, so a call can be enriched before anyone answers.

**Scenario:** a support line that wants to know who is calling before the agent picks up

## What this demonstrates

`GET /api/relay/rest/lookup/phone_number/{e164}` returns what the platform knows
about a number. The vendored REST spec describes `include` as "further number
information to include in the response, some of which are billable", with two
values: `carrier` for "full carrier information" and `cnam` for "Caller ID
information", joined by a comma. The SDK wraps the call as
`client.lookup.phone_number(e164, **params)`.

## How it works

```python
client = RestClient()

def enrich(e164):
    return client.lookup.phone_number(e164, include="carrier,cnam")

def check(e164):
    return client.lookup.phone_number(e164)
```

What the platform receives:

```
GET /api/relay/rest/lookup/phone_number/+15557654321?include=carrier,cnam
```

The spec's response schema carries `valid_number`, `e164`, the national and
international formatted forms, `country_code`, `timezones`, `number_type`, and
two objects that appear when asked for. `carrier` holds `lrn`, `spid`, `ocn`,
`lata`, `city`, `state`, `jurisdiction`, `lec` and `linetype`; `cnam` holds
`caller_id`. `check` leaves `include` off and pays for nothing extra.

A tool handler on an agent can call `enrich` with `caller_id_num` from the tool
POST and put `linetype` and `caller_id` into `global_data`, so the greeting can
use the name.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # project id, API token, space
python app.py +1XXXXXXXXXX
```

There is no server to expose; the script speaks to the REST API and exits. The
`carrier` and `cnam` includes are billable, per the spec.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, calls both helpers, and
asserts the following.

- `enrich` makes one `GET` to the documented lookup path for the number with `include=carrier,cnam` and nothing else
- `check` makes one `GET` to the same path with no query
- the path and the `include` parameter are documented, and the spec's description of `include` names `carrier` and `cnam`
- the spec's response schema carries `carrier` with `linetype`, `cnam`, `valid_number`, `e164` and `number_type`

## Limitations

The verifier proves the request and the documented response shape, not what a
lookup returns for a real number. CNAM data is a carrier database; a name is
absent for many numbers, and the spec marks both includes billable.

## What to change first

Change `include="carrier,cnam"` to `include="carrier"` and run the verifier.
The params assertion fails, which is the point: each include is a separate,
billable request for data, and you ask for exactly what you need.
