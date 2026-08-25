# Translate a call in real time

> Each side speaks their own language on one bridge.

**Scenario:** support without a language-matched agent

## What this demonstrates

Two people who share no language hold one conversation. The caller speaks
Spanish and hears English; the agent speaks English and hears Spanish. No
third party joins, no interpreter is scheduled, and neither side installs
anything. `live_translate` runs the translation inside the call itself.

This is a call-level verb, not an AI agent. There is no prompt to write and no
model to govern.

## How it works

`live_translate` opens a translation session, then `connect` bridges the second
party. The order matters: started after `connect`, the session covers only the
caller, and the agent's speech is never translated.

```yaml
- live_translate:
    action:
      start:
        from_lang: en-US
        to_lang: es-ES
        from_voice: Polly.Joanna
        to_voice: Polly.Lucia
        direction: [remote-caller, local-caller]
- connect: { to: "+15550100001" }
```

The schema requires `from_lang`, `to_lang` and `direction`, and two of those
carry the behaviour.

`direction` decides which legs are translated. Its values are `remote-caller`
and `local-caller`. Listing only one gives one-way translation, which is a
transcript read aloud rather than a conversation.

`from_voice` and `to_voice` decide what each side hears: the caller hears
`to_voice`, the agent hears `from_voice`. Omit one and that direction falls back
to the default voice.

With `live_events` on, your webhook receives partials while someone is still
speaking. Each final carries its direction and both strings, the words spoken
and the words the other side heard.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set PUBLIC_URL and AGENT_NUMBER
python app.py
```

Point a phone number's SWML webhook at `https://<your-host>/translate`.

## Verify it

No network, no account:

```bash
python verify.py
```

Both surfaces validate against the SWML schema. The verifier asserts:

- `live_translate` precedes `connect`, so the bridged leg is inside the session
- the schema's required `from_lang`, `to_lang` and `direction` are all present
- both `remote-caller` and `local-caller` are translated
- each direction names its own voice, and the two differ
- the webhook keeps finals with their direction, keeps the summary, drops partials

## Limitations

The action union is `start`, `stop`, `summarize` and `inject`. There is no
update, so changing the language pair mid-call means stopping the session and
starting a new one.

Translation is sequential: a side hears the other after the utterance completes,
not while it is being spoken. Long turns feel like long pauses, so tune
`vad_silence_ms` before blaming the network.

## What to change first

Set `direction` to `[remote-caller]` alone and call it. Only the caller is
translated, which is the difference between an interpreter and a subtitle.
