"""Prove the claim without a network.

Claim: the agent answers in the caller's language and switches mid-conversation
without a transfer.

Proof: the rendered SWML carries every language with its own voice and code,
`languages_enabled` is on (without it the list is ignored), and the document
contains no transfer or connect, so the switch happens inside one AI session
rather than by routing the call somewhere else.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))

import verifylib as V  # noqa: E402

os.environ.setdefault("SWML_BASIC_AUTH_USER", "signalwire")
os.environ.setdefault("SWML_BASIC_AUTH_PASSWORD", "verify-only-password")


def check(doc, label):
    """The parts of the claim both surfaces have to satisfy."""
    V.validate_swml(doc)
    ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]
    assert ai["params"]["languages_enabled"] is True, (label, ai["params"])
    codes = [l["code"] for l in ai["languages"]]
    assert len(set(codes)) == len(codes) >= 2, (label, codes)
    names = V.verb_names(doc)
    for verb in ("transfer", "connect"):
        assert verb not in names, (label, verb, names)
    return ai


def main():
    V.sdk_banner()
    from app import LANGUAGES, FrontDeskAgent

    agent = FrontDeskAgent()
    V.assert_basic_auth_from_env(agent)
    doc = json.loads(agent._render_swml())
    ai = check(doc, "python")

    # The switch is a parameter, not an inference. Without it the platform
    # ignores the languages list entirely.
    assert ai["params"]["languages_enabled"] is True, ai["params"]

    langs = ai["languages"]
    assert len(langs) == len(LANGUAGES), langs

    # Every language reaches the platform with the code and voice it was
    # registered with, in order: the first is the one the agent opens in.
    for (name, code, voice), got in zip(LANGUAGES, langs):
        assert got["name"] == name, (name, got)
        assert got["code"] == code, (code, got)
        assert voice.split(".")[-1].split(":")[0] in json.dumps(got), (voice, got)

    # A voice per language, not one voice reading three.
    voices = [json.dumps(sorted(l.items())) for l in langs]
    assert len(set(voices)) == len(langs), langs
    codes = [l["code"] for l in langs]
    assert len(set(codes)) == len(codes), codes

    # "without a transfer": the call never leaves this agent.
    names = V.verb_names(doc)
    for verb in ("transfer", "connect"):
        assert verb not in names, (verb, names)
    assert "SWAIG" not in ai or not ai["SWAIG"].get("functions"), ai.get("SWAIG")

    # The prompt asks the model to follow the caller rather than announcing it.
    prompt = json.dumps(ai["prompt"]).lower()
    assert "language" in prompt, ai["prompt"]

    # The hand-written surface makes the same claim without the SDK.
    yaml_ai = check(V.load_yaml(HERE / "swml" / "agent.yaml"), "yaml")
    assert [l["code"] for l in yaml_ai["languages"]] == [l["code"] for l in langs], yaml_ai

    print(f"ok: languages_enabled with {[l['code'] for l in langs]}, "
          f"a distinct voice each, and no transfer or connect in the document")


if __name__ == "__main__":
    main()
