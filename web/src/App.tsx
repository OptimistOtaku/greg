import { Component, useCallback, useEffect, useRef, useState } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Activity, ArrowDownToLine, ArrowRight, Battery, Check, ChevronRight, CircleHelp, Code2, Command, Crosshair, Database, Hexagon, Layers3, LoaderCircle, Network, Orbit, Pause, Play, Radio, RotateCcw, ScanLine, ShieldCheck, SkipForward, Sparkles, Unplug, X, Zap } from 'lucide-react';
import Station from './Station';
import type { Entity, Health, Receipt, Snapshot } from './types';

async function api<T>(path:string,body?:unknown):Promise<T>{
  const response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){let message=`Request failed (${response.status})`;try{const detail=(await response.json()).detail;message=typeof detail==='string'?detail:detail?.message||message;}catch{/* Non-JSON infrastructure errors retain their status. */}throw new Error(message);}
  return response.json();
}

class SceneBoundary extends Component<{children:ReactNode},{failed:boolean}>{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(error:Error,info:ErrorInfo){console.error('3D renderer',error,info);}
  render(){return this.state.failed?<div className="scene-fallback"><Orbit size={40}/><h2>3D rendering is unavailable</h2><p>Enable hardware acceleration and reload. The live crew controls and evidence remain available.</p></div>:this.props.children;}
}

const ROLE_NAMES:Record<string,string>={scout:'Survey & diagnosis',engineer:'Systems & repair',carrier:'Supply & transport',reserve:'Adaptive reserve'};
const ACTOR_NAMES:Record<string,string>={'agent-scout':'NAVIGATOR','agent-engineer':'MECHANIC','agent-carrier':'QUARTERMASTER','MISSION CONTROL':'MISSION CONTROL'};
const KIND_COLOR:Record<string,string>={Room:'#82b3ca',Body:'#e6bc80',Agent:'#a9e7ce',System:'#85b2dd',Task:'#bab1dc',Observation:'#ddc9a1',Hypothesis:'#e7b17c',Item:'#bdd8ca',Capability:'#9ab1bb'};

function EventItem({event,onSelect}:{event:Receipt;onSelect:()=>void}){
  const time=new Date(event.timestamp).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const Icon=event.category==='fault'?Unplug:event.category==='handoff'?Sparkles:event.category==='complete'?ShieldCheck:event.category==='coordination'?Network:event.category==='tool'?Code2:Radio;
  return <button className={`event-item ${event.category}`} onClick={onSelect}>
    <span className="event-icon"><Icon size={13}/></span>
    <span className="event-content"><span className="event-meta"><strong>{ACTOR_NAMES[event.actor]||event.actor}</strong><time>{time}</time></span><span className="event-title">{event.name}</span><span className="event-detail">{event.detail}</span>{event.query&&<span className="query-badge"><Database size={9}/>{event.query.replaceAll(',', ' · ')}</span>}</span>
  </button>;
}

export default function App(){
  const [state,setState]=useState<Snapshot|null>(null);
  const [health,setHealth]=useState<Health|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [connected,setConnected]=useState(false);
  const [selected,setSelected]=useState<string|null>(null);
  const [receipt,setReceipt]=useState<Receipt|null>(null);
  const [view,setView]=useState<'station'|'graph'>('station');
  const [mode,setMode]=useState('simulation');
  const [showQueries,setShowQueries]=useState(false);
  const [queries,setQueries]=useState<Record<string,string>>({});
  const [queryTab,setQueryTab]=useState('shared_cause');
  const [tab,setTab]=useState<'activity'|'evidence'>('activity');
  const [showChannel,setShowChannel]=useState(false);
  const initInFlight=useRef(false);
  const feedRef=useRef<HTMLDivElement>(null);
  const initialize=useCallback(async()=>{
    if(initInFlight.current)return;
    initInFlight.current=true;setBusy(true);setError('');
    try{const h=await api<Health>('/health');setHealth(h);if(h.database!=='connected')throw new Error('FalkorDB is offline. Start Docker Desktop, then run docker compose up -d --wait.');const requestedRun=new URLSearchParams(window.location.search).get('run');const latest=await api<Snapshot|{run:null}>(requestedRun?`/runs/${encodeURIComponent(requestedRun)}`:'/runs/latest');const current=latest.run?latest as Snapshot:await api<Snapshot>('/runs',{mode:'simulation'});setState(current);setMode(current.run.mode);setConnected(true);}catch(e){setError((e as Error).message);setConnected(false);}finally{initInFlight.current=false;setBusy(false);}
  },[]);
  useEffect(()=>{void initialize();},[initialize]);
  useEffect(()=>{
    if(!state?.run.id)return;
    const source=new EventSource(`/api/runs/${state.run.id}/events`);
    source.onmessage=e=>{setState(JSON.parse(e.data));setConnected(true);};
    source.onerror=e=>{setConnected(false);if(e instanceof MessageEvent){try{setError(JSON.parse(e.data).error);}catch{/* Browser network errors have no JSON payload. */}}};
    return ()=>source.close();
  },[state?.run.id]);
  useEffect(()=>{if(feedRef.current)feedRef.current.scrollTop=0;},[state?.events.length]);
  const perform=async(operation:()=>Promise<unknown>)=>{setBusy(true);setError('');try{await operation();if(state){const next=await api<Snapshot>(`/runs/${state.run.id}`);setState(next);}}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  const create=async()=>{setBusy(true);setError('');try{const next=await api<Snapshot>('/runs',{mode});setState(next);setSelected(null);setReceipt(null);}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  const openQueries=async(name='shared_cause')=>{setQueryTab(name.split(',')[0]);setShowQueries(true);try{setQueries(await api<Record<string,string>>('/queries'));}catch(e){setError((e as Error).message);}};
  const select=(id:string)=>{setSelected(id);setReceipt(null);setShowChannel(true);};
  const exportRun=()=>{if(!state)return;const url=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`greg-${state.run.id}.json`;a.click();URL.revokeObjectURL(url);};
  const nodes=state?.nodes||[];
  const bodies=nodes.filter(n=>n.kind==='Body');
  const tasks=nodes.filter(n=>n.kind==='Task');
  const observations=nodes.filter(n=>n.kind==='Observation');
  const hypothesis=nodes.find(n=>n.kind==='Hypothesis');
  const selectedNode=nodes.find(n=>n.id===selected);
  const complete=state?.run.status==='complete';
  const latestModel=[...(state?.events||[])].reverse().find(e=>e.data?.model)?.data?.model;
  const percent=state?Math.round(state.progress.done/state.progress.total*100):0;
  const blocked=state?.edges.some(e=>e.type==='CONNECTS'&&e.source==='hub'&&e.target==='power'&&e.blocked);
  const events=(state?.events||[]).filter(e=>tab==='activity'||e.query||e.category==='handoff'||e.category==='complete').slice().reverse();
  const phase=complete?'RECOVERY VERIFIED':tasks.find(t=>t.id==='repair')?.status==='done'?'VERIFYING SYSTEMS':tasks.find(t=>t.id==='correlate')?.status==='done'?'COORDINATING REPAIR':'BUILDING SHARED UNDERSTANDING';
  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="/" aria-label="GREG mission control"><span className="brand-mark"><Command size={23}/></span><strong>GREG<span>®</span></strong></a>
      <span className="brand-caption">COLLECTIVE INTELLIGENCE<br/><b>ORBITAL FIELD TEST / 001</b></span>
      <nav className="topnav"><span className="nav-current"><Orbit size={13}/> Mission control</span><button onClick={()=>void openQueries()}><Database size={13}/> Graph tools</button></nav>
      <div className="connection"><span className={`dot ${connected?'':'amber'}`}/><span>{connected?'FALKORDB CONNECTED':'AWAITING DATABASE'}</span></div>
      <span className="local-tag">LOCAL / SYNTHETIC</span>
    </header>

    {(error||state?.error)&&<div className="error-banner" role="alert"><Unplug size={14}/><span>{error||state?.error}</span>{!state&&<button onClick={()=>void initialize()}>Retry connection</button>}<button aria-label="Dismiss error" onClick={()=>setError('')}><X size={14}/></button></div>}

    <div className="workspace">
      <aside className="mission-panel">
        <div className="section-eyebrow"><span className="index">01</span> THE MISSION</div>
        <h1>BRING<br/>ORPHEUS<br/><span>BACK ONLINE.</span></h1>
        <p className="mission-copy">Two systems down. A connected crew.<br/>One shared understanding.</p>
        <div className="mission-progress"><div><span>RECOVERY</span><strong>{percent}<small>%</small></strong></div><div className="progress-track"><i style={{width:`${percent}%`}}/></div><small>{state?.progress.done||0} / {state?.progress.total||7} objectives verified</small></div>
        <div className="objectives">
          {[['coolant','Restore cooling'],['antenna','Restore communications'],['samples','Preserve research samples']].map(([id,label])=>{const system=nodes.find(n=>n.id===id);const done=id==='samples'?system?.status==='stable':state?.edges.some(e=>e.source===id&&e.type==='VERIFIED_BY');return <div key={id} className={done?'objective done':'objective'}><span>{done?<Check size={11}/>:<span/>}</span><p>{label}</p><small>{id==='samples'?(done?'STABLE':'AT RISK'):done?'VERIFIED':'PENDING'}</small></div>;})}
        </div>
        <div className="divider"/>
        <div className="section-eyebrow">CREW KNOWLEDGE <span className="tiny-count">{observations.length+(hypothesis?1:0)}</span></div>
        <button className="knowledge-summary" onClick={()=>{setView('graph');if(hypothesis)select(hypothesis.id);}}><Network size={21}/><span><strong>{hypothesis?'Shared cause identified':`${observations.length} / 2 observations shared`}</strong><small>{hypothesis?'Cooling + comms → power bus':'Local findings become crew evidence'}</small></span><ChevronRight size={13}/></button>
        <div className="test-conditions"><span className="section-eyebrow">STRESS THE CREW</span><p>Change the conditions. Watch the crew adapt.</p><button disabled={!state||busy||complete} onClick={()=>void perform(()=>api(`/runs/${state!.run.id}/corridor`,{start:'hub',end:'power',blocked:!blocked}))}><Unplug size={13}/>{blocked?'Reopen power corridor':'Seal power corridor'}<ArrowRight size={13}/></button></div>
        <div className="mission-footer"><Hexagon size={15}/><span>Agents share knowledge.<br/>Bodies define what they can do.</span></div>
      </aside>

      <main className="main-stage">
        <div className="stage-toolbar"><div className="view-switch"><button className={view==='station'?'active':''} onClick={()=>setView('station')}><Layers3 size={13}/> Station</button><button className={view==='graph'?'active':''} onClick={()=>setView('graph')}><Network size={13}/> Knowledge graph</button></div><button className="channel-toggle" onClick={()=>setShowChannel(!showChannel)}><Radio size={13}/> Crew channel</button><div className="stage-phase"><span className={`dot ${complete?'':'amber'}`}/>{phase}</div></div>
        <section className="viewport" aria-label={view==='station'?'Interactive 3D space station':'Live 3D knowledge graph'}>
          <div className="viewport-title"><span>LOW EARTH ORBIT · SYNTHETIC ENVIRONMENT</span><h2>{view==='station'?'ORPHEUS STATION':'THE COLLECTIVE GRAPH'}</h2><p>{view==='station'?'A crew is more than the sum of its bodies.':'Connections the crew actually uses to decide and act.'}</p></div>
          {state?<SceneBoundary><Station state={state} selected={selected} onSelect={select} view={view}/></SceneBoundary>:<div className="scene-loading"><Orbit size={44} className={busy?'spin':''}/><h2>{busy?'Connecting the crew':'Waiting for FalkorDB'}</h2><p>{busy?'Loading persistent station state…':'The live station starts when the graph is available.'}</p>{!busy&&<button onClick={()=>void initialize()}>Retry connection</button>}</div>}
          <div className="scene-corner top-left"/><div className="scene-corner top-right"/><div className="scene-corner bottom-left"/><div className="scene-corner bottom-right"/>
          {complete&&view==='station'&&<div className="complete-banner"><ShieldCheck size={19}/><span><strong>MISSION ACCOMPLISHED</strong>Recovery verified at both subsystems.</span></div>}
          <div className="viewport-bottom"><span><Crosshair size={12}/> DRAG TO ORBIT <i/> SCROLL TO ZOOM <i/> CLICK TO INSPECT</span><span className="graph-count"><Database size={11}/>{nodes.length} ENTITIES · {state?.edges.length||0} CONNECTIONS</span></div>
          {view==='station'&&<div className="scene-legend"><span><i style={{background:'#9de2c6'}}/>Crew</span><span><i style={{background:'#dfa86a'}}/>Needs attention</span><span><i style={{background:'#7fa7c5'}}/>Infrastructure</span></div>}
        </section>

        <section className="crew-section"><div className="crew-heading"><span className="section-eyebrow"><span className="index">02</span> EMBODIED CREW</span><span>{bodies.filter(b=>b.status==='online').length} ACTIVE <i/> {bodies.filter(b=>b.status==='standby').length} RESERVE</span></div>
          <div className="crew-grid">{bodies.map(b=>{const agent=nodes.find(n=>n.id===b.agent);const active=tasks.find(t=>t.owner===b.agent&&t.status==='active');const replacement=b.status==='offline'?bodies.find(other=>other.status==='online'&&other.agent&&nodes.some(n=>n.id===other.agent&&n.role===b.role)):undefined;return <article key={b.id} className={`crew-card ${selected===b.id?'selected':''} ${b.status}`} style={{'--robot':b.color} as React.CSSProperties}>
            <button className="crew-main" onClick={()=>select(b.id)}><span className="mini-bot"><span/><i/><i/></span><span><strong>{b.name}<small>{b.status==='standby'?'RESERVE':b.status==='offline'?'OFFLINE':b.id==='echo'?'TRANSFERRED':'ONLINE'}</small></strong><p>{ROLE_NAMES[String(agent?.role||b.role)]}</p></span></button>
            <div className="crew-task"><span className={active?'dot':'dot muted'}/><span>{b.status==='offline'?(replacement?`Agent now in ${replacement.name}`:b.agent?'Awaiting body transfer':'Body offline'):b.status==='standby'?'Ready to inherit an agent':active?active.name:complete?'Mission verified':agent?'Standing by for a task':'No agent bound'}</span></div>
            <div className="crew-bottom"><span><Battery size={12}/>{b.battery}%</span><span className="agent-binding">{agent?agent.name:'UNBOUND'}</span>{b.status==='online'&&<button title={`Disable ${b.name} and test crew recovery`} aria-label={`Disable ${b.name}`} disabled={busy||complete} onClick={()=>void perform(()=>api(`/runs/${state!.run.id}/bodies/${b.id}/disable`,{}))}><Unplug size={12}/></button>}</div>
          </article>;})}</div>
        </section>
        <footer className="run-controls"><div className="controller-label"><span className="dot"/><div><strong>{state?.run.mode==='gemini'?'GEMINI CREW':'SIMULATION CONTROLLER'}</strong><small>{state?.run.mode==='gemini'?String(latestModel||health?.model||'Gemini'):'Deterministic policy · real graph decisions'}</small></div></div><div className="run-buttons"><button className="icon-button" aria-label="Execute one crew step" title="Execute one crew step" disabled={!state||busy||state.auto||complete} onClick={()=>void perform(()=>api(`/runs/${state!.run.id}/step`,{}))}>{busy?<LoaderCircle size={16} className="spin"/>:<SkipForward size={16}/>}</button><button className={`play-button ${state?.auto?'running':''}`} disabled={!state||busy||complete} onClick={()=>void perform(()=>api(`/runs/${state!.run.id}/auto`,{enabled:!state!.auto}))}>{state?.auto?<Pause size={14}/>:<Play size={14}/>} {complete?'Recovery complete':state?.auto?'Pause crew':'Activate crew'}</button></div></footer>
      </main>

      <aside className={`activity-panel ${showChannel?'mobile-open':''}`}><div className="channel-header"><div><Radio size={16}/><h2>CREW CHANNEL</h2></div><span className={connected?'live-indicator':'live-indicator offline'}>{connected?'LIVE':'OFFLINE'}</span><button className="channel-close" aria-label="Close crew channel" onClick={()=>setShowChannel(false)}><X size={15}/></button></div><div className="channel-tabs"><button className={tab==='activity'?'active':''} onClick={()=>setTab('activity')}>Activity <span>{state?.events.length||0}</span></button><button className={tab==='evidence'?'active':''} onClick={()=>setTab('evidence')}>Evidence <Network size={11}/></button></div>
        <div className="event-feed" ref={feedRef}>{events.map(e=><EventItem key={e.id} event={e} onSelect={()=>{setReceipt(e);setSelected(null);}}/>)}{!events.length&&<div className="empty-feed"><Radio size={21}/><p>The crew channel is quiet.</p><small>Activate the crew to begin collecting evidence.</small></div>}</div>
        {(selectedNode||receipt)&&<div className="inspector">
          <div className="inspector-header">
            <span><ScanLine size={12}/> {receipt?'ACTION RECEIPT':'GRAPH INSPECTOR'}</span>
            <button aria-label="Close inspector" onClick={()=>{setSelected(null);setReceipt(null);}}><X size={13}/></button>
          </div>
          {selectedNode?<>
            <span className="entity-kind" style={{color:KIND_COLOR[selectedNode.kind]}}>{selectedNode.kind}</span>
            <h3>{selectedNode.name}</h3>
            <p>{selectedNode.detail||`${selectedNode.status||String(selectedNode.sector||'Connected station entity')}${selectedNode.room?' · '+nodes.find(n=>n.id===selectedNode.room)?.name:''}`}</p>
            {selectedNode.capabilities&&<div className="cap-tags">{selectedNode.capabilities.map(c=><span key={c}>{c}</span>)}</div>}
            <div className="inspector-links">{state?.edges.filter(e=>e.source===selectedNode.id||e.target===selectedNode.id).slice(0,7).map((e,i)=>{
              const other=e.source===selectedNode.id?e.target:e.source;
              return <button key={i} onClick={()=>select(other)}><span>{e.type.replaceAll('_',' ').toLowerCase()}</span><strong>{nodes.find(n=>n.id===other)?.name||other}</strong><ChevronRight size={11}/></button>;
            })}</div>
          </>:receipt?<>
            <h3>{receipt.name}</h3><p>{receipt.detail}</p>
            <small className="receipt-id">RECEIPT {receipt.id} · STEP {receipt.tick}</small>
            {receipt.query&&<button className="text-link" onClick={()=>void openQueries(receipt.query)}><Code2 size={12}/> Inspect executed Cypher <ArrowRight size={12}/></button>}
            <div className="inspector-links">{receipt.evidence?.map(id=><button key={id} onClick={()=>select(id)}><span>supported by</span><strong>{nodes.find(n=>n.id===id)?.name||id}</strong><ChevronRight size={11}/></button>)}</div>
            {Object.keys(receipt.data).length>0&&<pre className="receipt-data">{JSON.stringify(receipt.data,null,2)}</pre>}
          </>:null}
        </div>}
        <div className="channel-stats"><div><strong>{state?.metrics.actions||0}</strong><span>ACTIONS</span></div><div><strong>{state?.metrics.observations||0}</strong><span>OBSERVATIONS</span></div><div><strong>{state?.metrics.handoffs||0}</strong><span>HANDOFFS</span></div></div>
      </aside>
    </div>

    <footer className="app-footer"><span><Network size={12}/> SHARED KNOWLEDGE. DISTRIBUTED ACTION.</span><div><label htmlFor="crew-mode">CONTROLLER</label><select id="crew-mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="simulation">Simulation</option><option value="gemini" disabled={!health?.model_available}>Gemini {!health?.model_available?'· key required':''}</option></select><button disabled={busy} onClick={()=>void create()} title="Start a new persistent mission"><RotateCcw size={12}/> New mission</button><button disabled={!state} onClick={exportRun}><ArrowDownToLine size={12}/> Export evidence</button><button onClick={()=>void openQueries()} aria-label="View graph queries"><CircleHelp size={13}/></button></div></footer>

    {showQueries&&<div className="modal-backdrop" onClick={()=>setShowQueries(false)}><section className="query-modal" onClick={e=>e.stopPropagation()}><header><div><span className="section-eyebrow">FALKORDB / EXECUTED TOOLS</span><h2>The graph does the work.</h2></div><button onClick={()=>setShowQueries(false)} aria-label="Close queries"><X size={20}/></button></header><p>These parameterized Cypher statements run in the crew backend. Select a tool to inspect its actual query.</p><div className="query-tabs">{Object.keys(queries).map(q=><button className={q===queryTab?'active':''} key={q} onClick={()=>setQueryTab(q)}>{q.replaceAll('_',' ')}</button>)}</div><pre>{queries[queryTab]?.trim()||'Loading query source…'}</pre><div className="query-note"><Database size={14}/><span>Primary graph: <b>{health?.graph||'greg_crew'}</b> · task eligibility, routing, evidence and embodiment are persisted in FalkorDB.</span></div></section></div>}
  </div>;
}
