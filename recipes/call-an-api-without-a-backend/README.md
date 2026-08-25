# Call an API without a backend

> The tool is data, so SignalWire makes the request and you deploy nothing.

**Scenario:** an independent bookshop confirming titles by ISBN

## What this demonstrates

A tool that reaches a third-party API, with no service of yours in the path.
The HTTP request, the response template and the failure path are fields in the
document SignalWire runs. There is no handler, no callback URL and nothing to
keep online.

A normal tool gives the platform a URL to call back to. A DataMap tool gives it
the request to make instead.

## How it works

`DataMap` builds a function definition whose body is a `data_map` rather than a
`url`. `${args.x}` is substituted into the request before it is sent;
`${response.x}` reads the parsed JSON body on the way back.

```python
DataMap("look_up_book")
    .parameter("isbn", "string", "The 10 or 13 digit ISBN.", required=True)
    .webhook("GET", "https://openlibrary.org/isbn/${args.isbn}.json")
    .output(FunctionResult("ISBN ${args.isbn} is ${response.title}."))
    .error_keys(["error"])
    .fallback_output(FunctionResult("I could not reach the book catalogue."))
```

Where each result lands is the part worth reading twice. `.output()` attaches to
the webhook directly above it, so a chain of webhooks each carry their own. Only
`.fallback_output()` sits at the top of the `data_map`, and it is spoken when
every webhook has failed. `.error_keys()` names the JSON keys whose presence
means failure even though the request returned 200.

## Run it

```bash
cd python
pip install -r requirements.txt
python app.py
```

Point a phone number's SWML webhook at `https://<your-host>/catalogue`. Open
Library needs no key, so it works as written.

## Verify it

No network, no account:

```bash
python verify.py
```

It renders the SWML and asserts:

- the function carries a `data_map` and no `url` of ours
- the request is `GET` with `${args.isbn}` templated into the path
- the webhook's own output holds the `${response.title}` template
- the top-level output is the fallback, with no `${response.*}` in it
- the SDK refuses to run the tool locally, naming SignalWire as the executor
- the hand-written SWML surface is the same artifact, not a paraphrase

## Limitations

Templating is the only transform available. There is no place to put a
conditional or a unit conversion, so an API whose response needs reshaping wants
a normal tool with a handler (`give-an-agent-a-tool`).

Anything in `headers` ships inside the document SignalWire serves. For an API
that needs a secret, weigh that before choosing a DataMap.

## What to change first

Point the webhook at a URL that returns 404 and call the agent. The fallback is
what the caller hears, which is the difference between a degraded answer and
silence.
