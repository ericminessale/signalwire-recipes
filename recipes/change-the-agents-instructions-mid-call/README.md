# Change the agent's instructions mid-call

> A tool result replaces the system prompt on the call in progress, summarising or dropping the earlier turns, with no transfer.

**Scenario:** a bicycle shop's front desk that becomes billing or the workshop once it knows why you called

## What this demonstrates

A tool result can carry a `context_switch` action. The platform replaces the
system prompt of the conversation that is already running, on the same call, with
no transfer and no second agent. You choose whether the turns so far are
summarised into the new context or dropped. The
[context switch guide](https://signalwire.com/docs/swml/guides/context-switch)
documents the action and its fields.

The SDK method is `switch_context`; the wire key is `context_switch`. The verifier
asserts the key and the complete payload.

## How it works

One agent takes the call, finds out what it is about, then hands over to itself.

```python
@AgentBase.tool(name="become_billing", description="...", parameters={...})
def become_billing(self, args, raw_data):
    return FunctionResult("Switching you to billing.").switch_context(
        system_prompt=BILLING_PROMPT, consolidate=True
    )
```

The function result the platform receives:

```json
{"response": "Switching you to billing.",
 "action": [{"context_switch": {
   "system_prompt": "You are now the billing specialist ...",
   "consolidate": true}}]}
```

`consolidate` asks the platform to summarise the conversation so far into the new
context. `full_reset` drops the history instead; `start_over` uses it. Both are
fields of the documented action object.

With `system_prompt` alone the SDK emits the prompt as a bare string. The bundled
schema documents `context_switch` as an object, so every switch in this recipe
passes `consolidate` or `full_reset` and gets the object form.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/front-desk`, say you are calling about a
refund, then ask about a repair. The billing prompt tells the model not to
discuss repairs.

## Verify it

No network, no account. The verifier proves the payload, not the live conversation.

```bash
python verify.py          # from the recipe folder, not python/
```

It renders and validates the SWML, runs all three handlers, and asserts the
following.

- each result equals its expected payload exactly: the response text and one `context_switch` object
- `become_billing` and `become_workshop` carry the new `system_prompt` with `consolidate: true`
- `start_over` carries `full_reset: true`
- no key at any depth of any result is `SWML`, `transfer` or `connect`

## Limitations

The switch replaces the prompt, not the toolset. Every tool on the agent stays
registered after the switch. To change which tools exist, use contexts and steps,
where `set_functions` scopes them per step.

`consolidate` is a summary the platform writes. A fact the specialist must have
exactly, such as an account number, should travel in `global_data` from a tool
handler rather than be trusted to survive summarisation.

## What to change first

Change `consolidate=True` to `full_reset=True` in `become_billing` and run the
verifier. The payload assertion fails, and on a call the billing specialist
starts with no memory of what the caller said at the front desk.
