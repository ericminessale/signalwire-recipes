# Inject a message into a live AI call

> One REST command, `calling.ai_message`, pushes a system instruction, a `global_data` merge or a full reset into a conversation that is already running, addressed by call id.

**Scenario:** your CRM finishes a lookup after the call started and tells the agent who is on the line

## What this demonstrates

`POST /api/calling/calls` with `command: calling.ai_message` reaches into a live
AI session. The body carries the call `id` at the top level and a `params`
object. With `role: system` and `message_text`, the text is an instruction the
model follows from its next turn. The same command takes `global_data` to merge
keys into the session, or `reset` to drop the history under a new system prompt.

The vendored OpenAPI spec, `tools/openapi/rest.json`, describes the `system`
role as injecting "instructions or context that modify the AI's behavior
mid-conversation without the caller hearing it". The verifier checks every
request against that spec.

## How it works

```python
client = RestClient()

def nudge(call_id, instruction):
    return client.calling.ai_message(call_id, role="system", message_text=instruction)

def share(call_id, data):
    return client.calling.ai_message(call_id, global_data=data)

def restart(call_id, system_prompt):
    return client.calling.ai_message(
        call_id, reset={"full_reset": True, "system_prompt": system_prompt})
```

What the platform receives for `nudge`:

```json
{"command": "calling.ai_message",
 "id": "6d3f4a0e-2b1c-4e7a-9f0d-1c2b3a4d5e6f",
 "params": {"role": "system",
            "message_text": "The caller is a returning customer. Skip the identity questions."}}
```

The SDK's `calling` namespace sends every call command to the same path and
puts the call id in `id`, which the spec marks required for this command. The
`role` enum is `system`, `user` or `assistant`; `user` injects text as if the
caller said it, and `assistant` as if the agent did.

Your backend learns the call id from the agent: every tool webhook and status
callback carries `call_id`.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # project id, API token, space
python app.py <call_id> "The caller is a returning customer."
```

Take the call id from a tool webhook or a status callback of a call that is
running an AI agent. There is no server to expose; the script speaks to the
REST API and exits.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier swaps the SDK's HTTP layer for a recorder, calls the three helpers,
and asserts the following.

- each helper makes exactly one `POST` to the documented calling path
- each body equals `{"command": "calling.ai_message", "id": <call id>, "params": ...}` with the exact params
- the spec marks `command`, `id` and `params` required for this command, and every param sent is documented
- `role` is one of the documented enum values

## Limitations

The verifier proves the request, not the model's reaction. Whether the next
turn follows the instruction is the model's behaviour on a live call.

A `user` role message makes the model respond as if the caller spoke. Use it
for testing, not in production flows where the transcript is a record.

## What to change first

Change `role="system"` to `role="operator"` in `nudge` and run the verifier.
The enum assertion fails, which is the point: the three roles are the whole
vocabulary.
