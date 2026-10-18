# GREG: quick technical walkthrough

## Five-minute review

1. Read the README setup and graph diagram, then watch the 90-second demo in the
   [release](https://github.com/OptimistOtaku/greg/releases/tag/v0.1.0-demo).
2. Start FalkorDB and the API with the README commands. Create a simulation
   mission and activate the crew; this uses actual FalkorDB, with no LLM key.
3. Open **Knowledge graph** and **Graph tools**. Follow the two observations to
   their systems and the common upstream bus. Inspect the hypothesis's two
   `SUPPORTED_BY` edges and the action receipts' executed Cypher.
4. In a new mission disable BOLT after its inspection. The engineer retains
   access to shared observations and inhabits ECHO at the airlock. It must travel
   to the repair site; the handoff does not teleport it.
5. Confirm relay delivery precedes repair, then two subsystem checks precede
   completion. Export the evidence JSON.

For real-model reproduction, follow `docs/live-gemini.md` and supply your own
local Gemini key. Three completed authored runs and the interruption history
are linked from the README; simulation is not presented as live LLM behavior.

## Explain these design decisions

**Why a graph?** Eligibility joins capabilities, embodiment and task dependencies;
diagnosis traverses observations and system dependencies; routes depend on
changing corridor relationships. These relationships directly affect actions.

**What survives a body failure?** Observations retain provenance to the agent.
The agent's `EMBODIES` relationship changes to a capable standby body. Task claims
are released as appropriate; cargo remains recoverable at its physical location.

**What prevents hallucinated actions?** Bounded tools, graph-derived eligibility,
and host checks for capability, body status, location, battery, evidence and
prerequisites. The model cannot execute arbitrary Cypher or code.

**What proves centrality?** `scripts/benchmark.py` removes observation `ABOUT`
relationships, retains observation nodes, and verifies diagnosis is rejected.
Restored links plus a fresh client recover the mission. The app has no database
fallback. This establishes the implementation's dependency on graph links,
not superiority over another database architecture.

**What is the Earth use case?** The same coordination pattern could support
industrial inspection, warehouse crews or disaster-response teams. Adapters for
real robots, sensors and actuation are future work; only the synthetic station
environment is implemented and evaluated.

**What are its limits?** Authored tasks/fault rules, fixed model weights, one API
worker, no distributed action transaction or public authentication, no physical
robotics validation. See `docs/product.md` for operational details.

## Source map

| Concern | Source |
| --- | --- |
| Executed graph queries | `greg/queries.py` |
| Graph connection / persistence | `greg/database.py` |
| Action validation / graph mutations | `greg/service.py` |
| Deterministic scheduling | `greg/controller.py` |
| Gemini tool loop | `greg/gemini.py` |
| MCP tool transport | `greg/mcp_server.py`, `greg/mcp_client.py` |
| HTTP / SSE | `greg/main.py` |
| Station / graph UI | `web/src/Station.tsx` |
| Directed film replay | `web/src/film/` |
| Evaluations and methods | `docs/benchmarks.md`, `docs/live-gemini.md` |
