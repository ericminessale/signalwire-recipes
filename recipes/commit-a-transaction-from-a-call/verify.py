"""Prove the claim without a network.

Claim: the agent collects, confirms, and then commits once through a single
tool, and nothing is written before the confirmation is on record.

Proof: run the handlers in the platform's payload shape, threading
`global_data` the way the platform does, and assert the order book after each
step. Committing before any order, and committing before confirmation, each
refuse and write nothing. Changing the order after confirming resets the
confirmation. Committing after confirmation writes once and returns an order
id; committing again on the same call refuses with the same id and the book
still holds one order. A different call id gets its own order. The enum on
`set_order` limits the model's items to the catalogue, and the handler drops
anything else. Expected values live here, not in app.py.
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

# Expected values live here, not imported from app.py.
CATALOGUE = ["cargo-rack", "helmet", "puncture-kit"]
TOOLS = ["commit_order", "confirm_order", "set_order"]


class Session:
    """Threads global_data between tool calls the way the platform does."""

    def __init__(self, agent, call_id):
        self.agent, self.call_id, self.data = agent, call_id, {}

    def run(self, tool, **args):
        raw = {"call_id": self.call_id, "global_data": dict(self.data)}
        r = self.agent._execute_swaig_function(tool, args, call_id=self.call_id,
                                               raw_data=raw)
        for action in r.get("action", []):
            if "set_global_data" in action:
                self.data.update(action["set_global_data"])
        return r


def main():
    V.sdk_banner()
    import app as recipe

    agent = recipe.agent
    V.assert_basic_auth_from_env(agent)
    doc = json.loads(agent._render_swml())
    V.validate_swml(doc)
    ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]
    fns = {f["function"]: f for f in ai["SWAIG"]["functions"]}
    assert sorted(fns) == TOOLS, sorted(fns)
    enum = fns["set_order"]["parameters"]["properties"]["items"]["items"]["enum"]
    assert enum == CATALOGUE, enum

    book = recipe.ORDERS
    book.clear()
    s = Session(agent, "call-A")

    # commit with nothing on record: refused, nothing written
    r = s.run("commit_order")
    assert r["response"].startswith("INCOMPLETE") and "action" not in r, r
    assert book == {}

    # confirm with no order: refused
    r = s.run("confirm_order")
    assert r["response"].startswith("INCOMPLETE") and "action" not in r, r

    # the order, with one item that is not in the catalogue dropped
    r = s.run("set_order", items=["helmet", "puncture-kit", "unicycle"])
    assert r["action"] == [{"set_global_data": {
        "order": {"items": ["helmet", "puncture-kit"], "total": 101.5},
        "confirmed": False}}], r
    assert book == {}

    # commit before confirmation: refused, nothing written
    r = s.run("commit_order")
    assert r["response"].startswith("NOT_CONFIRMED") and "action" not in r, r
    assert book == {}

    # confirm, then change the order: the confirmation is gone again
    r = s.run("confirm_order")
    assert r["action"] == [{"set_global_data": {"confirmed": True}}], r
    r = s.run("set_order", items=["cargo-rack"])
    assert s.data["confirmed"] is False, s.data
    r = s.run("commit_order")
    assert r["response"].startswith("NOT_CONFIRMED"), r
    assert book == {}

    # confirm and commit: one write, one id
    s.run("confirm_order")
    r = s.run("commit_order")
    assert r["action"] == [{"set_global_data": {"order_id": "RC-1001"}}], r
    assert book == {"call-A": {"id": "RC-1001", "items": ["cargo-rack"], "total": 45.0}}

    # the model asks again: refused with the same id, still one order
    r = s.run("commit_order")
    assert r["response"].startswith("ALREADY_PLACED") and "RC-1001" in r["response"], r
    assert "action" not in r and len(book) == 1

    # another call is its own transaction
    t = Session(agent, "call-B")
    t.run("set_order", items=["helmet"])
    t.run("confirm_order")
    r = t.run("commit_order")
    assert r["action"] == [{"set_global_data": {"order_id": "RC-1002"}}], r
    assert sorted(book) == ["call-A", "call-B"]

    print(f"ok: {TOOLS} with the catalogue enum {CATALOGUE}; commit refused before "
          f"an order and before confirmation; a changed order drops the "
          f"confirmation; one commit per call id, a repeat returns the same id; "
          f"the book holds {len(book)} orders for two calls")


if __name__ == "__main__":
    main()
