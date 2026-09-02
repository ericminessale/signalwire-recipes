# Verify a caller ID for outbound calls

> Three REST calls take a number you own elsewhere through verification as an outbound caller ID: register it, send back the code the verification call reads out, and redial if the code was missed.

**Scenario:** a shop that wants outbound calls to show its long-standing mobile number

## What this demonstrates

`POST /api/relay/rest/verified_caller_ids` registers a number and a display name.
`PUT /api/relay/rest/verified_caller_ids/{id}/verification` submits the
`verification_code`. `POST` to that same verification path places the
verification call again. The SDK wraps the three as `create`,
`submit_verification` and `redial_verification` on `client.verified_callers`.

The vendored REST spec, `tools/openapi/rest.json`, is what the verifier checks
the three requests against. It marks `number` as the one required field on
create and `verification_code` as required on the PUT. The response carries
`id`, `number`, `name`, `verified`, `verified_at` and `status`.

## How it works

```python
client = RestClient()

def start(number, name):
    return client.verified_callers.create(number=number, name=name)

def confirm(caller_id, code):
    return client.verified_callers.submit_verification(caller_id, verification_code=code)

def resend(caller_id):
    return client.verified_callers.redial_verification(caller_id)
```

What the platform receives, in order:

```json
POST /api/relay/rest/verified_caller_ids
{"number": "+15557654321", "name": "Shop mobile"}

PUT  /api/relay/rest/verified_caller_ids/<id>/verification
{"verification_code": "482913"}

POST /api/relay/rest/verified_caller_ids/<id>/verification
```

The id in the second and third paths is the `id` the first response returned.
Once `verified` is true, the number is a value you can pass as `from` when you
place an outbound call.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # project id, API token, space
python app.py start +1XXXXXXXXXX "Shop mobile"     # the phone rings and reads a code
python app.py confirm <id> <code>
python app.py resend <id>                          # if nobody caught the code
```

Use a number you can answer. There is no server to expose; each command speaks
to the REST API and exits.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, calls the three helpers,
and asserts the following.

- `start` makes one `POST` to the documented path with exactly `number` and `name`
- `confirm` makes one `PUT` to the id's verification path with exactly `verification_code`
- `resend` makes one `POST` to that verification path with no body
- every body field is documented and every required field is present, per the vendored spec
- the spec's required list for create is exactly `number`

## Limitations

The verifier proves the three requests. Whether the phone rings and what the
code is are the platform's side of a live run.

A verified caller ID is a number you own elsewhere. Numbers on your SignalWire
project need no verification to be used as `from`.

## What to change first

Remove `name=name` from `start` and run the verifier. The exact-body assertion
fails, though the spec would still accept the request: `name` is optional and
`number` is the only required field.
