export type Entity = {
  id:string; kind:string; name:string; status?:string; role?:string; room?:string;
  battery?:number; color?:string; agent?:string; capabilities?:string[]; carrying?:string[];
  x?:number; y?:number; z?:number; detail?:string; signal?:string; owner?:string;
  action?:string; target?:string; preferred_role?:string; [key:string]:unknown;
};
export type Edge = {source:string;target:string;type:string;blocked?:boolean};
export type Receipt = {id:string;name:string;category:string;actor:string;detail:string;tick:number;timestamp:string;query:string;evidence:string[];data:Record<string,unknown>};
export type Snapshot = {run:Entity & {mode:string;tick:number;status:string};nodes:Entity[];edges:Edge[];events:Receipt[];progress:{done:number;total:number};metrics:{actions:number;observations:number;handoffs:number};auto?:boolean;error?:string};
export type Health = {database:string;model_available:boolean;model:string;graph:string};
