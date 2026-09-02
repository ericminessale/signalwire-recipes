# Check consent before an outbound call

> No outbound call is placed to a number without a consent record and inside the permitted local calling window. The check is code, and it runs before the `dial`, so a refused call is never a request.

**Scenario:** a workshop that calls customers when their bikes are ready, and only the ones who asked

## What this demonstrates

The platform's part is one `dial` on `POST /api/calling/calls`. The recipe is
the ordering around it. `place()` looks the number up in your consent store and
converts the current time to the callee's zone with `zoneinfo`. It checks that
time against a window. Any failure raises `NoConsent` with the reason, and
`client.calling.dial` is never reached. The person you did not have consent to
call never hears a ring, and your logs never show a request.

## How it works

```python
def allowed(number, now=None):
    record = CONSENT.get(number)
    if not record:
        return "no consent on record"
    if not record["consented"]:
        return "consent withdrawn"
    local = (now or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo(record["tz"]))
    if not WINDOW[0] <= local.time() <= WINDOW[1]:
        return f"outside the calling window, it is {local:%H:%M} in {record['tz']}"
    return None

def place(number, message, now=None):
    reason = allowed(number, now)
    if reason:
        raise NoConsent(f"not calling {number}: {reason}")
    return client.calling.dial(**{"from": FROM, "to": number, "timeout": 25, "swml": ...})
```

What the platform receives, and only when every check passed:

```json
{"command": "dial",
 "params": {"from": "+15550001111", "to": "+15557654321", "timeout": 25,
            "swml": {"version": "1.0.0", "sections": {"main": [
              {"answer": {}}, {"play": {"url": "say:Your bike is ready."}}, {"hangup": {}}]}}}}
```

The window is judged in the callee's zone, which is part of the consent record.
A caller in Los Angeles at 21:30 is refused even when it is 04:30 tomorrow on
the server. `CONSENT` here is a dictionary. Yours is a table with the date, the
channel and the wording the person agreed to, because that is what a regulator
asks for.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: your project id, API token, space and number
python app.py +1XXXXXXXXXX       # a number in CONSENT with consented true
```

There is no server to expose; the script speaks to the REST API and exits. A
refused number exits with the reason and no request.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, fixes the clock, and
asserts the following.

- a number with no record raises `NoConsent` saying so, and the recorder sees no request
- a number whose consent was withdrawn does the same
- a consented number at 21:30 local time does the same, with the local time in the reason
- the window is the callee's: the same instant is 10:00 in Los Angeles and passes
- the consented number in the window makes exactly one `POST` to the documented calling path with `command: dial`
- the dial params are documented properties of the SWML dial variant, the required ones are present, and the inline SWML validates

## Limitations

This is the ordering, not the law. Which hours count, what consent must say,
and how long a record is good for are yours to decide with counsel, and vary by
jurisdiction.

The store is in memory. Pair with `handle-opt-outs-yourself` to record a STOP
as a withdrawal.

## What to change first

Swap the order in `place()` so `dial` runs before `allowed()`, and run the
verifier. The first refusal assertion fails because a request was recorded,
which is the failure this recipe exists to prevent.
