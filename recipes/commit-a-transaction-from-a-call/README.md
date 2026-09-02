# Commit a transaction from a call

> The agent collects, confirms, and then commits once through a single tool. Nothing reaches the order book before the caller's confirmation is on record, and a second commit on the same call returns the first order's id.

**Scenario:** a bicycle shop taking accessory orders by phone

## What this demonstrates

Three tools, one write. `set_order` records the items in `global_data` and
marks the order unconfirmed. `confirm_order` reads it back and marks it
confirmed. `commit_order` writes to the order book once, and only when
`confirmed` is true in the `global_data` the platform posted with the call.

The model proposes each step. The handlers decide whether the step is allowed,
from state they wrote themselves. No sequence of model calls can write an
order the caller did not confirm.

## How it works

```python
def commit_order(self, args, raw_data):
    data = raw_data.get("global_data") or {}
    call_id = raw_data.get("call_id")
    if call_id in ORDERS:
        return FunctionResult(f"ALREADY_PLACED: order {ORDERS[call_id]['id']} is on file.")
    if not data.get("order"):
        return FunctionResult("INCOMPLETE: take the order first.")
    if data.get("confirmed") is not True:
        return FunctionResult("NOT_CONFIRMED: read the order back and get a yes.")
    ORDERS[call_id] = {"id": order_id, **data["order"]}
```

Each refusal is a response with no action, so the model hears why and nothing
changes. `set_order` always emits `"confirmed": false` alongside the order:

```json
{"response": "Order noted: helmet, puncture-kit, total 101.50. Read it back ...",
 "action": [{"set_global_data": {"order": {"items": ["helmet", "puncture-kit"],
                                           "total": 101.5},
                                 "confirmed": false}}]}
```

So a caller who confirms and then changes their mind has to confirm again. The
order book is keyed by `call_id`, which makes the commit idempotent per call:
a repeated `commit_order` returns the id already on file.

The `items` parameter carries an `enum` of the catalogue, so the model cannot
name an item that does not exist, and the handler drops anything outside it
anyway.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/orders/`, order a helmet, and try to get
it placed without saying yes.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

The verifier threads `global_data` between tool calls the way the platform
does and asserts the order book after each step.

- the three tools render, and `set_order` carries the catalogue as an `enum`
- `commit_order` before any order, and `confirm_order` before any order, each return `INCOMPLETE` with no action; the book is empty
- `set_order` drops an item outside the catalogue and emits the order with `confirmed: false`
- `commit_order` before confirmation returns `NOT_CONFIRMED`; the book is empty
- confirming and then changing the order resets `confirmed` to false, and the commit is refused again
- confirming and committing writes one order and returns its id; a second commit on the same call returns `ALREADY_PLACED` with that id, and the book still holds one
- a second call id gets its own order

## Limitations

The order book is a dictionary in the process. Your version writes to a system
that can itself refuse a duplicate, keyed by `call_id`, because a restart
between two commits would forget the first.

`global_data` is the platform's copy of the state, posted with each tool call.
A tool the caller reaches through a different agent on the same call would not
see it.

## What to change first

Delete the `NOT_CONFIRMED` check in `commit_order` and run the verifier. The
commit-before-confirmation assertion fails and the book has an order the caller
never agreed to, which is the failure this recipe exists to prevent.
