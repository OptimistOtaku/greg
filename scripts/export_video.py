"""Encode and verify the cinematic recording, with final audio and QA frames."""
from pathlib import Path
import json
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'artifacts'/'video'
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
source=DEST/'greg-demo-source.webm'
assert source.exists() and source.stat().st_size>100_000,'Record the film in the local studio first'
output=DEST/'greg-demo-1080p.mp4'
command=[ffmpeg,'-y','-hide_banner','-loglevel','warning','-i',str(source),'-i',str(DEST/'soundtrack.wav'),
         '-map','0:v:0','-map','1:a:0','-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','medium','-crf','19',
         '-c:a','aac','-b:a','192k','-ar','48000','-af','loudnorm=I=-16:TP=-1.5:LRA=9',
         '-movflags','+faststart','-t','90','-shortest',str(output)]
subprocess.run(command,check=True)
print('MP4 encoded; checking complete audio/video decode…',flush=True)
subprocess.run([ffmpeg,'-v','error','-i',str(output),'-f','null','-'],check=True)
reader=imageio_ffmpeg.read_frames(str(output));meta=next(reader);reader.close()
assert meta['size']==(1920,1080) and abs(meta['fps']-30)<.01 and 89<meta['duration']<91,meta
frame_dir=DEST/'qa-frames';frame_dir.mkdir(exist_ok=True)
times=[1,6,13,18,20,23,27,31,33,38,45,54,64,79,87]
sheet=Image.new('RGB',(4*480,4*300),'#070d13');draw=ImageDraw.Draw(sheet)
for i,seconds in enumerate(times):
    path=frame_dir/f'{seconds:02}.jpg'
    subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-ss',str(seconds),'-i',str(output),'-frames:v','1','-q:v','2',str(path)],check=True)
    with Image.open(path) as image:
        image.thumbnail((480,270));x=(i%4)*480;y=(i//4)*300;sheet.paste(image,(x,y));draw.text((x+12,y+277),f'{seconds:02}s',fill='#a5ebcd')
sheet.save(DEST/'contact-sheet.jpg',quality=93)
subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-ss','6','-i',str(output),'-frames:v','1','-q:v','1',str(DEST/'cover.jpg')],check=True)
report={'file':output.name,'bytes':output.stat().st_size,'duration_seconds':meta['duration'],'fps':meta['fps'],'resolution':list(meta['size']),
        'video_codec':meta.get('codec'),'audio':'AAC stereo, 48 kHz, normalized target -16 LUFS',
        'decode_check':'passed, complete video and audio','captions':'burned in; companion greg-demo.srt',
        'source':'Recorded Gemini outage mission action receipts; directed cinematic reconstruction',
        'narration':'Synthetic Charon voice generated with Gemini TTS','music':'Original procedural 120 BPM score',
        'credits':'Station geometry: project code. Earth imagery: NASA Blue Marble, credits in web/public/textures/CREDITS.md.'}
(DEST/'export-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
