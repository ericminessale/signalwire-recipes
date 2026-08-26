# Route a call to an AI agent

> Bind a number to a resource that points at your agent, not to a URL.

**Scenario:** putting a support line in front of an agent you already run

## What this demonstrates

Two requests bind a number you own to a SWML webhook resource that holds your agent's
URL. The first creates the resource. The second attaches the number's phone route to
it.

The number is bound to the resource rather than the URL. Moving the agent is
then one update of the resource, however many numbers point at it.

## How it works

`POST /api/fabric/resources/swml_webhooks` creates the resource.
`primary_request_url` is the only required field, and it is where SignalWire
fetches the document when a call arrives.

```python
resource = client.fabric.swml_webhooks.create(
    name="support agent",
    primary_request_url=AGENT_URL,
    primary_request_method="POST",
    fallback_request_url=FALLBACK_URL,
)
```

The fallback is worth setting even though it is optional: it gives SignalWire a second
URL to try when the primary request fails. Host it apart from the agent, or it shares
the outage it exists to cover.

Then the number. `assign_phone_route` posts to the resource's `phone_routes`,
taking the route id and a handler:

```python
client.fabric.resources.assign_phone_route(
    resource["id"], phone_route_id=PHONE_ROUTE_ID, handler="calls",
)
```

`handler` is `calls` or `messages`. The same resource type serves both, so a
number routed for calls is not routed for texts, and the mistake is silent
until somebody texts you.

The second request uses the id the first returned. That ordering is the whole
shape of the recipe: there is no way to bind a number to a resource that does
not exist yet.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env   # credentials, AGENT_URL, PHONE_ROUTE_ID
python app.py
```

`PHONE_ROUTE_ID` comes from the number you already own; see
`buy-a-number-and-point-it-at-your-app` for getting one.

## Verify it

No network, no account:

```bash
python verify.py          # from the recipe folder, not python/
```

With the HTTP layer replaced by a recorder, the verifier asserts:

- exactly two requests, in dependency order
- the create is a documented POST to `swml_webhooks` carrying the agent URL as
  `primary_request_url`, checked against `tools/openapi/rest.json`
- a fallback URL is set
- the bind is a documented POST to that resource's `phone_routes`
- `handler` is `calls`, not `messages`
- the bind uses the id the create returned, not a value from configuration

## Limitations

This points a number at an agent. It does not check the agent answers: a
resource happily holds a URL that 404s, and the failure shows up as a call that
goes nowhere.

Basic auth on your agent has to be in the URL you register, because the
resource is the only place SignalWire learns it.

## What to change first

Set `handler` to `messages` and call the number. Nothing answers, because the
number is now routed for texts and the call has no handler at all.
