# Send an SMS

> The three-line version, plus what to do when it fails.

## What this demonstrates

Sending a message is trivial. Handling the outcome is the part tutorials skip - a
queued message is not a delivered one, and carrier rejections arrive later on a
status webhook rather than in the API response.

## How it works

The create call returns once the message is accepted. Delivery, failure and carrier
filtering arrive afterwards on the status callback.

## Limitations

A 201 means accepted, never delivered. Treat the status webhook as the source of
truth, and make the handler idempotent - it can fire more than once for the same
message.

## What to change first

Send to an invalid number and watch which failure surfaces synchronously versus on
the webhook.
