# GREG demonstration

Use simulation for a reproducible walkthrough. It runs real graph queries but
does not demonstrate LLM reasoning. The three completed live Gemini trials,
saved mission links, provider interruptions and reproduction instructions are in
[live-gemini.md](live-gemini.md) and `artifacts/gemini-evaluation.json`.

1. Open mission control. Show the connected database badge, controller label,
   three active robots and the reserve ECHO body.
2. Activate the crew. Navigator and Mechanic reserve distinct inspection tasks,
   visit different rooms and share observations through FalkorDB.
3. Open Knowledge graph. Inspect new observation nodes and the supported common
   source hypothesis. Open an action receipt and its executed Cypher.
4. Watch the carrier collect a relay and deliver it to the power core. Engineering
   becomes eligible only after the delivery prerequisite completes.
5. Watch the repair and subsequent verification at both subsystems. The run ends
   only when cooling and communications have been verified.
6. Start another mission. Seal the hub/power corridor and show the alternate
   hub/airlock/power route.
7. Disable a robot using its unplug button. Its agent transfers to ECHO at the
   airlock, retains shared knowledge and continues from that body's location.
   An offline carrier's cargo is recoverable at its last location.
8. Export evidence. JSON includes topology, task state, observation provenance,
   assignments and timestamped action receipts.

Pitch: “GREG coordinates a crew through shared operational knowledge. The space
station is a bounded stress test: connected failures, different bodies and
changing routes. The graph determines what the crew can do, which evidence
connects, and how it recovers when a body fails.”

The demo establishes working simulator behavior. Do not call simulation a live
Gemini run, claim a new learning algorithm, or imply physical robotics validation.
