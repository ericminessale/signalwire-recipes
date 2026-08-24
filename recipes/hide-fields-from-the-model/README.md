# Hide fields from the model

> Load the whole record, expose a curated slice, and keep the rest out of the prompt entirely.

## What this demonstrates

The agent answers questions about a customer while never receiving that customer's
risk score, internal notes, or margin. Those fields are dropped server-side before
anything reaches the prompt.

This is stronger than instructing the model to stay quiet about them. A field the
model never received cannot be leaked, summarised, inferred aloud, or extracted by
a caller who asks cleverly.

## How it works

The tool handler loads the full record from your own system, then builds an explicit
allowlist projection. Only the projection is returned to the model.

## Limitations

Anything you put in the projection is in the prompt, permanently, for that call. Add
fields deliberately - a projection that grows to match the record defeats the point.

## What to change first

Add a field to the record but not to the projection, then try to get the agent to
reveal it.
