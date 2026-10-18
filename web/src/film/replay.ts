import type {Entity, Snapshot} from '../types';

// Selected receipt ticks from the actual completed body-outage mission.
export const CUES:[number,number][]=[[0,1],[14,4],[15,6],[17,8],[18,10],[19.1,12],[22,13],[25.2,15],[28,17],[29.3,20],[32,22],[40,24],[41,26],[43.5,29],[46,31],[49,33],[51,35],[52,38],[53.5,40],[56,45],[59,49],[60,51],[61,53],[62,55],[63,57],[64,60],[65,62],[66,63]];

export function replayAt(source:Snapshot,seconds:number):Snapshot{
  const tick=CUES.filter(([t])=>t<=seconds).at(-1)?.[1]||1;
  const nodes=source.nodes.filter(n=>!['Observation','Hypothesis'].includes(n.kind)).map(n=>({...n}));
  const get=(id:string)=>nodes.find(n=>n.id===id)!;
  const bodyRooms:Record<string,string>={pip:'hub',bolt:'hub',moss:'stores',echo:'airlock'};
  nodes.forEach(n=>{
    if(n.kind==='Task'){n.status='pending';n.owner='';}
    if(n.kind==='Body'){n.status=n.id==='echo'?'standby':'online';n.room=bodyRooms[n.id];n.battery=100;n.agent=n.id==='echo'?undefined:'agent-'+n.role;n.carrying=[];}
    if(n.kind==='System')n.status=n.id==='bus'?'unknown':n.id==='samples'?'at_risk':'degraded';
    if(n.kind==='Item'){n.status='available';n.room='stores';}
  });
  let edges=source.edges.filter(e=>['CONNECTS','DEPENDS_ON','REQUIRES','HAS_CAPABILITY'].includes(e.type));
  const events=source.events.filter(e=>e.tick<=tick);
  const addOriginal=(id:string)=>{if(!nodes.some(n=>n.id===id)){const original=source.nodes.find(n=>n.id===id);if(original)nodes.push({...original});}};
  for(const e of events){
    const d=e.data;const task=typeof d.task==='string'?nodes.find(n=>n.id===d.task):undefined;
    const body=typeof d.body==='string'?nodes.find(n=>n.id===d.body):undefined;
    if(e.category==='coordination'){
      const reserved=e.evidence.map(id=>nodes.find(n=>n.id===id)).find(n=>n?.kind==='Task');
      if(reserved){reserved.status='active';reserved.owner=e.actor;}
    }
    if(e.category==='fault'&&e.evidence.includes('bolt'))get('bolt').status='offline';
    if(e.category==='handoff'){
      get('bolt').agent=undefined;get('echo').agent='agent-engineer';get('echo').status='online';
    }
    if(e.category!=='action')continue;
    if(body){const cost:Record<string,number>={move:2,inspect:3,diagnose:2,pick_up:1,drop:1,repair:8,verify:2};body.battery=Number(body.battery)-(cost[String(d.action)]||0);}
    if(d.action==='move'&&body)body.room=String(d.to);
    if(d.action==='inspect'&&task){task.status='done';addOriginal('obs-'+task.target);}
    if(d.action==='diagnose'&&task){task.status='done';get('bus').status='diagnosed';addOriginal('hypothesis-bus');}
    if(d.action==='pick_up'&&body){get('relay').status='carried';get('relay').room=undefined;body.carrying=['relay'];}
    if(d.action==='drop'&&body&&task){get('relay').status='available';get('relay').room=body.room;body.carrying=[];task.status='done';}
    if(d.action==='repair'&&task){task.status='done';get('relay').status='installed';for(const id of ['bus','coolant','antenna'])get(id).status='operational';get('samples').status='stable';}
    if(d.action==='verify'&&task){task.status='done';edges.push({source:String(task.target),target:e.actor,type:'VERIFIED_BY'});}
  }
  for(const b of nodes.filter(n=>n.kind==='Body')){
    if(b.agent)edges.push({source:b.agent,target:b.id,type:'EMBODIES'});
    if(b.room)edges.push({source:b.id,target:b.room,type:'LOCATED_IN'});
  }
  const ids=new Set(nodes.map(n=>n.id));
  edges.push(...source.edges.filter(e=>['ABOUT','SUPPORTED_BY','OBSERVED_BY'].includes(e.type)&&ids.has(e.source)&&ids.has(e.target)));
  const done=nodes.filter(n=>n.kind==='Task'&&n.status==='done').length;
  const run={...source.run,status:done===7?'complete':'running',tick};
  return {run,nodes,edges,events,progress:{done,total:7},metrics:{actions:events.filter(e=>e.category==='action').length,observations:nodes.filter(n=>n.kind==='Observation').length,handoffs:events.filter(e=>e.category==='handoff').length}};
}

type V=[number,number,number];
export type Shot={start:number;end:number;from:V;to:V;look:V;fov:number;kind:string};
export const SHOTS:Shot[]=[
  {start:0,end:3,from:[22,8,38],to:[18,5,29],look:[0,0,0],fov:48,kind:'alert'},
  {start:3,end:8,from:[36,26,48],to:[24,19,34],look:[0,0,0],fov:40,kind:'hero'},
  {start:8,end:10,from:[3.8,2.8,6],to:[2.6,2.1,4.8],look:[-.6,.6,.6],fov:32,kind:'pip'},
  {start:10,end:12,from:[4.6,2.6,5.8],to:[3.8,1.8,4],look:[.7,.6,.35],fov:32,kind:'bolt'},
  {start:12,end:14,from:[5,4,15],to:[3,3,14],look:[0,.6,10],fov:32,kind:'moss'},
  {start:14,end:17,from:[19,12,-.5],to:[16,8,-1],look:[8,0,-5],fov:36,kind:'scan'},
  {start:17,end:19,from:[15,10,11],to:[14,7,10],look:[8,0,5],fov:36,kind:'scan'},
  {start:19,end:22,from:[13,6,-.2],to:[11,4,-1],look:[8,0,-5],fov:33,kind:'failure'},
  {start:22,end:25,from:[28,20,34],to:[22,17,28],look:[0,0,0],fov:40,kind:'memory'},
  {start:25,end:30,from:[6,4,-4],to:[4,2.7,-5],look:[.6,.6,-9.3],fov:35,kind:'handoff'},
  {start:30,end:36,from:[21,20,25],to:[18,17,20],look:[0,1,0],fov:40,kind:'graph'},
  {start:36,end:40,from:[18,18,20],to:[15,14,18],look:[0,1,0],fov:38,kind:'query'},
  {start:40,end:43,from:[5,4,15],to:[4,3,14],look:[0,.6,10],fov:36,kind:'pickup'},
  {start:43,end:47,from:[20,20,28],to:[15,17,22],look:[0,0,3],fov:40,kind:'transport'},
  {start:47,end:51,from:[0,7,0],to:[-2,5,-1],look:[-8,0,-5],fov:36,kind:'delivered'},
  {start:51,end:56,from:[-15,6,1],to:[-12,4,-.5],look:[-8,.6,-5],fov:36,kind:'repair'},
  {start:56,end:59,from:[25,25,33],to:[18,16,25],look:[0,0,0],fov:38,kind:'restored'},
  {start:59,end:62,from:[15,7,12],to:[13,5,10],look:[8,0,5],fov:36,kind:'verifycool'},
  {start:62,end:66,from:[15,7,1],to:[13,5,-.5],look:[8,0,-5],fov:36,kind:'verifycomm'},
  {start:66,end:76,from:[34,24,46],to:[23,18,34],look:[0,0,0],fov:42,kind:'ui'},
  {start:76,end:84,from:[28,20,36],to:[22,18,30],look:[0,0,0],fov:40,kind:'metrics'},
  {start:84,end:90,from:[42,28,52],to:[30,22,42],look:[0,0,0],fov:44,kind:'outro'},
];
export const shotAt=(t:number)=>SHOTS.find(s=>t>=s.start&&t<s.end)||SHOTS.at(-1)!;
