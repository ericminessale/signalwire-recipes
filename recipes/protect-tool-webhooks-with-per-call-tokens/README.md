# Protect tool webhooks with per-call tokens

> Every tool webhook request must carry a token minted for that call and that function. Anything else is refused before a handler runs.

**Scenario:** an account line where a refund must not be triggered from outside the call that asked

## What this demonstrates

Every tool with `secure=True`, the default, renders its `web_hook_url` with a
`__token` query parameter. The SDK mints that token for this call and this
function. It is an HMAC over the call id, the function name, an expiry and a
nonce, signed with a key that exists only in your process. A request that carries
a token from another call, for another function, altered, or expired is refused.

The SDK checks a token only when one is present. A request that omits it is not
refused by the token layer. The basic-auth credentials that gate the route sit in
the same URL an attacker captured, so they do not close that gap either. This agent
adds one rule of its own: no token, no handler.

## How it works

You write nothing to get the tokens. The document rendered for a call carries,
per secure function:

```json
{"function": "issue_refund",
 "web_hook_url": "https://user:pass@host/accounts/swaig/?__token=Y2FsbC1BLmlz..."}
```

The token decodes to `call_id.function.expiry.nonce.signature`. The SDK's
`SessionManager.validate_token` checks the function name, then the expiry, then
recomputes the signature, then compares the call id. Any mismatch returns a
refusal in the function result and the handler does not run.

The rule you add sits on the app the SDK builds:

```python
app = agent.get_app()

@app.middleware("http")
async def require_token(request, call_next):
    if request.url.path.rstrip("/") == tool_path and request.method == "POST":
        if "__token" not in request.query_params:
            return JSONResponse(status_code=403,
                                content={"response": "A per-call token is required."})
    return await call_next(request)
```

`get_app()` returns the FastAPI app that `serve()` runs, so the middleware is in
front of every tool request. `token_expiry_secs` on the constructor sizes the
window; 900 seconds is the default.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/accounts`.

## Verify it

No network, no account. The verifier drives the agent's own HTTP app with
FastAPI's test client, the way the platform would, and records every handler run.

```bash
python verify.py          # from the recipe folder, not python/
```

It renders the document for one call, takes the refund tool's token off its URL,
and POSTs to the tool endpoint, asserting the following.

- without basic auth the route answers 401 and nothing runs
- the token on its own call runs the handler once and returns the refund text
- the same token on another call, for the other function, or with a character changed gets the SDK's refusal and runs nothing
- a token minted with a closed expiry window gets the same refusal
- a request with no token gets a 403 from the middleware and runs nothing

The verifier never prints a URL, because the URLs carry your basic-auth credentials.

## Limitations

The middleware is the recipe's rule, not the SDK's. Without it, a request with no
token reaches the handler as soon as it passes basic auth.

The signing key is generated per process unless you pass `secret_key` to the
agent. Two replicas behind a load balancer will each refuse the other's tokens.

## What to change first

Delete the `require_token` middleware and run the verifier. The last check fails:
a request with no token now runs `issue_refund`, which is the gap this recipe
exists to close.
