"""Route calls by dialed number or time.

One SWML webhook serves several numbers. SignalWire fetches the document with
the inbound call webhook the vendored REST spec documents: a JSON body whose
`call` carries `to`, "The number/URI of the destination of this call", and
`to_number`, present for phone calls. Your handler reads the dialed number,
looks up that line, checks the clock in the line's own time zone, and returns
the document for that number at that hour. Open, the caller hears a greeting
and is connected; closed, they hear the hours and the call ends.

Written against signalwire-sdk 3.0.1 (SWMLService) and Flask.
"""
import os
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from signalwire import SWMLService

# the SDK does not read .env for you
load_dotenv()

# dialed number -> the line it belongs to; swap for your database
LINES = {
    "+15550001111": {"name": "sales", "tz": "America/Denver",
                     "open": (time(9, 0), time(18, 0)), "connect": "+15550100001",
                     "greeting": "Ridgeline Cycles sales, one moment."},
    "+15550002222": {"name": "workshop", "tz": "America/Los_Angeles",
                     "open": (time(8, 0), time(16, 0)), "connect": "+15550100002",
                     "greeting": "Ridgeline Cycles workshop, one moment."},
}
CLOSED = ("Thanks for calling Ridgeline Cycles. The {name} line is open from "
          "{start} to {end}. Please call back then.")
UNKNOWN = "This number is not in service."
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", "25"))


def clock(t):
    """9 AM, 4 PM: the spoken form, without a platform-specific strftime flag."""
    return t.strftime("%I %p").lstrip("0")


def is_open(line, now):
    """The line's hours, judged in the line's own zone."""
    local = now.astimezone(ZoneInfo(line["tz"]))
    start, end = line["open"]
    return start <= local.time() <= end


def document(to, now):
    """The SWML for this number at this moment."""
    service = SWMLService(name="front", route="/swml")
    service.reset_document()
    service.add_verb("answer", {})
    line = LINES.get(to)
    if not line:
        service.add_verb("play", {"url": f"say:{UNKNOWN}"})
    elif is_open(line, now):
        service.add_verb("play", {"url": f"say:{line['greeting']}"})
        service.add_verb("connect", {"to": line["connect"], "timeout": CONNECT_TIMEOUT})
    else:
        start, end = line["open"]
        service.add_verb("play", {"url": "say:" + CLOSED.format(
            name=line["name"], start=clock(start), end=clock(end))})
    service.add_verb("hangup", {})
    return service.get_document()


def dialed(call):
    """`to_number` for phone calls, else `to`; both are documented fields."""
    return call.get("to_number") or call["to"]


app = Flask(__name__)


@app.post("/swml")
def swml():
    payload = request.get_json(force=True)
    return jsonify(document(dialed(payload["call"]), datetime.now(timezone.utc)))


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "8080")))
