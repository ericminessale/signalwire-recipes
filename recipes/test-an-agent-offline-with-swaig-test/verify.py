"""Prove the claim without a network.

Claim: the SDK's `swaig-test` CLI loads an agent file and, with no number,
tunnel or account, dumps the SWML the platform would fetch, lists the tools,
and runs a tool with the arguments you give it.

Proof: run the CLI as a subprocess against python/app.py three times. The
`--dump-swml --raw` output parses as JSON, validates against the bundled
schema, and carries the one tool. `--list-tools` names the tool and its
parameter. `--exec check_hours --day saturday` prints the handler's exact
response, and an invalid day prints its refusal. Expected values live here,
not in app.py.
"""
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import verifylib as V  # noqa: E402

# what a reader's .env supplies; without it the SDK generates a password that
# exists only in this process and the number's webhook gets a 401
os.environ.setdefault("SWML_BASIC_AUTH_USER", "signalwire")
os.environ.setdefault("SWML_BASIC_AUTH_PASSWORD", "verify-only-password")

APP = HERE / "python" / "app.py"
SATURDAY = "On Saturday the shop is open 9 to 5."
INVALID = "INVALID: ask for a day of the week."


def swaig_test(*args):
    """Run the CLI the way a developer does, as its own process."""
    import signalwire
    env = dict(os.environ)
    # the directory that holds the `signalwire` package, so the child sees
    # the same SDK this verifier loaded
    env["PYTHONPATH"] = str(pathlib.Path(signalwire.__file__).parent.parent)
    cmd = [sys.executable, "-m", "signalwire.cli.swaig_test_wrapper", str(APP), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, (args, r.returncode, r.stderr[-800:])
    return r.stdout


def main():
    V.sdk_banner()

    # the document the platform would fetch, straight from the CLI
    out = swaig_test("--dump-swml", "--raw")
    doc = json.loads(out[out.index("{"):])
    V.validate_swml(doc)
    ai = next(v for v in doc["sections"]["main"] if "ai" in v)["ai"]
    assert [f["function"] for f in ai["SWAIG"]["functions"]] == ["check_hours"], ai["SWAIG"]

    # the tool inventory, with its parameter
    out = swaig_test("--list-tools")
    assert "check_hours" in out and "day (string) (required)" in out, out

    # the handler, run with arguments and fake call data
    out = swaig_test("--exec", "check_hours", "--day", "saturday")
    assert SATURDAY in out, out
    out = swaig_test("--exec", "check_hours", "--day", "someday")
    assert INVALID in out, out

    print(f"ok: swaig-test dumped valid SWML with ['check_hours'], listed the tool "
          f"and its required 'day', and ran it: {SATURDAY!r} and the INVALID refusal")


if __name__ == "__main__":
    main()
