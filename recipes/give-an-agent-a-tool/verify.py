"""Prove the claim without a network.

Claim: a Python function with a JSON-schema signature becomes something the
model can call mid-call, and your code decides what it gets back.

Proof: the rendered SWML carries the function in ai.SWAIG.functions with the
exact parameter schema, its LLM-facing descriptions and its fillers; running the
handler returns a spoken answer for a known order and a typed NOT_FOUND state
for an unknown one, with no invented delivery date.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
sys.path.insert(0, str(HERE / "python"))

import verifylib as V  # noqa: E402


def main():
    V.sdk_banner()
    from app import ORDERS, OrderAgent

    agent = OrderAgent()
    doc = json.loads(agent._render_swml())
    V.validate_swml(doc)
    ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]

    # The tool reaches the platform under the key it will be called by.
    funcs = {f["function"]: f for f in ai["SWAIG"]["functions"]}
    assert "get_order_status" in funcs, list(funcs)
    fn = funcs["get_order_status"]

    # The JSON schema is what the model fills in.
    params = fn["parameters"]
    assert params["type"] == "object", params
    assert list(params["properties"]) == ["order_id"], params
    assert params["required"] == ["order_id"], params

    # Descriptions are LLM-facing: an undescribed parameter is the #1 cause
    # of a tool that exists but never gets called.
    assert len(fn["description"]) > 40, fn["description"]
    assert params["properties"]["order_id"]["description"], params

    # Fillers cover the latency of the lookup.
    assert fn["fillers"]["en-US"], fn

    # A known order: the handler formats for speech, the prompt does not.
    r = agent._execute_swaig_function(
        "get_order_status", {"order_id": "48815"}, call_id="c1")
    said = r["response"]
    assert "out for delivery" in said and "Britewave" in said, r
    assert "today before 8pm" in said, r

    # An unknown order: a typed state that tells the model what to do, and
    # no date anywhere in the reply for it to read out.
    r = agent._execute_swaig_function(
        "get_order_status", {"order_id": "00000"}, call_id="c1")
    miss = r["response"]
    assert miss.startswith("NOT_FOUND"), miss
    assert "read it back" in miss or "read the" in miss, miss
    for order in ORDERS.values():
        assert order["eta"] not in miss, miss

    print(f"ok: get_order_status exposed with {list(params['properties'])} "
          f"(required {params['required']}); known order answered, "
          f"unknown order returns {miss.split(':')[0]}")


if __name__ == "__main__":
    main()
