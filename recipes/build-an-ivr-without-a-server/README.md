# Build an IVR without a server

> A call flow is a SWML document you hand to the platform, described in the spec as the document the flow should execute, so no server of yours serves it. One POST creates it from a `title`, a `relayml` document and the `flow_data` the spec pairs with it. One POST points a number at it by `phone_route_id` with the `calling` handler.

**Scenario:** a bike shop that wants "press 1 for sales, 2 for the workshop" on its main number and nothing to keep running

## What this demonstrates

The vendored REST spec's `POST /api/fabric/resources/call_flows` requires one
field, `title`, and takes `relayml`, "The calling SWML document this Call Flow
should execute". That sentence is the serverless part: the flow executes the
document, and nothing of yours serves it.
`POST /api/fabric/resources/{id}/phone_routes` requires `phone_route_id` and
`handler`, an enum of `calling` and `messaging`. Its prose says "incoming
`calls` or `messages`"; the enum is what the API accepts.
The document has four top-level verbs. They are `answer`, a `prompt` whose
schema requires `play` and collects one digit, a `switch` whose schema requires
`variable` and `case`, and `hangup`. You reach the REST calls as
`client.fabric.call_flows.create` and `client.fabric.resources.assign_phone_route`.

## How it works

```python
service.add_verb("prompt", {"play": f"say:{MENU}", "max_digits": 1, "initial_timeout": 8})
service.add_verb("switch", {
    "variable": "prompt_value",
    "case": {digit: [{"connect": {"to": number, "timeout": 25}}]
             for digit, number in DESKS.items()},
    "default": [{"play": {"url": f"say:{FALLBACK}"}}],
})

def deploy(title="Ridgeline Cycles IVR"):
    return client.fabric.call_flows.create(title=title, relayml=build().get_document())

def point_number(resource_id, e164):
    return client.fabric.resources.assign_phone_route(
        resource_id, phone_route_id=number_id(e164), handler="calling")
```

What the platform receives:

```http
POST /api/fabric/resources/call_flows
{"title": "Ridgeline Cycles IVR",
 "relayml": {"version": "1.0.0", "sections": {"main": [
   {"answer": {}},
   {"prompt": {"play": "say:Thanks for calling ...", "max_digits": 1, "initial_timeout": 8}},
   {"switch": {"variable": "prompt_value",
               "case": {"1": [{"connect": {"to": "+1555...", "timeout": 25}}],
                        "2": [{"connect": {"to": "+1555...", "timeout": 25}}]},
               "default": [{"play": {"url": "say:Sorry, that was not an option. Goodbye."}}]}},
   {"hangup": {}}]}}}

POST /api/fabric/resources/<resource_id>/phone_routes
{"phone_route_id": "<id of your number>", "handler": "calling"}
```

`prompt_value` holds the digit the prompt collected, so `switch` reads it by
name. `SWMLService.add_verb` raises `SchemaValidationError` for a verb the
bundled schema rejects, so a wrong field fails on your machine, not after
deployment. `number_id` looks the number up with the spec's `filter_number`
and compares exactly.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: credentials and the two desk numbers
python app.py document           # the SWML, to read
python app.py deploy             # prints the resource, including its id
python app.py point <resource_id> +1XXXXXXXXXX
```

There is no server to expose or keep running; the script speaks to the REST API
and exits, and the platform runs the document. Call the number and press 1.

## Verify it

No network, no account.

```bash
cd ..                     # back to the recipe folder
python verify.py
```

The verifier validates the document and swaps the SDK's HTTP layer for a
recorder. It asserts the following.

- the document validates and its verbs are `answer`, `prompt`, `switch`, `hangup`
- the prompt is exactly the menu, one digit and an eight-second initial timeout; the switch reads `prompt_value`, connects 1 and 2 to their desks with a 25-second timeout, and defaults to the fallback
- `add_verb` raises `SchemaValidationError` for a `prompt` with no `play`, and the document keeps its four verbs
- `deploy` makes one `POST` to the documented call flows path with exactly `title` and that document as `relayml`
- `point_number` makes one `GET` of the phone numbers list with exactly `filter_number` and picks the exact match over a near miss
- it then makes one `POST` to the documented phone routes path with exactly `phone_route_id` and `handler: calling`, and asserts `calling` is in the spec's enum
- the spec requires exactly `title` on the flow and exactly `phone_route_id` and `handler` on the route, and says `relayml` and `flow_data` travel together or not at all
- the spec describes `relayml` as the SWML document the flow should execute
- the bundled schema requires `play` on `prompt`, and `variable` and `case` on `switch`

## Limitations

You prove the document and the requests. What the caller hears, and whether a
desk answers, are the platform's side of a live call.

`flow_data` is the Call Flow Builder's own canvas state, opaque to the API.
The spec says to send it with `relayml` or send neither, so the script sends a
small descriptor beside the document. A flow deployed this way has no diagram
to edit in the Dashboard; the document is the source.

## What to change first

Add a third desk to `DESKS` under `"3"` and run the verifier. The switch
assertion fails, because the verifier pins two cases. Add the case there too.
The same document then deploys with three.
