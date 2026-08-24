"""Send an SMS, and handle the outcome properly."""
import os

from flask import Flask, request
from signalwire.rest import Client

app = Flask(__name__)
client = Client(
    os.environ["SIGNALWIRE_PROJECT_ID"],
    os.environ["SIGNALWIRE_API_TOKEN"],
    signalwire_space_url=os.environ["SIGNALWIRE_SPACE"],
)

TERMINAL = {"delivered", "undelivered", "failed"}
seen = set()


def send(to, body):
    msg = client.messages.create(
        from_=os.environ["SIGNALWIRE_PHONE_NUMBER"],
        to=to,
        body=body,
        status_callback=os.environ["PUBLIC_URL"] + "/sms-status",
    )
    # "queued" or "accepted" here. Not delivered.
    app.logger.info("accepted sid=%s status=%s", msg.sid, msg.status)
    return msg.sid


@app.post("/sms-status")
def sms_status():
    sid = request.form.get("MessageSid")
    status = request.form.get("MessageStatus")
    # Status callbacks can repeat. Make the handler idempotent.
    key = (sid, status)
    if key in seen:
        return "", 204
    seen.add(key)
    if status in TERMINAL:
        app.logger.info(
            "terminal sid=%s status=%s err=%s",
            sid,
            status,
            request.form.get("ErrorCode"),
        )
    return "", 204


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "8080")))
