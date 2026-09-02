# Embed a call widget with no backend

> A `<sw-click-to-call>` element with a Click to Call token from the Dashboard and a destination address puts a call button on a page. No server of yours is in the call path.

**Scenario:** a bike shop's website that wants a "talk to the workshop" button without standing up anything to answer it

## What this demonstrates

The Click-to-Call widget guide embeds the button with one script tag and one
element. The guide is
https://signalwire.com/docs/browser-sdk/guides/click-to-call-widget. The token is "created from a Click
to Call resource in the dashboard", and the widget "routes through
embeds.signalwire.com automatically". So the page needs no backend of yours:
the Flask app here serves static HTML, holds no API token, and has one route.
The vendored REST spec also documents `POST /api/fabric/embeds/tokens`, "Create
guest embed token". Its one required field is `token`, "Click to Call Token",
and its `201` response carries a `token`. The SDK wraps it as
`client.fabric.tokens.create_embed_token`. That exchange is for a client of your
own, not for the widget.

## How it works

```python
PAGE = """...
  <script src="{script}"></script>
...
  <sw-click-to-call token="{token}" destination="{destination}" label="{label}"></sw-click-to-call>
..."""

def page(token=None, destination=None, label=None):
    return PAGE.format(script=WIDGET_SCRIPT,
                       token=html.escape(token or C2C_TOKEN, quote=True),
                       destination=html.escape(destination or DESTINATION, quote=True),
                       label=html.escape(label or LABEL, quote=True))
```

What the browser receives:

```html
<script src="https://unpkg.com/@signalwire/web-components/dist/embed/signalwire-web-components-embed.iife.js"></script>
<sw-click-to-call token="c2c_..." destination="/public/workshop" label="Talk to the workshop"></sw-click-to-call>
```

The three attribute values come from the environment, and the page escapes
them on the way in. A label with a quote in it therefore stays a label. The
destination is a Fabric address, such as a SWML script's or an AI agent's
`/public/...` address; the guide's example is `/public/support`.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: CLICK_TO_CALL_TOKEN, DESTINATION, LABEL
python app.py
```

In the Dashboard, open Tools, then Click to Call, and create a token; the guide
names that path. Put the token and the destination address in `.env`, open
`http://localhost:8080/`, and press the button. Nothing needs a public URL; the
page is static, and the call goes to SignalWire.

## Verify it

No network, no account.

```bash
cd ..                     # back to the recipe folder
python verify.py
```

The verifier drives the Flask app with its test client and parses the page. It
asserts the following.

- the page is served as HTML, loads exactly the widget script the guide names, and holds exactly one `sw-click-to-call` element
- that element's `token`, `destination` and `label` are exactly the configured values
- the page carries neither the project id nor the API token, and the app has exactly one route
- a label containing a quote is escaped, so it stays inside the attribute and adds no attribute of its own
- `exchange` makes one `POST` to the documented embeds tokens path with exactly `token`, the spec's one required field, described as a Click to Call token, and the spec's `201` response carries `token`

## Limitations

You prove the page and the documented exchange. Whether the button rings the
destination, and what the visitor hears, are the widget's and the platform's
side of a live call.

A Click to Call token is public by design: it sits in the page source. Scope
what it can dial in the Dashboard resource, not in the page.

## What to change first

Point `DESTINATION` at the address of your own agent, from
`let-a-browser-dial-your-agent-with-no-dashboard-setup`, and run the verifier.
It fails, because it pins its own destination; run the app instead, and the
button dials your agent.
