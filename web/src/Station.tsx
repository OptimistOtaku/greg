import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html, Line, OrbitControls, RoundedBox, Stars } from '@react-three/drei';
import { Aperture, Box, Expand, Minimize2, RotateCcw, RotateCw, ScanLine } from 'lucide-react';
import * as THREE from 'three';
import { Earth, ModuleHull, PressureTunnel, StationHardware, Sun } from './OrbitalEnvironment';
import type { Entity, Snapshot } from './types';

type Props = {state:Snapshot;selected:string|null;onSelect:(id:string)=>void;view:'station'|'graph'};
const ROOM_COLORS:Record<string,string> = {hub:'#9edcca',power:'#e5aa68',comms:'#82b5e7',cooling:'#92d5ca',lab:'#b5a5da',stores:'#babdd1',airlock:'#bdc8d1'};

function Room({entity,selected,onClick,state,cutaway}:{entity:Entity;selected:boolean;onClick:()=>void;state:Snapshot;cutaway:boolean}) {
  const [hover,setHover] = useState(false);
  const systems = state.nodes.filter(n=>n.kind==='System' && n.room===entity.id);
  const bad = systems.some(n=>n.status==='degraded'||n.status==='diagnosed'||n.status==='at_risk');
  const color = bad?'#e5aa68':ROOM_COLORS[entity.id];
  return <group position={[entity.x!,0,entity.z!]}>
    <group onClick={e=>{e.stopPropagation();onClick();}} onPointerOver={e=>{e.stopPropagation();setHover(true);document.body.style.cursor='pointer';}} onPointerOut={()=>{setHover(false);document.body.style.cursor='auto';}}>
      <ModuleHull cutaway={cutaway} color={color} selected={selected||hover}/>
      <RoundedBox args={[4.25,.38,3.65]} radius={.16} position={[0,-.18,0]}><meshStandardMaterial color={selected||hover?'#364750':'#1a2834'} metalness={.55} roughness={.6}/></RoundedBox>
      <RoundedBox args={[3.95,.08,3.35]} radius={.1} position={[0,.06,0]}><meshStandardMaterial color="#31414b" metalness={.4} roughness={.85}/></RoundedBox>
      <mesh rotation={[-Math.PI/2,0,0]} position={[0,.11,0]}><planeGeometry args={[3.65,3.05]}/><meshStandardMaterial color="#25333c"/></mesh>
      {[-1,1].map(x=>[-1,1].map(z=><group key={`${x}${z}`} position={[x*1.98,.45,z*1.65]}>
        <mesh><boxGeometry args={[.12,.8,.12]}/><meshStandardMaterial color="#71818a" metalness={.75} roughness={.4}/></mesh>
        <mesh position={[0,.44,0]}><boxGeometry args={[.13,.06,.13]}/><meshBasicMaterial color={color}/></mesh>
      </group>))}
      {[-1,1].map(z=><mesh key={z} position={[0,.15,z*1.7]}><boxGeometry args={[3.8,.035,.035]}/><meshBasicMaterial color={selected?'#d5ffec':color}/></mesh>)}
      <mesh position={[-1.25,.43,-.8]}><boxGeometry args={[.8,.65,.5]}/><meshStandardMaterial color="#53616b" metalness={.5} roughness={.6}/></mesh>
      <mesh position={[-1.25,.65,-.54]}><planeGeometry args={[.5,.25]}/><meshBasicMaterial color={color}/></mesh>
      <mesh position={[1.25,.29,-.85]}><boxGeometry args={[.65,.35,.7]}/><meshStandardMaterial color="#43535e"/></mesh>
      {entity.id==='power' && <group position={[.1,.55,-.5]}><mesh><cylinderGeometry args={[.43,.43,.9,12]}/><meshStandardMaterial color="#394750" metalness={.8} roughness={.3}/></mesh>{[-.3,0,.3].map(y=><mesh key={y} position={[0,y,0]}><torusGeometry args={[.44,.035,6,24]}/><meshBasicMaterial color={bad?'#ffb760':'#a7e6d2'}/></mesh>)}</group>}
      {entity.id==='comms' && <group position={[.5,.5,-.4]} rotation={[.4,0,-.3]}><mesh><cylinderGeometry args={[.06,.06,1,8]}/><meshStandardMaterial color="#89929b"/></mesh><mesh position={[0,.6,0]} rotation={[Math.PI/2,0,0]}><sphereGeometry args={[.75,20,12,0,Math.PI*2,0,Math.PI/2]}/><meshStandardMaterial color="#b0bcc3" side={THREE.DoubleSide} metalness={.7} roughness={.5}/></mesh></group>}
      {entity.id==='cooling' && <group position={[.35,.45,-.5]}>{[-.5,.2,.9].map(x=><mesh key={x} position={[x,0,0]}><cylinderGeometry args={[.22,.22,.65,12]}/><meshStandardMaterial color="#507e87" metalness={.7}/></mesh>)}</group>}
      {entity.id==='lab' && <group position={[.2,.45,-.45]}>{[-.5,0,.5].map(x=><mesh key={x} position={[x,0,0]}><boxGeometry args={[.25,.6,.3]}/><meshStandardMaterial color="#9fb9b0" emissive="#6caa92" emissiveIntensity={.25} transparent opacity={.8}/></mesh>)}</group>}
      {entity.id==='stores' && <group position={[.45,.3,-.5]}>{[-.45,.3,.9].map((x,i)=><mesh key={x} position={[x,i%2*.15,0]}><boxGeometry args={[.55,.4,.6]}/><meshStandardMaterial color={i===1?'#ab8f62':'#65717b'}/></mesh>)}</group>}
    </group>
    <Html position={[0,cutaway?.45:2.7,2.5]} center distanceFactor={28} zIndexRange={[5,0]} style={{pointerEvents:'none'}}>
      <div className={`room-label ${selected?'chosen':''}`}><span className={bad?'dot amber':'dot'}/>{entity.name}<small>{String(entity.sector)}</small></div>
    </Html>
  </group>;
}

function Robot({body,rooms,selected,onSelect,cutaway}:{body:Entity;rooms:Entity[];selected:boolean;onSelect:()=>void;cutaway:boolean}) {
  const ref = useRef<THREE.Group>(null);
  const head = useRef<THREE.Group>(null);
  const room = rooms.find(r=>r.id===body.room);
  const offset = {pip:[-.6,.55],bolt:[.7,.35],moss:[0,1.1],echo:[.6,.7]}[body.id]||[0,0];
  const destination = useMemo(()=>new THREE.Vector3((room?.x||0)+offset[0],.3,(room?.z||0)+offset[1]),[room?.x,room?.z,offset[0],offset[1]]);
  const initial = useRef(destination.clone());
  const online = body.status==='online';
  const color = online?body.color!:'#6d7781';
  useFrame(({clock},dt)=>{
    if(!ref.current)return;
    const delta = destination.clone().sub(ref.current.position);
    if(delta.length()>.06){ref.current.rotation.y=Math.atan2(delta.x,delta.z);ref.current.position.lerp(destination,1-Math.exp(-dt*3.8));}
    if(head.current)head.current.position.y=.48+(online?Math.sin(clock.elapsedTime*2+body.id.length)*.018:0);
  });
  return <group ref={ref} position={initial.current}>
    <group scale={1.25} onClick={e=>{e.stopPropagation();onSelect();}}>
      <RoundedBox args={[.57,.36,.6]} radius={.08} position={[0,.16,0]}><meshStandardMaterial color={color} metalness={.5} roughness={.45}/></RoundedBox>
      {[-1,1].map(x=><group key={x} position={[x*.33,.03,0]}>{[-.18,.18].map(z=><mesh key={z} position={[0,0,z]} rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.12,.12,.11,12]}/><meshStandardMaterial color="#0d1820" roughness={.7}/></mesh>)}</group>)}
      <group ref={head} position={[0,.48,0]}>
        <RoundedBox args={[.63,.38,.48]} radius={.07}><meshStandardMaterial color={color} metalness={.35} roughness={.4}/></RoundedBox>
        <RoundedBox args={[.49,.24,.035]} radius={.04} position={[0,0,.25]}><meshStandardMaterial color="#07151c"/></RoundedBox>
        {[-.12,.12].map(x=><mesh key={x} position={[x,.02,.274]}><boxGeometry args={[.065,.09,.012]}/><meshBasicMaterial color={online?'#d9fff0':'#b76e60'}/></mesh>)}
        <mesh position={[.15,.28,0]}><cylinderGeometry args={[.015,.015,.2,6]}/><meshStandardMaterial color="#8d9da6"/></mesh>
        <mesh position={[.15,.4,0]}><sphereGeometry args={[.045,8,8]}/><meshBasicMaterial color={online?'#aaf1cf':'#d58c72'}/></mesh>
      </group>
      {!!body.carrying?.length&&<mesh position={[0,.4,-.4]}><boxGeometry args={[.4,.36,.3]}/><meshStandardMaterial color="#d8b076"/></mesh>}
      {(selected||online)&&<mesh rotation={[-Math.PI/2,0,0]} position={[0,-.15,0]}><ringGeometry args={[selected?.55:.43,selected?.59:.45,32]}/><meshBasicMaterial color={color} transparent opacity={selected?.9:.35} side={THREE.DoubleSide}/></mesh>}
    </group>
    {!cutaway&&<Line points={[[0,2.3,0],[0,3.1,0]]} color={color} transparent opacity={.6} dashed dashSize={.08} gapSize={.08}/>}
    <Html position={[0,cutaway?1.4:3.3,0]} center distanceFactor={28} zIndexRange={[8,0]}><button className={`robot-tag ${selected?'active':''}`} onClick={onSelect} style={{'--robot':color} as React.CSSProperties}>{body.name}<span>{body.status==='standby'?'RESERVE':body.status==='offline'?'OFFLINE':String(body.agent?.replace('agent-','')||body.role).toUpperCase()}</span></button></Html>
  </group>;
}

function Corridor({a,b,blocked,cutaway}:{a:Entity;b:Entity;blocked:boolean;cutaway:boolean}) {
  const start = new THREE.Vector3(a.x!,0,a.z!);const end=new THREE.Vector3(b.x!,0,b.z!);
  const mid=start.clone().add(end).multiplyScalar(.5);const length=start.distanceTo(end);
  const angle=Math.atan2(end.x-start.x,end.z-start.z);
  return <group position={mid} rotation={[0,angle,0]}>
    <PressureTunnel length={length} blocked={blocked} cutaway={cutaway}/>
    <mesh position={[0,-.18,0]}><boxGeometry args={[.85,.18,length]}/><meshStandardMaterial color={blocked?'#5c3434':'#2a3c48'} metalness={.65} roughness={.5}/></mesh>
    {[-.33,.33].map(x=><mesh key={x} position={[x,-.07,0]}><boxGeometry args={[.025,.025,length]}/><meshBasicMaterial color={blocked?'#dc866e':'#50717c'}/></mesh>)}
    {blocked&&<mesh position={[0,.25,0]}><boxGeometry args={[1.1,.8,.15]}/><meshStandardMaterial color="#a05d4c" emissive="#673527" emissiveIntensity={.5}/></mesh>}
  </group>;
}

function Knowledge({state,selected,onSelect}:{state:Snapshot;selected:string|null;onSelect:(id:string)=>void}) {
  const [hovered,setHovered]=useState<string|null>(null);
  const nodes=state.nodes.filter(n=>['Agent','Body','System','Task','Observation','Hypothesis','Item'].includes(n.kind));
  const layers:Record<string,number>={Agent:6,Body:3,System:0,Task:-4,Observation:6,Hypothesis:3,Item:-4};
  const colors:Record<string,string>={Agent:'#a8eccd',Body:'#e8bd81',System:'#80a9d3',Task:'#a7a1d7',Observation:'#e1d2ad',Hypothesis:'#f0b17d',Item:'#c2d4c6'};
  const positions:Record<string,THREE.Vector3>={};
  const groups:Record<string,Entity[]>={};nodes.forEach(n=>(groups[n.kind]??=[]).push(n));
  Object.entries(groups).forEach(([kind,list],g)=>list.forEach((n,i)=>{const angle=(i/list.length)*Math.PI*2+g*.6;const radius=kind==='System'?4:kind==='Task'?8:kind==='Observation'?5:7;positions[n.id]=new THREE.Vector3(Math.cos(angle)*radius,layers[kind],Math.sin(angle)*radius);}));
  const linked = new Set(state.edges.filter(e=>e.source===selected||e.target===selected).flatMap(e=>[e.source,e.target]));
  return <group position={[0,-1,0]}>
    {state.edges.filter(e=>positions[e.source]&&positions[e.target]).map((e,i)=><Line key={`${e.source}${e.type}${e.target}${i}`} points={[positions[e.source],positions[e.target]]} color={linked.has(e.source)&&linked.has(e.target)?'#c6f4db':'#3e6475'} transparent opacity={selected?(linked.has(e.source)&&linked.has(e.target)?.85:.13):.4} lineWidth={e.type==='SUPPORTED_BY'?1.6:.8}/>) }
    {nodes.map(n=><group key={n.id} position={positions[n.id]}>
      <mesh onClick={e=>{e.stopPropagation();onSelect(n.id);}} onPointerOver={e=>{e.stopPropagation();setHovered(n.id);document.body.style.cursor='pointer';}} onPointerOut={()=>{setHovered(null);document.body.style.cursor='auto';}}><sphereGeometry args={[n.kind==='Hypothesis'?.45:.3,16,16]}/><meshStandardMaterial color={colors[n.kind]} emissive={colors[n.kind]} emissiveIntensity={n.id===selected?1.4:.75} transparent opacity={selected&&!linked.has(n.id)&&n.id!==selected?.3:1}/></mesh>
      {(n.id===selected||n.id===hovered||(selected?linked.has(n.id):n.kind==='Agent'||n.kind==='Hypothesis'))&&<Html position={[0,.65,0]} center distanceFactor={29} zIndexRange={[5,0]}><button className={`graph-node-label ${n.id===selected?'active':''}`} onClick={()=>onSelect(n.id)}><small>{n.kind}</small>{n.name}</button></Html>}
    </group>)}
  </group>;
}

function CameraReset({reset,view}:{reset:number;view:'station'|'graph'}){
  const {camera,controls}=useThree();
  useEffect(()=>{
    if(view==='station')camera.position.set(26,21,33);
    else camera.position.set(22,24,29);
    camera.lookAt(0,0,0);
    const orbit=controls as unknown as {target:THREE.Vector3;update:()=>void}|undefined;
    orbit?.target.set(0,0,0);orbit?.update();
  },[reset,view,camera,controls]);
  return null;
}

function World({state,selected,onSelect,view,cutaway,rotate,reset}:Props&{cutaway:boolean;rotate:boolean;reset:number}){
  const rooms=state.nodes.filter(n=>n.kind==='Room');
  const bodies=state.nodes.filter(n=>n.kind==='Body');
  const corridorEdges=state.edges.filter(e=>e.type==='CONNECTS'&&e.source<e.target);
  const observation=state.nodes.find(n=>n.kind==='Hypothesis');
  return <>
    <color attach="background" args={['#03070e']}/>
    <ambientLight intensity={.42}/><hemisphereLight args={['#d9e3eb','#1d4261',.75]}/>
    <directionalLight position={[-25,35,18]} intensity={3.6} color="#fff4da"/>
    <directionalLight position={[18,-10,-18]} intensity={1.3} color="#629dce"/>
    <Stars radius={200} depth={120} count={2100} factor={2.3} saturation={0} fade speed={.06}/>
    {view==='station'&&<><Earth/><Sun/></>}
    {view==='station'?<group rotation={[0,-.15,0]}>
      <StationHardware rooms={rooms} corridors={corridorEdges}/>
      {corridorEdges.map(e=>{const a=rooms.find(r=>r.id===e.source)!;const b=rooms.find(r=>r.id===e.target)!;return <Corridor key={e.source+e.target} a={a} b={b} blocked={!!e.blocked} cutaway={cutaway}/>;})}
      {rooms.map(r=><Room key={r.id} entity={r} selected={selected===r.id} onClick={()=>onSelect(r.id)} state={state} cutaway={cutaway}/>)}
      {bodies.map(b=><Robot key={`${state.run.id}-${b.id}`} body={b} rooms={rooms} selected={selected===b.id} onSelect={()=>onSelect(b.id)} cutaway={cutaway}/>)}
      {observation&&['cooling','comms'].map(id=>{const p=rooms.find(r=>r.id==='power')!;const t=rooms.find(r=>r.id===id)!;return <Line key={id} points={[[p.x!,1.5,p.z!],[0,4,id==='cooling'?2:-3],[t.x!,1.5,t.z!]]} color="#e9b479" transparent opacity={.55} dashed dashSize={.18} gapSize={.15}/>;})}
    </group>:<Knowledge state={state} selected={selected} onSelect={onSelect}/>}
    <OrbitControls makeDefault minDistance={12} maxDistance={65} maxPolarAngle={Math.PI*.47} target={[0,0,0]} enableDamping dampingFactor={.08} autoRotate={rotate} autoRotateSpeed={.25}/>
    <CameraReset reset={reset} view={view}/>
  </>;
}

export default function Station(props:Props){
  const [cutaway,setCutaway]=useState(false);
  const [expanded,setExpanded]=useState(false);
  const [rotate,setRotate]=useState(false);
  const [reset,setReset]=useState(0);
  const selectedEntity=props.state.nodes.find(n=>n.id===props.selected);
  useEffect(()=>{const close=(event:KeyboardEvent)=>{if(event.key==='Escape')setExpanded(false);};window.addEventListener('keydown',close);return()=>window.removeEventListener('keydown',close);},[]);
  return <div className={`orbital-scene ${expanded?'expanded':''}`}>
    <Canvas camera={{position:[26,21,33],fov:36,near:.1,far:600}} dpr={[1,1.6]} gl={{antialias:true,alpha:false}}><Suspense fallback={null}><World {...props} cutaway={cutaway} rotate={rotate} reset={reset}/></Suspense></Canvas>
    {expanded&&<div className="orbital-expanded-title"><span>GREG / ORBITAL OBSERVATORY</span><h2>ORPHEUS STATION</h2><p>Earth backdrop · synthetic robot mission</p></div>}
    <div className="orbital-view-controls">
      {props.view==='station'&&<><button className={!cutaway?'active':''} onClick={()=>setCutaway(false)}><Box size={12}/>Exterior</button><button className={cutaway?'active':''} onClick={()=>setCutaway(true)}><ScanLine size={12}/>Cutaway</button></>}
      <button className={rotate?'active icon-only':'icon-only'} onClick={()=>setRotate(!rotate)} aria-label={rotate?'Stop camera orbit':'Orbit camera'} title="Orbit camera"><RotateCw size={13}/></button>
      <button className="icon-only" onClick={()=>setReset(reset+1)} aria-label="Reset camera" title="Reset camera"><RotateCcw size={13}/></button>
      <button className="icon-only" onClick={()=>setExpanded(!expanded)} aria-label={expanded?'Exit immersive view':'Expand 3D scene'} title={expanded?'Exit immersive view':'Expand 3D scene'}>{expanded?<Minimize2 size={13}/>:<Expand size={13}/>}</button>
    </div>
    {props.view==='station'&&<div className="orbital-location"><Aperture size={12}/><span>EARTH ORBIT <i/> ARTISTIC SCALE</span></div>}
    {expanded&&<div className="orbital-expanded-footer"><span><i/>LIVE GRAPH STATE · {props.state.nodes.filter(n=>n.kind==='Body'&&n.status==='online').length} ROBOTS ONLINE</span><p>Drag to orbit · scroll to zoom · select a module or robot · Esc to exit</p></div>}
    {expanded&&selectedEntity&&<div className="orbital-selection"><small>{selectedEntity.kind}</small><strong>{selectedEntity.name}</strong><span>{selectedEntity.status||selectedEntity.role||selectedEntity.sector as string}</span></div>}
  </div>;
}
