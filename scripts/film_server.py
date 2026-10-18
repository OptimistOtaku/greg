"""Local-only video studio server; accepts the single generated source recording."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'artifacts'/'video'
DEST.mkdir(exist_ok=True)
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT/'web'/'dist'),**kwargs)
    def translate_path(self,path):
        media={'/greg-demo.mp4':'greg-demo-1080p.mp4','/cover.jpg':'cover.jpg','/greg-demo.srt':'greg-demo.srt'}
        name=media.get(urlparse(path).path)
        return str(DEST/name) if name else super().translate_path(path)
    def do_POST(self):
        if self.path!='/upload':
            self.send_error(404);return
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<250_000_000:
            self.send_error(413);return
        path=DEST/'greg-demo-source.webm'
        with path.open('wb') as out:
            remaining=length
            while remaining:
                chunk=self.rfile.read(min(1_048_576,remaining))
                if not chunk:raise ConnectionError('Incomplete recording')
                out.write(chunk);remaining-=len(chunk)
        data=json.dumps({'saved':True,'bytes':length}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        print(f'Recording saved: {length} bytes',flush=True)
    def log_message(self,*args):
        pass
print('Film studio: http://127.0.0.1:8015/film.html',flush=True)
ThreadingHTTPServer(('127.0.0.1',8015),Handler).serve_forever()
