# Start from a prefab agent

> A complete receptionist or survey agent runs from a prefab class and a dozen lines of configuration.

**Scenario:** a bicycle shop's front desk and its workshop follow-up survey

## What this demonstrates

The SDK ships complete agents as classes. You pass configuration, not a prompt.
The prefab writes its prompt sections, registers its tools with their handlers,
sets its voice, and for the receptionist wires the transfer. `ReceptionistAgent`
takes a list of departments; `SurveyAgent` takes a list of typed questions. Each
is a dozen lines in `app.py`.

What you configure becomes enforcement. The department names become an `enum` on
the transfer tool, so the model cannot name a department that is not on the list.
A rating question's `scale` becomes the bound the validator applies.

## How it works

```python
ReceptionistAgent(
    departments=[
        {"name": "sales", "description": "Pricing, availability and new orders",
         "number": "+15551230001"},
        {"name": "workshop", "description": "Repairs, servicing and appointments",
         "number": "+15551230002"},
    ],
    greeting="Ridgeline Cycles, how can I help?",
)
```

The rendered document carries two tools you did not write, `collect_caller_info`
and `transfer_call`, a prompt you did not write, the voice `rime.spore`, and
`transfer_summary` in `params`. The departments sit in `global_data`, and the
transfer tool's `department` parameter is `{"enum": ["sales", "workshop"]}`. On a
transfer the handler emits a `connect` verb for the department's number with
`transfer: "true"`, and sets `post_process` so the goodbye is spoken first.

```python
SurveyAgent(
    survey_name="Workshop follow-up",
    questions=[{"id": "rating", "type": "rating", "scale": 5,
                "text": "From one to five, how would you rate the work?"}, ...],
)
```

The survey registers `validate_response` and `log_response`, sets a `post_prompt`,
and rejects a rating of seven on a five-point scale. The constructor accepts
four question types, `rating`, `multiple_choice`, `yes_no` and `open_ended`, and
raises at construction if a rating lacks `scale` or a multiple choice lacks
`options`.

`PREFAB` chooses which one this process serves. Both are built in `app.py` so the
verifier proves both.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # set SWML_BASIC_AUTH_PASSWORD and the numbers
python app.py                    # PREFAB=survey python app.py for the other
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. Point a number's SWML webhook at
`https://<user>:<password>@<your-host>/reception` or `/survey`.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

It builds both agents, renders and validates each, and asserts the following.

- the receptionist exposes `collect_caller_info` and `transfer_call`, with `transfer_summary` set and the voice `rime.spore`
- the department enum equals your list; a transfer's whole result equals the expected payload: `connect` to the configured number with `transfer: "true"`
- an unlisted department is refused with the prefab's exact message, and nothing is dialled
- the survey exposes `validate_response` and `log_response`, sets a `post_prompt`, and carries your questions with their types and scale
- a rating of seven is refused; a four returns the prefab's exact valid and recorded messages

## Limitations

A prefab is a starting point with opinions. The receptionist takes `voice` as a
constructor argument, but its prompt text and tool descriptions are its own, and
changing them means subclassing. `SurveyAgent` has no `voice` argument at all.
When the configuration surface stops fitting, write the agent directly; the
prefabs are short and readable in `signalwire/prefabs/`.

The receptionist transfers by phone number. A SIP address works in `number` too,
because it is handed to `connect` unchanged.

## What to change first

Add `{"name": "legal", ...}` to `DEPARTMENTS` and run the verifier. The enum
assertion fails, which is the point: the enum is derived from your list, and the
model's choices are exactly the departments you configured.
