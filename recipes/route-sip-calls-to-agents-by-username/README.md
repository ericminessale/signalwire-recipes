# Route SIP calls to agents by username

> Calls to different SIP usernames on one domain land on different agents behind one AgentServer. A routing callback reads the username from the request body and the SDK answers with a 307 to that agent's route.

**Scenario:** a PBX trunk that sends `sales@` and `workshop@` to one webhook and expects two different agents

## What this demonstrates

`register_routing_callback(fn, path)` on an agent mounts `path` under the
agent's route. When the platform POSTs there, the SDK calls `fn(request, body)`;
a returned route becomes a 307 redirect and `None` means "carry on and serve
this agent". `SWMLService.extract_sip_username(body)` reads the username out of
`call.to`: the part before `@` of a `sip:` URI, the digits of a `tel:` URI, or
the bare value. A dictionary from username to route is the whole router.

In 3.0.1 the callback must be registered before `server.register(agent)`,
because that call copies the agent's routes into the app once. The server's own
`setup_sip_routing()` registers its callback after that copy and mounts no
`/sip` endpoint, which the verifier's design works around and Limitations
records.

## How it works

```python
USERNAMES = {"sales": "/sales", "orders": "/sales", "support": "/support",
             "workshop": "/support"}

def route_by_username(request, body):
    username = SWMLService.extract_sip_username(body)
    return USERNAMES.get((username or "").lower())

class DeskAgent(AgentBase):
    def __init__(self, name, route, role):
        super().__init__(name=name, route=route)
        self.prompt_add_section("Role", role)
        self.register_routing_callback(route_by_username, path="/sip")
```

What the platform sends and gets back for a call to the workshop:

```
POST /sales/sip
{"call": {"call_id": "...", "to": "sip:workshop@pbx.example.com", "from": "..."}}

HTTP/1.1 307 Temporary Redirect
Location: /support
```

A 307 keeps the method and body, so the platform re-POSTs the same request to
the support agent, which serves its SWML. A username the map does not know
returns `None` from the callback, and the agent that received the request
serves its own document.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point the SIP domain's handler at
`https://<user>:<password>@<your-host>/sales/sip/`; either agent's `/sip` path
routes for both. Dial `sip:workshop@<your-domain>` and `sip:sales@<your-domain>`.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier builds the server, drives its FastAPI app with the test client, and
asserts the following.

- `extract_sip_username` returns the username of a `sip:` URI, the number of a `tel:` URI, and `None` for a body with no call
- each of the four usernames, POSTed to either agent's `/sip` path, answers 307 with the mapped agent's route in `Location`
- an unknown username and a `tel:` destination answer 200 with the receiving agent's own SWML, which validates and names the sales desk
- a POST without basic auth is refused

## Limitations

`AgentServer.setup_sip_routing()` exists in 3.0.1 but mounts nothing: it
registers its callback after `server.register()` has already copied each
agent's routes. Register the callback on the agent first, as this recipe does.

Routing is by username only. The domain part of the URI is ignored, so two
domains sharing a username share an agent.

## What to change first

Move `self.register_routing_callback(...)` out of `DeskAgent.__init__` and call
it on each agent after `server.register()`. Run the verifier: every `/sip` POST
is a 404, which is the 3.0.1 ordering rule made visible.
