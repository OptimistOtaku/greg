import type {Snapshot} from '../types';
import {shotAt, SHOTS} from './replay';
import {drawKnowledge,drawMemoryInset} from './knowledge';

export type Caption={start:number;end:number;text:string};
const C={ink:'#050a10',paper:'#eeeade',mint:'#a5ebcd',red:'#ed775e',blue:'#93bbd8',muted:'#91a4ae',gold:'#e6b77d'};
export const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const ease=(x:number)=>1-Math.pow(1-clamp(x),3);

function type(c:CanvasRenderingContext2D,text:string,x:number,y:number,size=28,color=C.paper,weight=500,mono=false){
  c.fillStyle=color;c.font=`${weight} ${size}px "${mono?'IBM Plex Mono':size>70?'Barlow Condensed':'DM Sans'}"`;c.fillText(text,x,y);
}
function label(c:CanvasRenderingContext2D,text:string,x:number,y:number,color=C.muted,size=17){
  c.font=`400 ${size}px "IBM Plex Mono"`;c.fillStyle=color;let px=x;
  for(const ch of text){c.fillText(ch,px,y);px+=c.measureText(ch).width+2.1;}
}
function line(c:CanvasRenderingContext2D,x1:number,y1:number,x2:number,y2:number,color=C.mint,width=1){
  c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.moveTo(x1,y1);c.lineTo(x2,y2);c.stroke();
}
function panel(c:CanvasRenderingContext2D,x:number,y:number,w:number,h:number,color=C.mint){
  c.fillStyle='rgba(4,12,18,.9)';c.fillRect(x,y,w,h);c.strokeStyle=color;c.lineWidth=1;c.strokeRect(x,y,w,h);
  for(const [a,b] of [[x,y],[x+w-12,y],[x,y+h],[x+w-12,y+h]])line(c,a,b,a+12,b,color,3);
}
function title(c:CanvasRenderingContext2D,lines:string[],t:number,x=96,y=440,size=130,color=C.paper){
  lines.forEach((s,i)=>{const p=ease((t-i*.08)/.55);c.save();c.globalAlpha=p;c.beginPath();c.rect(x,y-size+i*size*.94,1600,size*1.1);c.clip();type(c,s,x,y+(1-p)*70+i*size*.94,size,color,600);c.restore();});
}
function progress(c:CanvasRenderingContext2D,text:string,x:number,y:number,p:number,color=C.mint){
  label(c,text,x,y,color,15);line(c,x,y+20,x+340,y+20,'#29414a',3);line(c,x,y+20,x+340*clamp(p),y+20,color,3);
}
function centered(c:CanvasRenderingContext2D,text:string,y:number,size:number,color=C.paper,weight=600){
  c.font=`${weight} ${size}px "${size>70?'Barlow Condensed':'DM Sans'}"`;c.fillStyle=color;c.fillText(text,(1920-c.measureText(text).width)/2,y);
}
function wrapped(c:CanvasRenderingContext2D,text:string,width:number){
  const lines:string[]=[];let row='';
  for(const word of text.split(' ')){const next=row?row+' '+word:word;if(c.measureText(next).width>width&&row){lines.push(row);row=word;}else row=next;}
  if(row)lines.push(row);return lines;
}

export function drawGraphics(c:CanvasRenderingContext2D,t:number,state:Snapshot,image:HTMLImageElement|null,captions:Caption[]){
  const shot=shotAt(t),age=t-shot.start;
  // Directed exposure: clear space on the left for editorial titles.
  const shade=c.createLinearGradient(0,0,1920,0);shade.addColorStop(0,'rgba(2,7,12,.94)');shade.addColorStop(.45,'rgba(2,7,12,.28)');shade.addColorStop(1,'rgba(2,7,12,.04)');
  c.fillStyle=shade;c.fillRect(0,72,1920,936);
  if(['graph','query','ui','metrics','outro'].includes(shot.kind)){c.fillStyle=`rgba(3,8,13,${shot.kind==='outro'?.89:shot.kind==='ui'?.8:shot.kind==='metrics'?.88:.86})`;c.fillRect(0,72,1920,936);}
  if(shot.kind==='alert'){
    c.fillStyle='rgba(3,7,12,.7)';c.fillRect(0,72,1920,936);
    label(c,'ORPHEUS / INCIDENT 007',96,184,C.red);
    title(c,['TWO SYSTEMS','OFFLINE.'],age,96,470,190,C.paper);
    const p=ease(age/1.2);line(c,1040,290,1040,790,C.red,2);progress(c,'COOLING    / DEGRADED',1120,440,p,C.red);progress(c,'COMMS      / DEGRADED',1120,590,p,C.red);
    label(c,'NO SINGLE ROBOT CAN FINISH ALONE',96,845,C.red,20);
  }else if(shot.kind==='hero'){
    label(c,'COLLECTIVE INTELLIGENCE / ORBITAL FIELD TEST',96,190,C.mint);
    title(c,['GREG'],age,90,540,290);
    type(c,'AI CREW.',102,654,70,C.mint,600);type(c,'SHARED MEMORY.',102,730,70,C.paper,600);
    label(c,'POWERED BY FALKORDB',104,858,C.mint,18);
  }else if(['pip','bolt','moss'].includes(shot.kind)){
    const names:Record<string,string[]>={pip:['PIP','SCOUT / SURVEY + DIAGNOSIS','SCAN','ANALYZE'],bolt:['BOLT','ENGINEER / SYSTEMS + REPAIR','SCAN','REPAIR'],moss:['MOSS','CARRIER / SUPPLY + TRANSPORT','SCAN','CARRY']};
    const n=names[shot.kind];const color=shot.kind==='pip'?C.mint:shot.kind==='bolt'?C.gold:C.blue;
    label(c,'01 / MEET THE CREW',96,178,color);title(c,[n[0]],age,96,520,230,color);label(c,n[1],105,612,C.paper,19);
    n.slice(2).forEach((s,i)=>{panel(c,105+i*220,680,195,56,color);label(c,s,130+i*220,716,color,17);});
    label(c,'MIND ≠ BODY',105,850,C.muted,22);
  }else if(shot.kind==='scan'){
    const isComms=t<17;label(c,'02 / INVESTIGATE',96,178,C.blue);
    title(c,[isComms?'LOCAL CHECK.':'EVIDENCE','SHARED.'],age,96,410,125);
    progress(c,isComms?'BOLT / COMMS ARRAY':'PIP / COOLING LOOP',105,740,ease(age/(shot.end-shot.start)),C.blue);
    label(c,'SIGNAL: POWER_LOSS',105,828,C.gold,20);
    if(t>=18)drawMemoryInset(c,t,state);
  }else if(shot.kind==='failure'){
    c.fillStyle='rgba(90,20,12,.2)';c.fillRect(0,72,1920,936);
    label(c,'CONTINGENCY / MID-MISSION BODY FAILURE',96,178,C.red);
    title(c,['BOLT','OFFLINE.'],age,96,440,180,C.red);
    label(c,'BODY LOST. EVIDENCE RETAINED.',104,835,C.paper,22);
    line(c,1100,340,1510,340,C.red,2);for(let i=0;i<9;i++)line(c,1100+i*45,330+(i%2)*20,1120+i*45,350-(i%2)*20,C.red,2);
  }else if(shot.kind==='memory'){
    drawKnowledge(c,t,state);
  }else if(shot.kind==='handoff'){
    label(c,'EMBODIMENT TRANSFER / VALIDATED BY CAPABILITY',96,178,C.gold);
    title(c,['SAME AGENT.','NEW BODY.'],age,96,410,150);
    panel(c,104,725,620,137,C.gold);label(c,'ENGINEER  —[EMBODIES]→  ECHO',133,778,C.gold,18);label(c,'LOCATION: AIRLOCK / NO TELEPORTATION',133,825,C.paper,14);
    drawMemoryInset(c,t,state);
  }else if(shot.kind==='graph'||shot.kind==='query'){
    drawKnowledge(c,t,state);
  }else if(['pickup','transport','delivered'].includes(shot.kind)){
    label(c,'04 / COORDINATE THE REPAIR',96,178,C.blue);
    const titleLines=shot.kind==='pickup'?['CLAIM.','COLLECT.']:shot.kind==='transport'?['FOLLOW THE','OPEN ROUTE.']:['PART DELIVERED.','REPAIR UNLOCKED.'];
    title(c,titleLines,age,96,415,shot.kind==='delivered'?110:130);
    const p=clamp((t-40)/10);progress(c,'MOSS / RELAY DELIVERY',104,800,p,C.blue);
    label(c,'STORES  →  HUB  →  POWER CORE',104,874,C.paper,19);
  }else if(shot.kind==='repair'){
    label(c,'05 / ACT THROUGH THE NEW BODY',96,178,C.gold);
    title(c,['ECHO','RESTORES POWER.'],age,96,420,140);
    progress(c,'REPAIR PREREQUISITES / SATISFIED',104,795,ease(age/4),C.gold);label(c,'DIAGNOSIS + DELIVERED RELAY + CAPABILITY',104,870,C.muted,15);
  }else if(shot.kind==='restored'){
    label(c,'POWER BUS / OPERATIONAL',96,178,C.mint);title(c,['REPAIR IS NOT','VERIFICATION.'],age,96,410,140);
    label(c,'THE CREW STILL HAS TO CHECK BOTH SYSTEMS.',104,840,C.mint,19);
  }else if(shot.kind==='verifycool'||shot.kind==='verifycomm'){
    label(c,'06 / VERIFY AT THE SUBSYSTEM',96,178,C.mint);
    title(c,[shot.kind==='verifycool'?'COOLING.':'COMMS.','VERIFIED.'],age,96,430,160,C.mint);
    label(c,shot.kind==='verifycool'?'PIP / PHYSICAL CHECK':'ECHO / PHYSICAL CHECK',104,820,C.paper,21);
    const percent=Math.round(clamp((age+.3)/2.5)*100);type(c,String(percent).padStart(3,'0')+'%',1250,835,110,C.mint,600);
  }else if(shot.kind==='ui'){
    label(c,'ACTUAL MISSION CONTROL / SAVED GEMINI RUN',96,156,C.mint);
    title(c,['7/7'],age,96,490,270,C.mint);type(c,'OBJECTIVES VERIFIED',104,586,48,C.paper,600);
    ['COOLING      VERIFIED','COMMS        VERIFIED','SAMPLES      STABLE'].forEach((s,i)=>{const p=ease((age-i*.25)/.7);c.save();c.globalAlpha=p;label(c,s,106,686+i*58,C.mint,18);c.restore();});
    if(image){const p=ease(age/.8);c.save();c.globalAlpha=p;const x=1050+(1-p)*80,y=195;panel(c,x-12,y-12,768,692,'#3e5d65');c.drawImage(image,x,y,744,668);c.restore();}
    label(c,'3D REPLAY RECONSTRUCTED FROM RECORDED ACTION RECEIPTS',104,910,C.muted,13);
  }else if(shot.kind==='metrics'){
    label(c,'MEASURED. REPRODUCIBLE. LOCAL.',96,168,C.mint);title(c,['THE RECEIPTS.'],age,96,325,130);
    const metrics=[['3/3','LIVE GEMINI DEMOS','THREE AUTHORED SCENARIOS'],['60/60','SIMULATION RUNS','6 CASES × 10 REPEATS'],['1.19','ms / MEDIAN DIAGNOSIS','200 LOCAL QUERY SAMPLES']];
    metrics.forEach((m,i)=>{const p=ease((age-i*.15)/.9);c.save();c.globalAlpha=p;const x=104+i*585;line(c,x,430,x+520,430,'#446354',1);type(c,m[0],x,650,190,i===2?C.gold:C.mint,600);label(c,m[1],x,723,C.paper,17);label(c,m[2],x,779,C.muted,13);c.restore();});
    label(c,'AUTHORED DEMOS ≠ GENERAL RELIABILITY / FULL RESULTS IN THE REPOSITORY',104,906,C.muted,14);
  }else if(shot.kind==='outro'){
    centered(c,'GREG',535,330,C.paper);centered(c,'SHARED KNOWLEDGE. DISTRIBUTED ACTION.',665,43,C.mint,500);
    centered(c,'github.com/OptimistOtaku/greg',789,27,C.paper,400);
    centered(c,'FALKORDB / TRACK 01 / AGENTS THAT ACT ON CONNECTED DATA',867,18,C.muted,400);
    centered(c,'SYNTHETIC STATION  ·  RECORDED GEMINI ACTIONS  ·  ORIGINAL SCORE  ·  SYNTHETIC VOICE',928,14,C.muted,400);
  }

  // Film gate, restrained metadata, and open captions.
  c.fillStyle=C.ink;c.fillRect(0,0,1920,72);c.fillRect(0,1008,1920,72);
  label(c,'GREG / ORBITAL FIELD TEST 001',54,44,C.paper,15);
  label(c,'RECORDED GEMINI RUN / TIME COMPRESSED',650,44,C.muted,13);
  const sec=Math.floor(t),frame=Math.floor((t-sec)*30);label(c,`00:${String(sec).padStart(2,'0')}:${String(frame).padStart(2,'0')}`,1695,44,C.mint,15);
  line(c,54,994,1866,994,'#263d42',1);line(c,54,994,54+1812*clamp(t/90),994,C.mint,2);
  const caption=captions.find(s=>t>=s.start&&t<s.end);
  if(caption){c.font='500 25px "DM Sans"';const rows=wrapped(c,caption.text,1740);rows.slice(0,2).forEach((s,i)=>{c.fillStyle=C.paper;c.fillText(s,(1920-c.measureText(s).width)/2,1036+i*29);});}
  else label(c,shot.kind==='outro'?'BUILT FOR GRAPH HACKS 2026':'WORLD: SYNTHETIC  /  MEMORY: FALKORDB  /  ACTUATION: VALIDATED TOOLS',54,1050,C.muted,13);
  // A short optical cut accent, never a continuous strobe.
  const cut=SHOTS.some(s=>[3,19,25,56,84].includes(s.start)&&t>=s.start&&t<s.start+.075);
  if(cut){c.fillStyle=`rgba(238,234,222,${.7*(1-(age/.075))})`;c.fillRect(0,0,1920,1080);}
  if(t>88.5){c.fillStyle=`rgba(3,7,12,${clamp((t-88.5)/1.5)})`;c.fillRect(0,0,1920,1080);}
  if(t<.35){c.fillStyle=`rgba(3,7,12,${1-t/.35})`;c.fillRect(0,0,1920,1080);}
}
