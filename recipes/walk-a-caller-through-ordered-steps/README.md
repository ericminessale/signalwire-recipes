# Walk a caller through ordered steps

> Every step names one tool, and every step but the last names one next step, so the model is never offered a way to skip ahead or double back.

**Scenario:** recording a roadside assistance request, three questions in order

## What this demonstrates

A step is a prompt the model reads while that step is active, plus three fields
around it. `valid_steps` lists where the model's `next_step` tool can go.
`functions` lists the tools that exist while the step is active. `step_criteria`
is the sentence the runtime judges before it advances. The
[steps reference](https://developer.signalwire.com/swml/methods/ai/prompt/contexts/steps/)
documents all three. Each step below names exactly one tool, and each step but the
last names only the step after it, so the flow is a line.

Tool handlers accept the answers and write them to `global_data`. The model
proposes an answer; your handler decides whether it counts.

## How it works

Each step is declared once and carries its own edges.

```python
flow.add_step("location") \
    .add_section("Current Task", "Ask where the vehicle is.") \
    .set_step_criteria("save_location has accepted a location.") \
    .set_functions(["save_location"]) \
    .set_valid_steps(["vehicle"])
```

The last step sets `end` instead of `valid_steps`. What the platform receives:

```json
{"name": "location", "text": "...",
 "step_criteria": "save_location has accepted a location.",
 "functions": ["save_location"],
 "valid_steps": ["vehicle"]}
```

Call `set_functions` on every step. The SDK's own note on `set_functions` says a
step that does not declare `functions` inherits the previous step's set. It calls
that the most common bug in multi-step agents.

The handler judges the answer. A location under six characters returns
`INCOMPLETE` and writes nothing. A usable one emits `set_global_data`. The last
handler records the problem; nothing is dispatched, and the caller is told the
request is recorded.

The SDK closes the flow at build time. A `valid_steps` entry naming a step that
does not exist fails the context builder's `validate()`. The SDK catches that
error during render and logs it, so what you see is a schema error about a
missing prompt. The message naming the step is in the log.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/intake`.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

It renders and validates the SWML, then asserts the following.

- the three steps appear in order; each names one `functions` entry, and each but the last names one `valid_steps` entry
- no step can reach an earlier step or skip one
- the last step carries `end` and no `valid_steps`
- an inadequate answer returns `INCOMPLETE` with no action; a usable one emits `set_global_data`
- a step naming a destination that does not exist fails `validate()` and cannot render

## Limitations

A step is not a security boundary. `step_criteria` is a sentence the model judges,
and `valid_steps` shapes the tool it is offered. What the verifier proves is the
document: one tool per step, one edge per step. Anything that must not happen
early belongs in a handler.

`gather_info` is a shorter way to write a sequence. It is absent from the 3.0.1
schema and does not validate offline, so this recipe does not use it.

## What to change first

Give `vehicle` a `valid_steps` of `["problem", "location"]` and run the verifier.
It fails on the backward edge: the document now offers the model a way back.
