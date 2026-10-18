"""Probe local Gemini configuration with credential-redacted diagnostics."""
import json
import os
import argparse
from pathlib import Path

from dotenv import load_dotenv
from google import genai

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--generate", action="store_true")
parser.add_argument("--model")
args = parser.parse_args()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=key)
try:
    if args.generate:
        model = args.model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        response = client.models.generate_content(model=model, contents="Reply with OK.")
        print(json.dumps({"authenticated": True, "model": model, "generation": "ok"}))
    else:
        models = [m.name for m in client.models.list() if "generateContent" in (m.supported_actions or [])]
        print(json.dumps({"authenticated": True, "models": models}))
except Exception as exc:
    # Strip the configured credential before reporting provider quota diagnostics.
    message = str(exc).replace(key, "[REDACTED]") if key else str(exc)
    print(json.dumps({"request_succeeded": False, "error_type": type(exc).__name__, "status": getattr(exc, "code", None), "diagnostic": message[:4000]}))
    raise SystemExit(1)
finally:
    client.close()
