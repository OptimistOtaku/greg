import {Suspense, useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Canvas,useFrame} from '@react-three/fiber';
import {Stars} from '@react-three/drei';
import * as THREE from 'three';
import {Room,Robot,Corridor,Knowledge} from '../Station';
import {Earth,Sun,StationHardware} from '../OrbitalEnvironment';
import type {Snapshot} from '../types';
import {replayAt,shotAt} from './replay';
import {drawGraphics} from './graphics';
import type {Caption} from './graphics';
import '@fontsource/barlow-condensed/600.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/ibm-plex-mono/400.css';
import './studio.css';

let playhead=6;
let recording=false;
let started=0;
let frameCount=0;
let finished=false;
let finishRecording:(()=>void)|null=null;
let outputCanvas:HTMLCanvasElement|null=null;
let currentState:Snapshot|null=null;
let previewPlaying=false;
let previewStart=0;
let take=0;
const DURATION=90;

function FilmWorld({source,image,captions,onReady}:{source:Snapshot;image:HTMLImageElement;captions:Caption[];onReady:()=>void}){
  const [state,setState]=useState(()=>replayAt(source,playhead));
  const [cutaway,setCutaway]=useState(false);
  const [graph,setGraph]=useState(false);
  const lastTick=useRef(-1),ready=useRef(false),lastShot=useRef('');
  const rooms=state.nodes.filter(n=>n.kind==='Room');
  const bodies=state.nodes.filter(n=>n.kind==='Body');
  const corridors=state.edges.filter(e=>e.type==='CONNECTS'&&e.source<e.target);
  useFrame(({gl,scene,camera})=>{
    const raw=recording?(performance.now()-started)/1000:previewPlaying?(performance.now()-previewStart)/1000:playhead;
    const t=Math.min(DURATION,raw);playhead=t;
    const shot=shotAt(t),p=Math.max(0,Math.min(1,(t-shot.start)/(shot.end-shot.start))),smooth=p*p*(3-2*p);
    const position=new THREE.Vector3(...shot.from).lerp(new THREE.Vector3(...shot.to),smooth);
    const target=new THREE.Vector3(...shot.look);
    if(!['graph','query'].includes(shot.kind)){
      position.applyAxisAngle(new THREE.Vector3(0,1,0),-.15);
      target.applyAxisAngle(new THREE.Vector3(0,1,0),-.15);
    }
    camera.position.copy(position);camera.lookAt(target);
    (camera as THREE.PerspectiveCamera).fov=shot.fov;(camera as THREE.PerspectiveCamera).updateProjectionMatrix();
    const unit=Math.floor(t*10);
    if(unit!==lastTick.current){lastTick.current=unit;const updated=replayAt(source,t);currentState=updated;setState(updated);}
    if(shot.kind!==lastShot.current){lastShot.current=shot.kind;setCutaway(!['alert','hero','memory','restored','ui','metrics','outro'].includes(shot.kind));setGraph(shot.kind==='graph'||shot.kind==='query');}
    gl.render(scene,camera);
    const ctx=outputCanvas?.getContext('2d',{alpha:false});
    if(ctx&&outputCanvas){ctx.drawImage(gl.domElement,0,0,1920,1080);drawGraphics(ctx,t,currentState||state,image,captions);}
    if(!ready.current&&gl.info.render.calls>10){ready.current=true;onReady();}
    if(recording){frameCount++;if(raw>=DURATION&&!finished){finished=true;finishRecording?.();}}
    if(previewPlaying&&raw>=DURATION)previewPlaying=false;
  },1);
  return <>
    <color attach="background" args={['#03070e']}/>
    <ambientLight intensity={.42}/><hemisphereLight args={['#d9e3eb','#1d4261',.75]}/>
    <directionalLight position={[-25,35,18]} intensity={3.6} color="#fff4da"/>
    <directionalLight position={[18,-10,-18]} intensity={1.3} color="#629dce"/>
    <Stars radius={200} depth={120} count={1800} factor={2.3} saturation={0} fade speed={.06}/>
    {!graph&&<><Earth/><Sun/></>}
    {!graph?<group rotation={[0,-.15,0]}>
      <StationHardware rooms={rooms} corridors={corridors}/>
      {corridors.map(e=><Corridor key={e.source+e.target} a={rooms.find(r=>r.id===e.source)!} b={rooms.find(r=>r.id===e.target)!} blocked={!!e.blocked} cutaway={cutaway}/>)}
      {rooms.map(r=><Room key={r.id} entity={r} selected={false} onClick={()=>{}} state={state} cutaway={cutaway}/>)}
      {bodies.map(b=><Robot key={`${take}-${b.id}`} body={b} rooms={rooms} selected={shotAt(playhead).kind===b.id||(b.id==='echo'&&playhead>=25&&playhead<30)} onSelect={()=>{}} cutaway={cutaway}/>)}
    </group>:<Knowledge state={state} selected="hypothesis-bus" onSelect={()=>{}}/>}
  </>;
}

function Studio(){
  const [source,setSource]=useState<Snapshot|null>(null);
  const [image,setImage]=useState<HTMLImageElement|null>(null);
  const [captions,setCaptions]=useState<Caption[]>([]);
  const [ready,setReady]=useState(false);
  const [status,setStatus]=useState('Loading local footage and fonts…');
  const [time,setTime]=useState(6);
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    Promise.all([fetch('/film-assets/outage.json').then(r=>r.json()),fetch('/film-assets/captions.json').then(r=>r.json()),document.fonts.ready]).then(([s,subs])=>{
      setSource(s);setCaptions(subs);const img=new Image();img.onload=()=>setImage(img);img.src='/film-assets/mission-control.png';
    }).catch(()=>setStatus('Missing film assets. Run scripts/prepare_video.py first.'));
    const update=window.setInterval(()=>{setTime(playhead);if(recording)setStatus(`Recording ${playhead.toFixed(1)} / 90 seconds · ${frameCount} rendered frames`);},200);
    return()=>clearInterval(update);
  },[]);
  const record=async()=>{
    if(!outputCanvas||!ready)return;
    previewPlaying=false;setBusy(true);setStatus('Arming the recorder…');playhead=0;finished=false;frameCount=0;take++;
    const mime=MediaRecorder.isTypeSupported('video/webm;codecs=vp9')?'video/webm;codecs=vp9':'video/webm;codecs=vp8';
    const recorder=new MediaRecorder(outputCanvas.captureStream(30),{mimeType:mime,videoBitsPerSecond:14000000});
    const chunks:BlobPart[]=[];
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recorder.onstop=async()=>{
      recording=false;setStatus('Saving rendered footage…');
      const blob=new Blob(chunks,{type:mime});
      const result=await fetch('/upload',{method:'POST',headers:{'Content-Type':'video/webm'},body:blob});
      const saved=await result.json();setBusy(false);setStatus(result.ok?`Saved ${saved.bytes} bytes · ${frameCount} frames · source recording complete`:'Recording save failed');
    };
    finishRecording=()=>recorder.stop();
    // The slate resets before the timed capture begins.
    window.setTimeout(()=>{started=performance.now();recording=true;recorder.start(1000);},250);
  };
  return <main className="studio">
    <header><div><small>GREG / FILM STUDIO</small><h1>Orbital field test.</h1></div><span>1920 × 1080 · 30 FPS · 90 SECONDS</span></header>
    <canvas id="film-output" width={1920} height={1080} ref={node=>{outputCanvas=node;}}/>
    <section className="studio-controls">
      <button disabled={!ready||busy} onClick={()=>void record()}>Record cinematic demo</button>
      <button disabled={!ready||busy} onClick={()=>{previewPlaying=!previewPlaying;if(previewPlaying)previewStart=performance.now()-playhead*1000;}}>Play / pause preview</button>
      <label>Preview time <input aria-label="Preview time" type="range" min="0" max="89.8" step=".1" value={time} disabled={busy} onChange={e=>{previewPlaying=false;playhead=Number(e.target.value);setTime(playhead);}}/><b>{time.toFixed(1)}s</b></label>
      <output role="status">{status}</output>
    </section>
    <p>Recorded Gemini action receipts · directed 3D replay · synthetic narration and original score are mixed during MP4 export.</p>
    {source&&image&&<div className="film-stage"><Canvas dpr={1} camera={{position:[26,21,33],fov:40,near:.1,far:600}} gl={{antialias:true,alpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'}}><Suspense fallback={null}><FilmWorld source={source} image={image} captions={captions} onReady={()=>{setReady(true);setStatus('Ready to record. No model calls are made by this renderer.');}}/></Suspense></Canvas></div>}
  </main>;
}

createRoot(document.getElementById('root')!).render(<Studio/>);
