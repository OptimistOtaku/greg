# GREG — submission copy

**Track:** 01 — Agents That Act on Connected Data

**Team:** solo participant; use the registered account's team/name

**Repository:** https://github.com/OptimistOtaku/greg

**Demo download and captions:** https://github.com/OptimistOtaku/greg/releases/tag/v0.1.0-demo

**Run locally:** https://github.com/OptimistOtaku/greg#run-mission-control

## Project name

GREG — Shared knowledge. Distributed action.

## One-line pitch

An AI robot crew that shares operational knowledge in FalkorDB, connects failures,
and keeps working when an agent has to switch bodies.

## Short description

GREG gives AI agents a shared operational graph. In a synthetic orbital station,
three robot roles investigate failures, correlate evidence, coordinate a repair,
and verify recovery. If a body fails, its agent transfers to a capable reserve
body while shared evidence remains available in FalkorDB.

## Problem and solution

Agents acting on partial observations need to agree on what is known, which
work is ready, and who can act. A body failure should not erase shared evidence
or allow duplicate, impossible, or unsupported actions.

GREG separates the agent mind from its body and stores the crew's operational
world in FalkorDB: observations, provenance, system dependencies, tasks, claims,
capabilities, locations, cargo, and action receipts. Gemini selects bounded
tools through MCP; the host validates actions against graph-backed state.

The orbital station is a bounded stress-test demo. A cooling fault and a comms
fault look separate until observations trace to a shared upstream power bus.
One robot delivers a relay; another repairs the bus; both subsystems must be
physically checked before the mission completes. A sealed corridor changes the
available route. A failed body causes a capable replacement to be selected at
its actual location, while evidence remains attached to the agent mind.

## How FalkorDB is central

- Multi-hop `Observation → ABOUT → System → DEPENDS_ON → System` traversal
  finds a common upstream cause only with two distinct observed subsystems.
- Task dependencies and body capabilities determine eligible work.
- A conditional graph mutation reserves a pending task for one agent.
- Corridor relationships determine open routes.
- Capability traversal determines eligible replacement bodies.
- Dependency impact queries determine affected downstream systems.
- Action receipts retain the evidence and queries behind decisions.

The exact executed parameterized Cypher is in `greg/queries.py`; the application
also exposes it through `/api/queries` and its Graph tools inspector. Removing
FalkorDB stops the application. Removing observation `ABOUT` edges blocks
diagnosis despite retaining the observation nodes; restoring them enables
recovery. This ablation is recorded in the benchmark artifacts.

## Track 01 fit

GREG demonstrates multi-hop reasoning, graph queries as agent tools, real MCP
stdio tool transport, actions based on graph results, and explainable receipts.
Shared memory supports these actions; the chosen entry is Track 01 only.

## Technology

FalkorDB / Cypher, Python / FastAPI, Gemini function calling, MCP stdio,
React / TypeScript, Three.js / React Three Fiber, Docker Compose.

## What is working

- Interactive station exterior/cutaway and knowledge graph.
- Labeled deterministic simulation and an optional real Gemini controller.
- Inspection, supported diagnosis, delivery, repair, and two verifications.
- Corridor blockage, robot outages, cargo recovery, and mind/body handoff.
- Inspectable Cypher, receipt history, JSON evidence export, saved missions.

Three authored real-Gemini scenarios completed all seven objectives and two
verifications. Deterministic stress tests completed 60/60 repeated scenarios and
18/18 failure-timing cases. Evidence-link ablation blocked diagnosis 10/10 times;
restored links plus a fresh client recovered 10/10. Shared-cause queries measured
1.190 ms median over 200 local calls on a 5,251-node/14,048-edge graph.
These are local measurements and authored demonstrations, not general robotics
reliability or comparative claims. Provider interruptions and model changes are
disclosed in the README and raw reports.

## Data, original work, and AI assistance

Station topology, tasks, faults, robot geometry, and mission data are original
synthetic content. No private, personal, login-protected, or restricted data is
loaded into the graph. NASA Earth imagery is a frontend visual asset with
credits; it is not graph input. See `docs/data-provenance.md`.

AI coding assistance from Codex was used for research, design, implementation,
debugging, evaluation, documentation, and media production. Runtime agents use
Gemini. The demo uses synthetic narration and an original procedural score;
the promotional thumbnail is AI-generated cover art. The participant chose the
direction, requirements, and revisions and must personally review and be able
to explain the implementation. No claim of unaided development is made.

## Setup / deployment answer

Complete local instructions are provided in the README. Docker starts the real
FalkorDB service; locked Python dependencies and the production web build start
the application at `http://127.0.0.1:8000`. Simulation needs no LLM key. Gemini
mode requires a participant-owned local key and available provider quota.
The service is a trusted, unauthenticated, single-worker local prototype.
There is no public live backend deployment.

## Participant final steps

1. Confirm registration/team details in the signed-in organizer portal.
2. Add the uploaded YouTube URL to the demo field; the GitHub release is an
   additional directly downloadable copy.
3. Select **Track 01 — Agents That Act on Connected Data**.
4. Review any account-specific declarations and submit the form.
5. Keep the confirmation page/receipt; a prepared package is not a saved entry.

The portal requires sign-in, so account-specific fields and final acceptance
have not been verified from this local package. Do not put localhost URLs in
the public deployment field; use the local-setup explanation instead.
