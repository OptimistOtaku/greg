# GREG build contract

GREG is a reusable crew coordination prototype. A synthetic orbital station is
its stress-test environment. Agents inhabit capability-constrained robot bodies,
use tools, share evidence, reserve work, and recover from body outages.

FalkorDB owns all durable station state, embodiment, capabilities, observations,
tasks, claims and action receipts. No alternate in-memory world database exists.
The browser interpolates recorded movement for presentation only.

Build order: graph state + action semantics; meaningful integration checks;
FastAPI and Gemini tool loop; live 3D station and evidence inspector; MCP surface;
fresh setup and submission docs. Run a clearly labeled deterministic controller
when a user chooses simulation. Never label deterministic behavior as Gemini.

First mission: restore cooling and communications, whose power dependencies
overlap; diagnose the common source, transport a replacement, repair the bus,
and verify both goals. Disable a robot or block a corridor mid-mission to test
capability-aware reallocation and routing.

Scope: one station, three robot bodies, three separate agent contexts, bounded
tools, a deterministic simulator, real parameterized Cypher and inspectable
evidence. The Gemini model is configurable. No robotics or training claim.

Acceptance: graph paths influence routing and task choices; capabilities and
location constrain actions; inspection establishes observations; diagnosis
requires shared evidence; parts must be carried before repair; reservations
prevent duplicate work; offline bodies release unfinished tasks; verification
requires the restored system; stale or invalid operations reject without mutation;
database outages produce errors. Synthetic data only. API failures remain visible.
