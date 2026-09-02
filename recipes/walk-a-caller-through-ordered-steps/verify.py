"""Prove the claim without a network.

Claim: every step names one tool, and every step but the last names one next
step, so the model is never offered a way to skip ahead or double back. Every
answer is accepted by a handler rather than read out of the transcript.

Proof: render the SWML and assert `valid_steps`, `functions`, `step_criteria`
and `end` on each step under `ai.prompt.contexts`, the keys the platform reads.
Run the handlers and assert the `set_global_data` action they emit, and that an
inadequate answer writes nothing. Then show the flow is closed at build time:
the SDK's context builder refuses a `valid_steps` entry that names a step
which does not exist, and the document cannot render.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))

import verifylib as V  # noqa: E402

# what a reader's .env supplies; without it the SDK generates a password that
# exists only in this process and the number's webhook gets a 401
os.environ.setdefault("SWML_BASIC_AUTH_USER", "signalwire")
os.environ.setdefault("SWML_BASIC_AUTH_PASSWORD", "verify-only-password")

# Expected values live here, not imported from app.py. The order is the claim.
ORDER = ["location", "vehicle", "problem"]
TOOL_FOR = {"location": "save_location", "vehicle": "save_vehicle",
            "problem": "save_problem"}


def main():
    V.sdk_banner()
    from app import ClaimIntakeAgent

    agent = ClaimIntakeAgent()
    V.assert_basic_auth_from_env(agent)
    doc = json.loads(agent._render_swml())
    V.validate_swml(doc)
    ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]

    steps = ai["prompt"]["contexts"]["default"]["steps"]
    assert [s["name"] for s in steps] == ORDER, [s["name"] for s in steps]
    by = {s["name"]: s for s in steps}

    # Each step offers exactly one destination and exactly one tool.
    for i, name in enumerate(ORDER):
        s = by[name]
        assert s["functions"] == [TOOL_FOR[name]], (name, s.get("functions"))
        assert s["step_criteria"], (name, "a step with no criteria never advances")
        if i < len(ORDER) - 1:
            assert s["valid_steps"] == [ORDER[i + 1]], (name, s.get("valid_steps"))
            assert "end" not in s, s
        else:
            assert "valid_steps" not in s, s
            assert s["end"] is True, s

    # No step can reach an earlier one or jump forward two.
    for i, name in enumerate(ORDER[:-1]):
        allowed = set(by[name]["valid_steps"])
        assert not allowed & set(ORDER[:i + 1]), (name, "can go backwards")
        assert not allowed & set(ORDER[i + 2:]), (name, "can skip ahead")

    # All three tools exist on the agent; the step decides which is visible.
    names = sorted(f["function"] for f in ai["SWAIG"]["functions"])
    assert names == sorted(TOOL_FOR.values()), names

    # Handlers accept or refuse; the platform state key is set_global_data.
    r = agent._execute_swaig_function(
        "save_location", {"location": "M62 westbound near junction 24"}, call_id="c1")
    assert r["action"] == [{"set_global_data": {
        "location": "M62 westbound near junction 24"}}], r
    r = agent._execute_swaig_function("save_location", {"location": "here"}, call_id="c1")
    assert r["response"].startswith("INCOMPLETE"), r
    assert "action" not in r, r  # an unusable answer writes nothing

    r = agent._execute_swaig_function("save_vehicle", {"vehicle": "blue"}, call_id="c1")
    assert r["response"].startswith("INCOMPLETE") and "action" not in r, r
    r = agent._execute_swaig_function(
        "save_vehicle", {"vehicle": "blue Ford Transit"}, call_id="c1")
    assert r["action"] == [{"set_global_data": {"vehicle": "blue Ford Transit"}}], r

    r = agent._execute_swaig_function(
        "save_problem", {"problem": "flat tyre, no spare"}, call_id="c1")
    assert r["action"] == [{"set_global_data": {"problem": "flat tyre, no spare"}}], r

    # The flow is closed at build time. The context builder names the bad
    # destination; the SDK catches that error during render and logs it, and
    # the render then fails because the ai verb has no prompt. Both are
    # asserted, because the second is what a developer actually sees.
    from signalwire import AgentBase

    class Broken(AgentBase):
        def __init__(self):
            super().__init__(name="broken", route="/broken")
            self.prompt_add_section("Role", "test")
            flow = self.define_contexts().add_context("default")
            flow.add_step("one").add_section("Task", "x") \
                .set_valid_steps(["nowhere"])

    broken = Broken()
    try:
        broken._contexts_builder.validate()
    except ValueError as e:
        assert "nowhere" in str(e), e
    else:
        raise AssertionError("validate() accepted a valid_steps entry naming a "
                             "step that does not exist")
    try:
        broken._render_swml()
    except Exception as e:  # the SDK re-raises this as a schema error
        assert "prompt" in str(e) or "nowhere" in str(e), e
    else:
        raise AssertionError("a flow with an unknown destination rendered")

    print(f"ok: {' -> '.join(ORDER)}, one tool per step "
          f"{[TOOL_FOR[n] for n in ORDER]}, no backward or skip edges; "
          f"inadequate answers write nothing; an unknown destination is refused "
          f"at build time")


if __name__ == "__main__":
    main()
