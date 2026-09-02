# Place an outbound AI call

> One REST `dial` carries the agent's SWML in the request, and two `ai` params make it an outbound conversation: `direction: outbound`, and `wait_for_user: true` so the agent waits for the callee to speak first.

**Scenario:** a workshop calling a customer to say their bike is ready

## What this demonstrates

`POST /api/calling/calls` with `command: dial` originates the call. The request
carries the document the call runs on answer, so nothing is fetched from you.
That document is an ordinary `AgentBase` rendered with `_render_swml()`. Two
entries in its `ai.params` change the shape of the conversation. The
[ai params reference](https://signalwire.com/docs/swml/reference/ai/params)
says `direction` "forces the direction of the call to the assistant". It says
`wait_for_user: true` means the "agent will wait for the user to speak first".

## How it works

```python
class ReminderAgent(AgentBase):
    def __init__(self):
        super().__init__(name="reminder", route="/reminder")
        self.prompt_add_section("Role", "You are calling from Ridgeline Cycles ...")
        self.set_params({"direction": "outbound", "wait_for_user": True,
                         "outbound_attention_timeout": 20000})

def place(to):
    return client.calling.dial(**{
        "from": FROM, "to": to, "swml": json.loads(agent._render_swml()),
        "status_url": f"{PUBLIC_URL}/call-status",
        "status_events": ["ringing", "answered", "ended"], "timeout": 25})
```

What the platform receives, trimmed:

```json
{"command": "dial",
 "params": {"from": "+15550001111", "to": "+15552223333", "timeout": 25,
            "swml": {"version": "1.0.0", "sections": {"main": [{"answer": {}},
              {"ai": {"prompt": {"pom": [...]},
                      "params": {"direction": "outbound", "wait_for_user": true,
                                 "outbound_attention_timeout": 20000}}}]}}}}
```

`outbound_attention_timeout` is how long the agent waits for the callee before
prompting, in milliseconds; the schema allows 10,000 to 600,000. `dial` takes
either `swml` or `url`; this recipe inlines the document because the agent has
no tools to serve. An agent with tools needs to be running at a public URL for
its webhooks, and `url` would point the dial at it.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # project id, API token, space, your number
python app.py +15552223333
```

The number you call from must be a voice-enabled number on your project.
`status_url` receives the lifecycle events; point `PUBLIC_URL` at a host you
control or remove the two status keys.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, calls `place()`, and
asserts the following.

- exactly one `POST` to the documented calling path with `command: dial`
- every dial parameter is a documented property of the SWML dial variant, and the required ones are present
- `to` and `from` carry the configured numbers, and the document travels as `swml`, not `url`
- the inline document validates against the bundled schema and opens with the agent's `Role` section
- `ai.params` carry `direction: outbound`, `wait_for_user: true`, and an `outbound_attention_timeout` inside the documented range
- `status_events` uses only documented event names

## Limitations

The verifier proves the request. Whether the callee speaks first, and what the
agent then says, is a live call.

Answering machines answer too. `wait_for_user` makes the agent wait for the
machine's greeting to end; pair with `detect-an-answering-machine` when a
voicemail should get a different message.

## What to change first

Remove `"direction": "outbound"` from `set_params` and run the verifier. The
params assertion fails, which is the point: without it the platform treats the
agent as answering an inbound call.
