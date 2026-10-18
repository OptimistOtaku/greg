import type {Snapshot} from '../types';

const mint='#a5ebcd',gold='#e6b77d',blue='#93bbd8',paper='#eeeade',red='#ed775e';
type Point={x:number;y:number;title:string;sub:string;color:string};
const layout:Record<string,Point>={
  'agent-engineer':{x:205,y:405,title:'ENGINEER MIND',sub:'AGENT / SHARED CONTEXT',color:gold},
  'agent-scout':{x:205,y:735,title:'SCOUT MIND',sub:'AGENT / SHARED CONTEXT',color:mint},
  'bolt':{x:205,y:245,title:'BOLT / OFFLINE',sub:'BODY / EVIDENCE RETAINED',color:red},
  'echo':{x:515,y:245,title:'ECHO / ONLINE',sub:'REPLACEMENT BODY',color:gold},
  'obs-antenna':{x:625,y:405,title:'COMMS READING',sub:'OBSERVATION / POWER_LOSS',color:blue},
  'obs-coolant':{x:625,y:735,title:'COOLING READING',sub:'OBSERVATION / POWER_LOSS',color:blue},
  'antenna':{x:1060,y:350,title:'COMMS ARRAY',sub:'SYSTEM',color:blue},
  'coolant':{x:1060,y:770,title:'COOLING LOOP',sub:'SYSTEM',color:blue},
  'bus':{x:1535,y:550,title:'POWER BUS',sub:'SYSTEM / SHARED CAUSE',color:gold},
  'hypothesis-bus':{x:965,y:560,title:'UPSTREAM FAILURE',sub:'HYPOTHESIS / 2 SOURCES',color:mint},
};
function text(c:CanvasRenderingContext2D,s:string,x:number,y:number,size=18,color=paper,mono=false){c.font=`${mono?400:500} ${size}px "${mono?'IBM Plex Mono':'DM Sans'}"`;c.fillStyle=color;c.fillText(s,x,y);}
function pos(id:string,t:number){const p=layout[id];return {...p,x:p.x+Math.sin(t*.22+p.y)*5,y:p.y+Math.cos(t*.17+p.x)*4};}
function link(c:CanvasRenderingContext2D,a:Point,b:Point,label:string,t:number,index:number){
  const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy),ux=dx/len,uy=dy/len;
  const trim=(p:Point,sign:number)=>{const d=Math.min(Math.abs(ux)>0.001?132/Math.abs(ux):1e5,Math.abs(uy)>0.001?43/Math.abs(uy):1e5);return {x:p.x+ux*d*sign,y:p.y+uy*d*sign};};
  const start=trim(a,1),end=trim(b,-1),p=(t*.45+index*.19)%1;
  c.strokeStyle=label==='SUPPORTED_BY'?mint:'#526b78';c.lineWidth=label==='SUPPORTED_BY'?2:1.4;c.beginPath();c.moveTo(start.x,start.y);c.lineTo(end.x,end.y);c.stroke();
  c.fillStyle=c.strokeStyle;c.beginPath();c.moveTo(end.x,end.y);c.lineTo(end.x-ux*10-uy*5,end.y-uy*10+ux*5);c.lineTo(end.x-ux*10+uy*5,end.y-uy*10-ux*5);c.fill();
  c.shadowColor=mint;c.shadowBlur=14;c.fillStyle=mint;c.beginPath();c.arc(start.x+(end.x-start.x)*p,start.y+(end.y-start.y)*p,3.8,0,Math.PI*2);c.fill();c.shadowBlur=0;
  const mx=(start.x+end.x)/2,my=(start.y+end.y)/2;c.font='400 13px "IBM Plex Mono"';const width=c.measureText(label).width;c.fillStyle='#071019';c.fillRect(mx-width/2-7,my-11,width+14,21);text(c,label,mx-width/2,my+4,13,label==='SUPPORTED_BY'?mint:'#b9c9cf',true);
}

/** Topology is filtered from the recorded snapshot. Moving dots illustrate graph access,
 * not additional database relationships or live model activity. */
export function drawKnowledge(c:CanvasRenderingContext2D,t:number,state:Snapshot){
  c.fillStyle='#050b12';c.fillRect(0,72,1920,936);
  const glow=c.createRadialGradient(970,560,40,970,560,930);glow.addColorStop(0,'#112c32');glow.addColorStop(1,'#050b12');c.fillStyle=glow;c.fillRect(0,72,1920,936);
  c.strokeStyle='#183039';c.lineWidth=.5;
  for(let x=20;x<1920;x+=60){c.beginPath();c.moveTo(x,180);c.lineTo(x,910);c.stroke();}
  for(let y=190;y<920;y+=60){c.beginPath();c.moveTo(0,y);c.lineTo(1920,y);c.stroke();}
  text(c,'FALKORDB / THE CREW’S SHARED KNOWLEDGE GRAPH',70,130,20,mint,true);
  const diagnosed=state.nodes.some(n=>n.id==='hypothesis-bus');
  text(c,diagnosed?'TWO OBSERVATIONS. ONE CONNECTED CAUSE.':'THE BODY FAILS. THE EVIDENCE STAYS.',70,181,41,paper);
  const visible=new Set(state.nodes.filter(n=>layout[n.id]&&(n.id!=='echo'||Number(state.metrics.handoffs)>0)).map(n=>n.id));
  const edges=state.edges.filter(e=>visible.has(e.source)&&visible.has(e.target)&&['ABOUT','OBSERVED_BY','DEPENDS_ON','SUPPORTED_BY','EMBODIES'].includes(e.type));
  edges.forEach((e,i)=>link(c,pos(e.source,t),pos(e.target,t),e.type,t,i));
  for(const id of visible){const p=pos(id,t);c.fillStyle='#09151f';c.strokeStyle=p.color;c.lineWidth=1.5;c.shadowBlur=id==='hypothesis-bus'?24:8;c.shadowColor=p.color;c.fillRect(p.x-132,p.y-43,264,86);c.strokeRect(p.x-132,p.y-43,264,86);c.shadowBlur=0;
    c.fillStyle=p.color;c.fillRect(p.x-132,p.y-43,4,86);text(c,p.sub,p.x-115,p.y-15,11,p.color,true);text(c,p.title,p.x-115,p.y+15,22,paper);
    if(id==='bus'&&diagnosed){text(c,'← 2 INDEPENDENT SUBSYSTEMS',p.x-130,p.y+72,13,gold,true);}
  }
  if(!diagnosed){text(c,'AWAITING CORRELATION',1390,690,17,gold,true);text(c,'Both readings persist outside the robot bodies.',1170,728,19,paper);}
  // Separate access lane: these are illustrative read animations, not schema edges.
  const lane=884; c.strokeStyle='#355d60';c.setLineDash([3,7]);c.beginPath();c.moveTo(210,lane);c.lineTo(1710,lane);c.stroke();c.setLineDash([]);
  for(let i=0;i<3;i++){const x=210+i*750;c.fillStyle='#08131b';c.fillRect(x-125,lane-21,250,43);text(c,['SCOUT / READ','ENGINEER / READ','CARRIER / READ'][i],x-106,lane+5,16,i===1?gold:mint,true);const q=(t*.4+i/3)%1;c.fillStyle=mint;c.beginPath();c.arc(240+q*1410,lane,4,0,Math.PI*2);c.fill();}
  text(c,'SHARED CONTEXT ACCESS · DOTTED LANE ILLUSTRATES READS; SOLID ARROWS ARE RECORDED RELATIONSHIPS',75,942,13,'#9bb1b9',true);
  text(c,`RECEIPT TICK ${state.run.tick}   /   ${state.metrics.observations} OBSERVATIONS   /   ${edges.length} SHOWN RELATIONSHIPS`,75,973,13,mint,true);
  if(t>=36){
    c.fillStyle='rgba(4,12,19,.96)';c.fillRect(1190,738,660,102);c.strokeStyle=gold;c.strokeRect(1190,738,660,102);
    text(c,'SHARED-CAUSE QUERY / PATH SUMMARY',1210,765,13,gold,true);
    text(c,'Observation → ABOUT → System → DEPENDS_ON*1..3 → root',1210,793,14,paper,true);
    text(c,'size(collect(DISTINCT system)) ≥ 2  →  bus',1210,822,15,mint,true);
  }
}

export function drawMemoryInset(c:CanvasRenderingContext2D,t:number,state:Snapshot){
  const x=1100,y=610;c.fillStyle='rgba(4,12,19,.94)';c.fillRect(x,y,715,305);c.strokeStyle=mint;c.strokeRect(x,y,715,305);
  text(c,'FALKORDB / SAME MIND, RETAINED EVIDENCE',x+25,y+37,16,mint,true);
  const transferred=state.metrics.handoffs>0;
  text(c,'COMMS READING',x+25,y+105,21,blue);text(c,'─[OBSERVED_BY]→ ENGINEER',x+230,y+105,17,paper,true);
  text(c,'ENGINEER',x+25,y+172,24,gold);text(c,'─[EMBODIES]→ '+(transferred?'ECHO':'BOLT'),x+230,y+172,21,gold,true);
  text(c,transferred?'BOLT OFFLINE / EVIDENCE EDGE UNCHANGED':'EVIDENCE WRITTEN TO SHARED GRAPH',x+25,y+232,16,mint,true);
  text(c,'READABLE BY SCOUT · ENGINEER · CARRIER',x+25,y+272,15,paper,true);
}
