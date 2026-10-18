# Data and asset provenance

| Material | Origin / use |
| --- | --- |
| Rooms, systems, dependencies, tasks, capabilities, bodies and faults | Original synthetic scenario authored in this repository; graph data |
| Observations, hypotheses, claims and action receipts | Produced by local simulator/Gemini missions through validated tools; graph data |
| Benchmark fixtures and results | Synthetic local missions; reported measurement outputs, no private source dataset |
| Real-model replay artifacts | Synthetic mission state plus recorded bounded tool actions; no API keys included |
| Station and robot meshes | Original procedural project code; frontend only |
| Earth / clouds / night textures | NASA public imagery; source links and credits in `web/public/textures/CREDITS.md`; frontend only |
| Fonts and software libraries | Bundled package dependencies with their upstream licenses; no claim of authorship |
| Demo narration | Gemini TTS synthetic prebuilt Charon voice; transcript and metadata generated locally by `scripts/video_narration.py` |
| Demo music and sound design | Original procedural synthesis in `scripts/prepare_video.py` |
| YouTube thumbnail | AI-generated promotional illustration using the project's robot screenshot as reference; not a product screenshot |

The operational graph contains no private, personal, paywalled, login-protected,
or otherwise restricted source information. Local credentials belong in ignored
`.env` files and are not part of the submission.

The thumbnail uses image generation with a frame from the project's recorded
3D replay as reference. It depicts the product concept artistically.
