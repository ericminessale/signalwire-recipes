# Push events from an agent to the browser

> A tool result carries a SWML `user_event` whose `event` is any JSON object the handler chooses. The bundled schema describes the verb as sending events to the connected client on the call.

**Scenario:** a booking page that highlights the slot the caller picked, the moment the agent holds it

## What this demonstrates

`FunctionResult.swml_user_event(event)` wraps a `user_event` verb in a one-verb
SWML document and adds it as a `SWML` action on the tool result. The bundled
schema says `user_event` "allows the user to set and send events to the
connected client on the call". It notes the verb is "commonly used with the
browser-sdk" and that "the event object can be any valid JSON object". The
handler decides what happened and the event carries the facts; the model only
gets a sentence.

## How it works

```python
def hold_slot(self, args, raw_data):
    slot = args.get("slot")
    if slot not in SLOTS:
        return FunctionResult("INVALID: that slot is not on the page.")
    return FunctionResult(f"Holding {SLOTS[slot]} for the caller.").swml_user_event(
        {"type": "slot_held", "slot": slot, "label": SLOTS[slot], "held_for_seconds": 300})
```

The function result the platform receives:

```json
{"response": "Holding Thursday 2pm for the caller.",
 "action": [{"SWML": {"version": "1.0.0", "sections": {"main": [
   {"user_event": {"event": {"type": "slot_held", "slot": "thu-14",
                             "label": "Thursday 2pm", "held_for_seconds": 300}}}]}}}]}
```

`user_event` requires `event`; the schema rejects the verb without one. The
`slot` parameter carries an `enum` of the ids on the page. The handler refuses
anything else with no action, so the page never hears about a hold that did
not happen.

The `swml/` surface fires a `user_event` from a plain document, before the `ai`
verb, so the page knows the call was answered. Your backend can push the same
shape mid-call with the REST command `calling.user_event`, whose params take
`event`.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a Browser SDK client's
destination at an address that runs
`https://<user>:<password>@<your-host>/booking/`. Subscribe the page to user
events, pick a slot by voice, and watch the page.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

It renders and validates the SWML, runs the handler, and asserts the following.

- the tool's `slot` parameter carries the three slot ids as an `enum`
- a valid slot returns the exact payload: one `SWML` action holding one `user_event` with the exact `event` object
- that inline document validates against the bundled schema
- a `user_event` with no `event` fails the schema
- an unknown slot returns `INVALID` with no action
- the plain-SWML surface validates and its verbs are `answer`, `user_event`, `ai`, with the exact event

## Limitations

The verifier proves the document. How a page receives the event is the client
side of a live call. The Browser SDK's documentation covers the call a page
subscribes with.

A `user_event` has no delivery result. If the page must acknowledge, have it
call your backend.

## What to change first

Remove `"label": SLOTS[slot]` from the event and run the verifier. The exact
payload assertion fails. On a live call the page would have to look the label
up itself, so put in the event everything the page needs to render.
