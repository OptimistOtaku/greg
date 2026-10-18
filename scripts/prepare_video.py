"""Prepare local recorded evidence, aligned captions and an original synth score."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import textwrap
import wave

import imageio_ffmpeg
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'artifacts'/'video'
ASSETS=ROOT/'web'/'public'/'film-assets'
DEST.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'artifacts'/'gemini-mid-mission-body-outage-replay.json',ASSETS/'outage.json')
shutil.copyfile(ROOT/'artifacts'/'gemini-live-demo.png',ASSETS/'mission-control.png')
shutil.copyfile(ROOT/'web/node_modules/@fontsource/dm-sans/files/dm-sans-latin-500-normal.woff2',ASSETS/'sans.woff2')
shutil.copyfile(ROOT/'web/node_modules/@fontsource/barlow-condensed/files/barlow-condensed-latin-600-normal.woff2',ASSETS/'display.woff2')

with wave.open(str(DEST/'narration.wav'),'rb') as wav:
    rate=wav.getframerate();audio=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16).astype(np.float32)/32768
    if wav.getnchannels()>1:audio=audio.reshape(-1,wav.getnchannels()).mean(axis=1)
    voice_duration=len(audio)/rate
target_voice_duration=80
tempo=voice_duration/target_voice_duration
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(DEST/'narration.wav'),'-af',f'atempo={tempo}', '-ar','48000','-ac','1',str(DEST/'narration-timed.wav')],check=True)

sentences=[line.strip() for line in (DEST/'narration.txt').read_text().splitlines() if line.strip()]
weights=np.array([len(s.split())+1.8 for s in sentences]);ideals=np.cumsum(weights)/weights.sum()*voice_duration
# Snap estimated paragraph ends to nearby actual quiet passages.
hop=int(rate*.02)
rms=np.array([np.sqrt(np.mean(audio[i:i+hop]**2)) for i in range(0,len(audio)-hop,hop)])
quiet=np.where(rms<.015)[0]*.02
ends=[];previous=0.
for i,ideal in enumerate(ideals):
    if i==len(ideals)-1:end=voice_duration
    else:
        candidates=quiet[(quiet>max(previous+.7,ideal-1.2))&(quiet<ideal+1.2)]
        end=float(candidates[np.argmin(abs(candidates-ideal))]) if len(candidates) else float(ideal)
    ends.append(end);previous=end
captions=[];start=4.
for sentence,end in zip(sentences,ends):
    stop=4+end/tempo
    captions.append({'start':round(start,3),'end':round(stop,3),'text':sentence})
    start=stop
(ASSETS/'captions.json').write_text(json.dumps(captions,indent=2)+'\n')
def stamp(t):
    millis=round(t*1000);hours,millis=divmod(millis,3600000);minutes,millis=divmod(millis,60000);seconds,millis=divmod(millis,1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'
(DEST/'greg-demo.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n"+'\n'.join(textwrap.wrap(c['text'],68)) for i,c in enumerate(captions))+'\n',encoding='utf-8')

# Original 120 BPM score. All oscillators, percussion and FX are synthesized here.
sr=48000;duration=90;n=sr*duration;rng=np.random.default_rng(20261018)
music=np.zeros(n,dtype=np.float32)
def add(at,signal,gain=1.):
    begin=int(at*sr);end=min(n,begin+len(signal))
    if begin<n:music[begin:end]+=signal[:end-begin]*gain
def tone(freq,seconds,amp=.1):
    t=np.arange(int(seconds*sr))/sr
    envelope=(1-np.exp(-t*30))*np.exp(-t*1.9)
    return amp*(np.sin(2*np.pi*freq*t)+.22*np.sin(2*np.pi*freq*2*t))*envelope
for beat in np.arange(0,89.5,.5):
    if 19<=beat<22 or 84<=beat<86:continue
    # Kick with pitch drop and an airy upper transient.
    t=np.arange(int(sr*.36))/sr
    kick=np.sin(2*np.pi*(43*t+32*(1-np.exp(-t*28))/28))*np.exp(-t*15)
    section=.62 if beat<8 else .8 if beat<40 else 1.
    add(beat,kick,.24*section)
    if int(beat*2)%2:
        t=np.arange(int(sr*.14))/sr;noise=rng.normal(0,1,len(t)).astype(np.float32)
        snap=(noise-np.convolve(noise,np.ones(7)/7,'same'))*np.exp(-t*35)
        add(beat,snap,.065)
    if beat>=8:
        for off in [0,.25]:
            t=np.arange(int(sr*.055))/sr;noise=rng.normal(0,1,len(t))
            hat=(noise-np.convolve(noise,np.ones(9)/9,'same'))*np.exp(-t*90)
            add(beat+off,hat,.025)
    note=[73.416,73.416,87.307,65.406][int(beat//4)%4]
    add(beat,tone(note,.46,.16*section))
    if beat>=30:
        arp=[146.83,220,261.63,349.23,293.66,261.63,220,174.61][int(beat*2)%8]
        add(beat+.25,tone(arp,.7,.055))
# Slow harmonic bed, with original pitched oscillators only.
t=np.arange(n)/sr
for freq in [146.83,174.61,220,261.63]:
    music+=.013*np.sin(2*np.pi*freq*t+.3*np.sin(2*np.pi*.07*t))*(.65+.35*np.sin(2*np.pi*.025*t))
for at in [3,8,14,19,22,25,30,36,40,43,47,51,56,59,62,66,76,84]:
    tt=np.arange(int(sr*.65))/sr
    whoosh=rng.normal(0,1,len(tt)).astype(np.float32)*np.sin(np.pi*np.minimum(1,tt/.65))**3
    whoosh=np.convolve(whoosh,np.ones(15)/15,'same')
    add(max(0,at-.4),whoosh,.11)
    add(at,tone(36.708,1.5,.15))
for at in [19,19.6,20.2]:
    tt=np.arange(int(sr*.14))/sr;add(at,np.sin(2*np.pi*830*tt)*np.sin(np.pi*tt/.14)**2,.06)
for at in [63,65,66]:
    add(at,tone(880,.65,.07));add(at+.11,tone(1318.5,.6,.04))
music*=np.minimum(1,t/2)*np.minimum(1,(90-t)/3)
music=np.tanh(music)*.34
with wave.open(str(DEST/'narration-timed.wav'),'rb') as wav:
    voice=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16).astype(np.float32)/32768
voice=voice/(np.max(np.abs(voice))+.001)*.78
mix=music.copy();voice_start=4*sr
# Keep the score under the narrator without flattening the impact sound design.
mix[voice_start:voice_start+len(voice)]*=.5
mix[voice_start:voice_start+len(voice)]+=voice
mix=np.clip(mix,-.96,.96)
stereo=np.stack([mix,mix],axis=1)
with wave.open(str(DEST/'soundtrack.wav'),'wb') as wav:
    wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(sr);wav.writeframes((stereo*32767).astype('<i2').tobytes())
(DEST/'production.json').write_text(json.dumps({'duration':90,'resolution':[1920,1080],'fps':30,'narration_start':4,'narration_seconds':target_voice_duration,'narration_source_seconds':voice_duration,'music':'Original procedurally synthesized 120 BPM score','source_run':'mission-6cfc9b866988','disclosure':'Directed reconstruction from recorded Gemini action receipts, with time compression. Synthetic voice.'},indent=2)+'\n')
print(json.dumps({'prepared':True,'captions':len(captions),'voice_seconds':voice_duration,'soundtrack_seconds':90,'ffmpeg':ffmpeg}))
