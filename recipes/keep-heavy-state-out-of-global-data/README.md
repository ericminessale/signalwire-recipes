# Keep heavy state out of global_data

> Per-call state lives server-side keyed by `call_id`. Only a count and a one-line summary go to `global_data`, and the handlers read the full record from the store.

**Scenario:** a mechanic phoning in a bike inspection, one finding at a time

## What this demonstrates

`global_data` travels with every tool call and the model can see it. That makes
it the right place for a short, AI-facing summary and the wrong place for a
growing record. This agent keeps the record in a store keyed by `call_id`, which
the platform posts with every tool call. It writes only a count and the list of
areas to `global_data`. A second tool reads the whole record back from the store.

## How it works

```python
def record_finding(self, args, raw_data):
    call_id = raw_data.get("call_id")
    findings = STORE.setdefault(call_id, [])
    findings.append({"area": area, "detail": detail})          # the full text
    r = FunctionResult(f"Recorded {area}. {len(findings)} findings so far.")
    r.add_action("set_global_data", {                          # the summary
        "findings": len(findings),
        "areas": ", ".join(f["area"] for f in findings)})
    return r
```

After the third finding, what the platform receives:

```json
{"response": "Recorded wheels. 3 findings so far.",
 "action": [{"set_global_data": {"findings": 3, "areas": "brakes, gears, wheels"}}]}
```

The three findings in the store run to several hundred bytes; the action stays
under 120. `read_back_report` reads `STORE[call_id]`, not `global_data`, so the
agent can recite every detail it was told without the model having carried any
of it.

`call_id` is the key because it is the one identifier the platform attaches to
every tool call for the life of the call. Two calls in flight at once get two
records.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/inspection/`, report three findings at
length, then ask for the report.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier runs the handlers with the platform's payload shape and asserts
the following.

- both tools render, and `area` carries the five areas as an `enum`
- three long findings on one call each emit `set_global_data` holding only the count and the areas, never the detail text
- each of those actions is 120 bytes of JSON or fewer, while the store for that call holds more than three times that
- a finding on a second call gets its own record, and the first call's record is unchanged
- `read_back_report` returns every detail from the store for its own call, with no action, and `INCOMPLETE` for a call with none
- an invalid finding writes nothing to the store

## Limitations

The store is a dictionary in the process. A restart loses it, and two replicas
would not share it; your version is a table keyed by `call_id`.

Nothing cleans the store up here. A real one expires a call's record after the
end-of-call POST. That POST is where `extract-structured-data-after-a-call`
picks up.

## What to change first

Put `detail` into the `set_global_data` action and run the verifier. The size
assertion fails on the first finding. That is the point: the record was about to
ride along with every tool call for the rest of the conversation.
