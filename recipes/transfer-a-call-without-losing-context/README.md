# Transfer a call without losing context

> State and identity travel with the call, so the next leg already knows who this is.

## What this demonstrates

The caller gives their name and reason once. When the call moves to a second agent,
that agent already has both - no re-authentication, no repeated intake, and no
serialising context into a URL and hoping the other side parses it.

The platform holds interaction state, so the handoff carries it. On a stateless
CPaaS this is application code you write and maintain yourself.

## How it works

Data written to the shared context during intake is still present after the
transfer. The receiving agent reads it on its first turn.

## Limitations

Context travels with the call, not with the caller. Recognising a returning caller
across separate calls is a different problem and needs durable storage keyed to the
contact.

## What to change first

Add a field during intake and read it from the receiving agent to find the boundary
of what survives.
