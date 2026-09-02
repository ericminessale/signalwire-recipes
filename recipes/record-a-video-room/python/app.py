"""Record a video room.

`record_on_start` on a room is the switch. The vendored REST spec describes it
as "Specifies whether to start recording a Room Session when one is started
for this Room." Every session of the room is then recorded, and the
recordings are REST objects: `GET /api/video/room_sessions/{id}/recordings`
lists a session's, each with a `status`, a `duration`, a `format` and a `uri`
to fetch, `GET /api/video/room_recordings/{id}` reads one, and
`DELETE /api/video/room_recordings/{id}` removes it.

Written against signalwire-sdk 3.0.1 (RestClient.video).
"""
import os

from dotenv import load_dotenv
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()

ROOM = os.getenv("ROOM_NAME", "workshop-standup")


def create_room(name=ROOM):
    """A room whose every session is recorded."""
    return client.video.rooms.create(name=name, display_name="Workshop stand-up",
                                     record_on_start=True)


def recordings_of(session_id):
    """What a session produced. Each entry carries the uri to download."""
    return client.video.room_sessions.list_recordings(session_id)


def recording(recording_id):
    return client.video.room_recordings.get(recording_id)


def delete_recording(recording_id):
    """Your retention policy, applied by id."""
    return client.video.room_recordings.delete(recording_id)


if __name__ == "__main__":
    import sys

    usage = ("usage: python app.py room | recordings <session_id> | "
             "get <recording_id> | delete <recording_id>")
    if len(sys.argv) < 2:
        raise SystemExit(usage)
    verb, args = sys.argv[1], sys.argv[2:]
    if verb == "room":
        print(create_room())
    elif verb == "recordings" and args:
        print(recordings_of(args[0]))
    elif verb == "get" and args:
        print(recording(args[0]))
    elif verb == "delete" and args:
        print(delete_recording(args[0]))
    else:
        raise SystemExit(usage)
