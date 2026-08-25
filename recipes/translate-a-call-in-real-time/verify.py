"""Prove the claim without a network.

Claim: two people speaking different languages hear each other translated on one
bridge, with a chosen voice per direction.

Proof: both surfaces validate against the SWML schema; live_translate starts
before connect so the bridged leg is inside the session; both directions are
translated; each direction names its own voice; and the webhook handler keeps
finals with the direction they came from, keeps the summary, and drops partials.
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))
os.environ.setdefault("PUBLIC_URL", "https://recipes.example.test")

import verifylib as V  # noqa: E402


def check(doc, label):
    V.validate_swml(doc)
    names = V.verb_names(doc)
    # after connect, the leg the bridge adds would be outside the session
    assert names.index("live_translate") < names.index("connect"), (label, names)
    start = V.first(doc, "live_translate")["action"]["start"]
    # the schema's required trio
    for key in ("from_lang", "to_lang", "direction"):
        assert start.get(key), (label, key, start)
    assert start["from_lang"] != start["to_lang"], (label, start)
    # one language each way is not a translated conversation
    assert set(start["direction"]) == {"remote-caller", "local-caller"}, (label, start)
    # the claim's "a chosen voice per direction"
    assert start["from_voice"] and start["to_voice"], (label, start)
    assert start["from_voice"] != start["to_voice"], (label, start)
    return start


def main():
    V.sdk_banner()
    import app as recipe

    start = check(recipe.build().get_document(), "python")
    assert start["webhook"] == "https://recipes.example.test/translation", start
    check(V.load_yaml(HERE / "swml" / "agent.yaml"), "yaml")

    # the webhook keeps what is worth keeping and drops the rest
    client = recipe.app.test_client()
    events = [
        {"call_id": "c1", "type": "partial", "text": "necesito ay"},
        {"call_id": "c1", "direction": "remote-caller",
         "text": "necesito ayuda", "translated": "I need help"},
        {"call_id": "c1", "direction": "local-caller",
         "text": "of course", "translated": "por supuesto"},
        {"call_id": "c1", "type": "summary", "summary": "Caller asked for help."},
    ]
    for e in events:
        assert client.post("/translation", json=e).status_code == 204

    turns = recipe.turns["c1"]
    assert len(turns) == 2, turns                      # the partial was dropped
    assert {t["direction"] for t in turns} == {"remote-caller", "local-caller"}
    assert turns[0]["spoken"] == "necesito ayuda", turns
    assert turns[0]["heard"] == "I need help", turns   # each side hears the other
    assert recipe.summaries["c1"] == "Caller asked for help."

    print(f"ok: live_translate({start['from_lang']} -> {start['to_lang']}, "
          f"{start['from_voice']}/{start['to_voice']}) before connect, both legs; "
          f"{len(turns)} finals kept, partial dropped, summary kept")


if __name__ == "__main__":
    main()
