# GREG demo film

Final deliverable: `artifacts/video/greg-demo-1080p.mp4` — 90 seconds, 1920×1080,
30 fps, H.264 video, AAC stereo audio, fast-start metadata and burned-in captions.
Companion captions: `artifacts/video/greg-demo.srt`.

The film uses 22 directed shots, hard cuts, kinetic typography, an animated
receipt-driven FalkorDB knowledge graph, a real mission-control screenshot, original electronic score,
synthetic narration and procedural transition sounds.

## Evidence and disclosures

The 3D sequence is reconstructed from the actual ordered action receipts in
`artifacts/gemini-mid-mission-body-outage-replay.json`, mission
`mission-6cfc9b866988`. It is time-compressed and camera-directed, rather than a
claim that the LLM completed the mission live in 90 seconds. The renderer does
not make model calls or modify the operational graph.

The film states that the station is synthetic, the run is recorded, and the
three live scenarios are authored demonstrations. The 60/60 result refers to
six deterministic scenarios repeated ten times. The 1.19 ms figure is the local
median of 200 shared-cause query samples, not an LLM response-time claim.
Full context and interrupted attempts remain in the README and raw reports.

Narration is a synthetic prebuilt Charon voice from Gemini TTS, not a recording
or imitation of a particular person. Its original transcript and generation
metadata are saved beside the film. All score, percussion and transition sounds
are synthesized by `scripts/prepare_video.py`; no commercial music is used.
Earth imagery is NASA Blue Marble, credited in
`web/public/textures/CREDITS.md`. Geometry and graphics are project code.

## Rebuild the film

After the normal project setup, install the optional local media dependencies:

```powershell
uv pip install --python .venv/Scripts/python.exe imageio-ffmpeg numpy pillow
# Only needed to regenerate the voice; calls the configured provider:
uv run --no-sync python scripts/video_narration.py
.venv/Scripts/python.exe scripts/prepare_video.py
npm run build --prefix web
.venv/Scripts/python.exe scripts/film_server.py
```

Open `http://127.0.0.1:8015/film.html`. The slider previews individual shots.
Click **Record cinematic demo** and leave the page rendering for 90 seconds.
It saves `greg-demo-source.webm` to the fixed local video-artifact directory.
The receiver is bound only to localhost and caps source recordings at 250 MB.

Then:

```powershell
.venv/Scripts/python.exe scripts/export_video.py
```

The exporter mixes the original score and narration, normalizes audio to a
target of -16 LUFS, encodes MP4, checks the complete video/audio decode, and
creates a contact sheet, cover, QA frames and technical report. Media files and
prepared web assets are ignored by Git to avoid adding large intermediates.

`http://127.0.0.1:8015/film-watch.html` provides the finished player and download
links while the local film server is running. The MP4 can also be played directly
from the artifacts folder. No external publication/upload is performed by the
video scripts.

## Shared graph sequence

The graph shots show nodes and relationships filtered from each reconstructed
receipt tick: `Observation-[:OBSERVED_BY]->Agent`,
`Observation-[:ABOUT]->System`, `System-[:DEPENDS_ON]->System`,
`Hypothesis-[:SUPPORTED_BY]->Observation`, and `Agent-[:EMBODIES]->Body`.
The hypothesis appears only after the recorded diagnosis. The engineer changes
bodies while the observation remains connected to its mind. Dotted read pulses
illustrate shared context access; they are explicitly separate from stored edges.
The query inset summarizes the shared-cause traversal, not a second live execution.
