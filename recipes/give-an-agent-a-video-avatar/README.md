# Give an agent a video avatar

> Three `ai.params`, `video_idle_file`, `video_listening_file` and `video_talking_file`, give an agent a face on a video call. The platform switches between the three clips with the agent's state.

**Scenario:** a bike shop's video front desk that shows a face rather than a blank tile

## What this demonstrates

The bundled schema documents three parameters under `ai.params`.
`video_idle_file` is the "URL of a video file to play when AI is idle".
`video_listening_file` is the one "to play when AI is listening to the user
speak". `video_talking_file` is the one "to play when AI is talking". Each
carries the note "Only works for calls that support video". You supply three
looping clips
and three URLs; the platform decides which one plays. Nothing about the prompt,
the tools or the voice changes.

## How it works

```python
AVATAR = {
    "video_idle_file": f"{BASE}/idle.mp4",
    "video_listening_file": f"{BASE}/listening.mp4",
    "video_talking_file": f"{BASE}/talking.mp4",
}

class FaceAgent(AgentBase):
    def __init__(self):
        super().__init__(name="face", route="/face")
        self.prompt_add_section("Role", "You are the front desk at Ridgeline Cycles, on a video call. ...")
        self.set_params(AVATAR)
```

What the platform receives, inside the `ai` verb:

```json
"params": {"video_idle_file": "https://media.example.com/avatar/idle.mp4",
           "video_listening_file": "https://media.example.com/avatar/listening.mp4",
           "video_talking_file": "https://media.example.com/avatar/talking.mp4"}
```

`set_params` merges into the agent's params, so the three sit beside whatever
else you set. The `swml/` surface is the same verb written by hand. The clips
are yours to make: a few seconds each, looping cleanly, hosted where the
platform can fetch them.

## Run it

```bash
cd python
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env: AVATAR_BASE_URL and the basic-auth pair
python app.py
```

The webhook needs a public HTTPS URL. For a local run, expose port 3000 with a
tunnel such as ngrok and use that hostname. A video call is what shows the
face, so point a Fabric address or a video-capable client at
`https://<user>:<password>@<your-host>/face/`. A phone call runs the same agent
with no video.

## Verify it

No network, no account.

```bash
cd ..                     # back to the recipe folder
python verify.py
```

The verifier renders the agent's document and validates both surfaces. It
asserts the following.

- `ai.params` holds exactly the three expected URLs, and no other `video_*` key
- the plain-SWML surface validates and carries the same three
- both prompts say the agent is on a video call
- the bundled schema documents each key as a string, names its state in the description, and notes it only works for calls that support video
- a document with a misspelt key, `video_idel_file`, still validates, which is why the first assertion compares the keys whole

## Limitations

You prove the document and the schema. Which clip plays when, and how the
switch looks, are the platform's side of a live video call.

The clips are files you host. The schema says nothing about format or length;
short, loopable, and served with a correct content type is the safe reading.

The schema does not reject an unknown key under `params`, so a typo in one of
the three names validates and shows nothing. Copy the names from the schema.

## What to change first

Point `AVATAR_BASE_URL` at your own three clips and run the verifier. It fails,
because its expected URLs are its own. That is the design: the verifier pins
the example, and your `.env` carries your files.
