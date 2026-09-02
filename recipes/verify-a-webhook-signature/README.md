# Verify a webhook signature

> A request whose `X-Signalwire-Signature` header does not match hex(HMAC-SHA1(signing_key, url + raw_body)) is refused with 403 before any route runs. A matching one, or a matching `X-Signalwire-SHA256-Signature`, is served.

**Scenario:** a public webhook that must never run a document for a request SignalWire did not send

## What this demonstrates

SignalWire signs the requests it makes to your webhooks. The SWML webhook
security guide documents two headers. `X-Signalwire-Signature` is "HMAC-SHA1,
hex encoded" and arrives on every signed request. `X-Signalwire-SHA256-Signature`
is "HMAC-SHA256, hex encoded" and arrives on call requests. The signed payload
is "the request URL concatenated directly with the raw request body, with no
separator", so the formula is `hex(HMAC(signing_key, url + raw_body))`. You
find the key in the Dashboard under API Credentials, as Signing Key
(https://signalwire.com/docs/swml/guides/webhook-security).

The check runs in a Flask `before_request` hook, so it runs before routing. A
request that fails it never reaches your code, not even a 404.

## How it works

```python
def expected(key, url, raw_body, digest):
    return hmac.new(key.encode(), url.encode() + raw_body, digest).hexdigest()

def verify(headers, url, raw_body, key=None):
    key = key or SIGNING_KEY
    for header, digest in DIGESTS.items():          # SHA-256 first, then SHA-1
        sent = headers.get(header)
        if sent:
            return hmac.compare_digest(sent, expected(key, url, raw_body, digest))
    return False

@app.before_request
def gate():
    url = WEBHOOK_URL + ("?" + request.query_string.decode() if request.query_string else "")
    if not verify(request.headers, url, request.get_data()):
        abort(403)
```

Two choices matter. The URL comes from `WEBHOOK_URL`, the address you gave
SignalWire, not from the request: a tunnel or a proxy rewrites what Flask sees,
and the platform signed the one you configured. The guide says the URL includes
the query string, so the hook appends the request's. And `compare_digest` does
the comparison in constant time.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: SIGNALWIRE_SIGNING_KEY and WEBHOOK_URL
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 8080 with a
tunnel such as ngrok, and set `WEBHOOK_URL` to `https://<your-host>/webhook`,
exactly as you enter it in the Dashboard. Point a number's SWML webhook at that
URL and call it. Then send the same URL a `curl` with no header and read the
403.

## Verify it

No network, no account.

```bash
cd ..                     # back to the recipe folder
python verify.py
```

The verifier drives the Flask app with its test client and a signing key of its
own. It asserts the following.

- a body signed with SHA-1 over `url + body` is served, and the reply is a SWML document that validates with `answer`, `play`, `hangup`
- a body signed with SHA-256 alone is served, and when both headers arrive the SHA-256 one decides
- the two hex digests are 40 and 64 characters
- no header, a body altered by one byte, a signature from another key, a signature over `url + "\n" + body`, a wrong SHA-256 and an empty header are each refused with 403
- a request with a query string is served only when the signature covers the query string
- an unknown path is 403, not 404, because the gate runs before routing
- `verify()` on its own agrees with the app, so you can call it outside Flask

## Limitations

The verifier signs with its own key, so it proves the arithmetic and the gate,
not that a given production request came from SignalWire. That proof is the
signature on your real traffic against your real key.

The guide says the URL "excludes basic auth credentials on call requests" and
includes them on messaging requests "as configured". Set `WEBHOOK_URL` to match
the kind of webhook you serve.

## What to change first

Change the separator: sign over `url + "\n" + raw_body` in `expected()` and run
the verifier. Every served request becomes a 403 and the "a separator" case is
served instead. The formula is the platform's, not yours.
