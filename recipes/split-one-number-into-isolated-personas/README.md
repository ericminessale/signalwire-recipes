# Split one number into isolated personas

> One number reaches sales, support or billing through the default context. Each persona is an isolated context whose step names only its own tools, so the other desks' tools are structurally absent while it is on the line.

**Scenario:** a bicycle shop with one number and three desks that must not blur into each other

## What this demonstrates

Contexts do two jobs here. `isolated: true` on a persona context means, per the
bundled schema, that entering it "resets conversation history to only the
system prompt". The support desk does not inherit what the caller told sales.
`functions` on each persona's step names only that desk's tool. The
three tools all live on the agent; the step is what decides which one exists on
a given turn. The default context, where every call starts, names no tools and
lists the three personas in `valid_contexts`. The schema requires a context
named `default`.

The [contexts reference](https://developer.signalwire.com/swml/methods/ai/prompt/contexts/)
documents contexts and steps; `isolated` is the context field the schema adds
for the wipe.

## How it works

```python
triage = contexts.add_context("default")
triage.add_step("ask") \
    .set_functions([]) \
    .set_valid_contexts(["sales", "support", "billing"])

for name, (prompt, tools) in PERSONAS.items():
    ctx = contexts.add_context(name)
    ctx.set_isolated(True)
    ctx.add_section("Role", prompt)
    ctx.add_step("help").set_functions(tools).set_valid_contexts(["default"]).set_end(True)
```

What the platform receives for the support persona, trimmed:

```json
{"support": {"isolated": true,
             "pom": [{"title": "Role", "body": "You are the workshop support desk ..."}],
             "steps": [{"name": "help", "functions": ["book_repair"],
                        "valid_contexts": ["default"], "end": true, ...}]}}
```

The model moves between contexts with the `change_context` tool the platform
offers it, limited to the names in `valid_contexts`. Entering support wipes the
history and offers `book_repair` alone; `quote_price` and `look_up_invoice`
are not in the step's `functions`, so the model is not offered them.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/front-door/`, ask for support, then ask
for a price.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

It renders and validates the SWML, reads `ai.prompt.contexts`, and asserts the
following.

- the contexts are exactly `default`, `sales`, `support` and `billing`
- the default context's step names no functions and lists exactly the three personas in `valid_contexts`, and it is not isolated
- each persona context carries `isolated: true` and a `Role` section naming its desk
- each persona has one step whose `functions` is exactly its own tool, with `valid_contexts` back to `default` and `end: true`
- no persona step names another persona's tool
- all three tools exist on the agent, so the steps are what scopes them
- the bundled schema documents `isolated` on a context as a boolean that resets conversation history

## Limitations

A step is not a security boundary. `functions` shapes what the model is offered;
a handler that must not run for the wrong desk checks `global_data` itself, as
`require-verification-before-unlocking-tools` shows.

Isolation wipes what the caller already said. A fact the next desk needs, such
as a name, should travel in `global_data` from a handler before the switch.

## What to change first

Add `"quote_price"` to the support step's `functions` and run the verifier. The
cross-persona assertion fails, which is the point: a desk's tools are exactly
the list on its step, and nothing else decides it.
