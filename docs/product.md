# GREG architecture and limits

GREG is a prototype crew coordination system. A synthetic orbital station
demonstrates how agents can act through bodies with different capabilities while
sharing operational evidence in FalkorDB. It is not an aerospace simulation.

## Execution

The API is a single local FastAPI process. Its transition lock serializes body
actions, reservations and fault injection. Every validated action changes the
real graph and writes an inspectable receipt. The React/Three.js interface reads
snapshots through server-sent events. Browser movement is visual interpolation
between committed rooms, not an independent physics/world engine.

Run with **one worker**. Multiple graph writes in an action are not a distributed
transaction; this is a trusted local prototype, not a multi-user production API.
The API is bound to localhost and provides no authentication layer.

The graph stores rooms, corridors, systems, bodies, capabilities, agents, task
prerequisites, cargo, observations, hypotheses, claims and action receipts.
`CONNECTS.blocked` controls routes. Each agent's `EMBODIES` relationship points to
its current physical body. Body location, battery and capabilities are checked
before actions. Offline carriers release cargo at their last location. The
reserve body is physically at the airlock and does not teleport to the old body.

An observation is produced by executing an inspection at a subsystem. Diagnosis
uses two distinct observed systems with a common upstream dependency. The
diagnosis is supported within the authored model, not universal causal proof.
Repair requires the replacement part at the repair site. Two subsequent physical
checks verify the restored systems before mission completion.

`Fault` nodes contain simulator ground truth and are excluded from public
snapshots and agent context. Every query is scoped to a mission's `run_id`.

## Two explicit controller modes

**Simulation:** a deterministic role-aware policy reads current graph eligibility,
routes and shared evidence. It is repeatable and visibly labeled. It does not
demonstrate LLM reasoning or model training.

**Gemini:** three separate conversation contexts receive the current graph and
choose bounded function calls. Model weights remain fixed. The model cannot
act until the host scheduler finds an eligible role/task or a capable reserve
body through FalkorDB. It chooses the tool and action; the scheduler does not
execute a simulated action on the model's behalf. One complete previous model
turn is retained per agent, while durable mission memory comes from the graph.
The model cannot
execute arbitrary code or unrestricted Cypher. Missing keys/provider errors do
not switch modes. Both the in-app model controller and external clients use
actual MCP stdio transport to reach those operations through the local API.

Set `GEMINI_API_KEY`, `GEMINI_MODEL` and `GEMINI_MAX_TURNS` in local `.env`. Restart
the API after edits. Live provider behavior needs validation with your key.
Pause prevents starting the next turn; an already-running model request may finish.
Provider 429/5xx generation failures have three bounded SDK attempts. Exhausted
provider errors pause the crew and return a sanitized 502/503 response, retaining
graph state and never changing controller mode.

## Interfaces

- `GET /api/health`: database status and model configuration presence, no secrets.
- `POST /api/runs`: create a persistent mission in simulation or Gemini mode.
- `GET /api/runs/latest`: resume the newest saved mission after a restart.
- `GET /api/runs/{id}`: graph snapshot, action receipts and mission metrics.
- `GET /api/runs/{id}/events`: live snapshot stream.
- `POST /api/runs/{id}/step` and `/auto`: control crew turns.
- `POST /api/runs/{id}/bodies/{body}/disable`: inject a body outage.
- `POST /api/runs/{id}/corridor`: change an existing corridor's blocked state.
- `POST /api/runs/{id}/tools`: bounded tool dispatch through the API writer.
- `GET /api/queries`: exact Cypher source used by product operations.

The MCP stdio server forwards tool calls to the running API. Start it with
`uv run python -m greg.mcp_server`; `GREG_API_URL` defaults to
`http://127.0.0.1:8000`. A client uses the current run ID and `agent-scout`,
`agent-engineer`, or `agent-carrier`. The six tools are inspect_context,
find_route, claim_task, execute_action, inhabit_body, and read_graph_query.

## Limits and future work

Task prerequisites and fault transition rules are authored scenario data.
Dynamic task generation, arbitrary environments, robotics adapters, independent
agent baselines and comparative model evaluations remain future work. A shared
graph alone does not establish a new learning or coordination algorithm.

The three simulated robot roles and one reserve body demonstrate a body boundary;
actual physical bodies require their own observation/action adapters and validation.

The deterministic scenario evaluator reports actual executions of six stress
cases against FalkorDB. It makes no claim of superiority over other methods.
The submission checklist includes a public source repository, a working demo
recording, registration and the organizer's final submission form.
