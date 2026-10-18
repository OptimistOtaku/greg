"""Transcribe the synthetic voice once to catch missing or unintended narration."""
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'artifacts'/'video'
load_dotenv(ROOT/'.env')
client=genai.Client(api_key=os.getenv('GEMINI_API_KEY'),http_options=types.HttpOptions(timeout=60000))
try:
    response=client.models.generate_content(model='gemini-3.1-flash-lite',contents=[
        types.Part.from_text(text='Transcribe this synthetic narration verbatim. Return only the spoken words, no analysis or headings.'),
        types.Part.from_bytes(data=(DEST/'narration.wav').read_bytes(),mime_type='audio/wav')],
        config=types.GenerateContentConfig(temperature=0,max_output_tokens=2000))
    transcript=response.text or ''
    expected=(DEST/'narration.txt').read_text()
    normalize=lambda s:re.sub(r'[^a-z0-9]+','',s.lower())
    ratio=SequenceMatcher(None,normalize(expected),normalize(transcript),autojunk=False).ratio()
    report={'model':'gemini-3.1-flash-lite','normalized_transcript_similarity':round(ratio,4),
            'expected_words':len(expected.split()),'transcribed_words':len(transcript.split()),'transcript':transcript,
            'scope':'Automated ASR sanity check, not a substitute for listening'}
    (DEST/'narration-transcript-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='transcript'}))
except Exception as exc:
    print(json.dumps({'audio_check':'unavailable','type':type(exc).__name__,'provider_status':getattr(exc,'code',None)}))
finally:
    client.close()
