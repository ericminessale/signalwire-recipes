# Scope an agent's tools per step

> At each point in the conversation the model can only see the tools you allowed there.

## What this demonstrates

The model cannot call a tool that is not exposed at the current step. The tool is
absent from its world rather than discouraged by an instruction, so neither a
persistent caller nor a prompt injection can reach it.

This is the difference between a rule and a constraint. A prompt saying "do not
transfer before taking a name" is a preference the model may ignore under
pressure. A step that does not list `transfer_to_human` in its functions makes
transferring unavailable.

## Limitations

Step *advancement* is model-evaluated against the step criteria. Tool
*visibility* is not. If the order itself must be guaranteed, force the transition
from inside the tool handler rather than trusting the criteria.

## What to change first

Add a third step and give it a tool the earlier steps must not reach. Then try to
talk the agent into using it early.
