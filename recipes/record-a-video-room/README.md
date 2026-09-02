# Record a video room

> `record_on_start: true` on a room makes the platform record each of its sessions. A session's recordings list over REST, each with a `uri`, a `status` and a `duration`, and a DELETE by recording id removes one.

**Scenario:** a workshop stand-up on video that the people who missed it watch later

## What this demonstrates

Recording is a property of the room, not a button in the call. The vendored
REST spec's `POST /api/video/rooms` takes `record_on_start`, a boolean it
describes as "Specifies whether to start recording a Room Session when one is
started for this Room." From then on the recordings are REST objects.
`GET /api/video/room_sessions/{id}/recordings` lists a session's, and each
carries `status`, `duration`, `format`, `size_in_bytes` and a `uri` to fetch.
`GET /api/video/room_recordings/{id}` reads one, and
`DELETE /api/video/room_recordings/{id}` answers `204` and removes it. You
reach them as `client.video.rooms.create`,
`client.video.room_sessions.list_recordings`, and `client.video.room_recordings`
`get` and `delete`.

## How it works

```python
def create_room(name=ROOM):
    return client.video.rooms.create(name=name, display_name="Workshop stand-up",
                                     record_on_start=True)

def recordings_of(session_id):
    return client.video.room_sessions.list_recordings(session_id)

def delete_recording(recording_id):
    return client.video.room_recordings.delete(recording_id)
```

What the platform receives:

```json
POST /api/video/rooms
{"name": "workshop-standup", "display_name": "Workshop stand-up", "record_on_start": true}

GET /api/video/room_sessions/<session_id>/recordings
GET /api/video/room_recordings/<recording_id>
DELETE /api/video/room_recordings/<recording_id>
```

The session id comes from the room's `active_session` in the room object, or
from `GET /api/video/room_sessions`. The list and the get take `media_ttl`, how
long the returned `uri` stays valid; the recipe leaves it at the platform's
default.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: your project id, API token and space
python app.py room               # once; then hold a session in the room
python app.py recordings <session_id>
python app.py get <recording_id>
python app.py delete <recording_id>
```

There is no server to expose; the script speaks to the REST API and exits. Join
the room from a browser, leave, and the session's recording appears once the
platform finishes it.

## Verify it

No network, no account.

```bash
python verify.py          # from the recipe folder, not python/
```

You swap the SDK's HTTP layer for a recorder that answers with a room and one
recording. You call the four helpers and assert the following.

- they make four requests in order: `POST` the room, `GET` the session's recordings, `GET` one recording, `DELETE` it
- the room body is exactly `name`, `display_name` and `record_on_start: true`, and the other three carry no body or query
- every path and body is documented; the spec requires `name` on the room and describes `record_on_start` with the quoted sentence
- the spec's recording schema, on both the list and the get, carries `id`, `room_session_id`, `status`, `duration`, `format` and `uri`, and the fixture uses only documented fields
- the delete answers `204` with no body, and the list documents `media_ttl`

## Limitations

You prove the requests and the documented shapes. When a recording reaches
`completed`, and what the `uri` serves, are the platform's side of a live
session.

Starting a recording from inside the call is not here. The Browser SDK v4
reference labels `startRecording` unimplemented, so the room property is the
documented switch.

## What to change first

Drop `record_on_start=True` from `create_room` and run the verifier. The
exact-body assertion fails, and nothing else would: the spec's own default is
not to record, so a room without the switch produces sessions and no
recordings.
