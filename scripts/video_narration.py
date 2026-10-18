"""Generate original synthetic narration using the locally configured Gemini key."""
import io
import json
import os
from pathlib import Path
import wave

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "artifacts" / "video"
DEST.mkdir(exist_ok=True)
TRANSCRIPT = """Three robots. Two failed systems. One shared understanding.
This is Greg: an AI crew coordinated through a FalkorDB knowledge graph.
On Orpheus, cooling and communications are degraded. The crew investigates, until Bolt goes offline.
The engineer transfers to Echo. A different body. A different location. Shared evidence survives.
Two independent observations connect to one upstream power bus.
The graph determines which tasks are ready, which routes are open, and which body can act.
Moss delivers the replacement relay. Echo repairs the bus.
The crew verifies both systems before declaring recovery.
These are recorded actions from a real Gemini run, replayed faster for this film.
Three authored live-model scenarios completed, including a sealed corridor and a mid-mission body failure.
Sixty deterministic recovery runs also passed.
Greg. Shared knowledge. Distributed action."""
(DEST / "narration.txt").write_text(TRANSCRIPT + "\n", encoding="utf-8")
load_dotenv(ROOT / ".env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options=types.HttpOptions(timeout=120000))
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents="Read the following original script as a composed, confident cinematic mission-control narrator. Clear diction, restrained intensity, natural short pauses. About 125 words per minute. Do not read these directions. Pronounce Greg like the name, FalkorDB as Falkor D B. Script:\n" + TRANSCRIPT,
        config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")))),
    )
    parts = response.candidates[0].content.parts
    data = b"".join(p.inline_data.data for p in parts if p.inline_data)
    assert data
    path = DEST / "narration.wav"
    if data[:4] == b"RIFF":
        path.write_bytes(data)
    else:
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(data)
    with wave.open(str(path), "rb") as wav:
        seconds = wav.getnframes() / wav.getframerate()
    metadata = {"synthetic_voice": True, "voice": "Charon", "model": "gemini-2.5-flash-preview-tts", "seconds": round(seconds, 3)}
    (DEST / "narration-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))
except Exception as exc:
    print(json.dumps({"narration_generated": False, "type": type(exc).__name__, "provider_status": getattr(exc, "code", None)}))
    raise SystemExit(1)
finally:
    client.close()
