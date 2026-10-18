# Live Gemini demo evaluation

These trials execute the real path:

`HTTP step → graph eligibility → Gemini function selection → MCP stdio → HTTP tool → FalkorDB action → graph receipt`.

The model chooses every executed crew tool/action. Host scheduling reads graph
eligibility, capabilities and role preferences. World transitions remain bounded
and validated by the service. There is no deterministic-controller fallback.

## Run and resume

Configure an API key only in the ignored local `.env`, set `GEMINI_MODEL`, and
start the single-worker API. Then:

```powershell
uv run python scripts/check_gemini.py
uv run python scripts/evaluate_gemini.py
# If provider availability/quota interrupts a trial:
uv run python scripts/evaluate_gemini.py --resume
```

The evaluator performs normal recovery, recovery with the hub/power corridor
closed, and recovery with BOLT disabled after the first observation. Each
successful trial must complete all seven tasks and retain two physical
verification edges. The outage case must actually inject its fault.

Missions remain in the local `greg_crew` graph. A saved mission can be opened
using `http://127.0.0.1:8000/?run=MISSION_ID`; the report includes these links.
This opens its current saved state and receipts. It does not replay an animated
timeline or make new model calls. Exported snapshots provide static evidence
when the original local database is unavailable.

The evaluator writes its report after every turn and exports complete snapshots:

- `artifacts/gemini-evaluation.json`
- `artifacts/gemini-nominal-replay.json`
- `artifacts/gemini-blocked-corridor-replay.json`
- `artifacts/gemini-mid-mission-body-outage-replay.json`

## Actual interruptions and fixes

The first Gemini 3.8 Flash run exposed a conversation-format bug: a retained
function call had lost its originating user message. Google rejected the next
turn. The adapter now keeps one complete previous turn and injects current graph
context for every decision. Regression tests check the conversation sequence.

The next 3.8 trial reached both observations but hit provider-side high demand.
An explicit operator change selected 3.5 Flash. That trial reached the repair,
then its free-tier request quota was exhausted. Provider diagnostics reported a
20-request daily cap and a reset hours later; short retries could not resolve it.
An explicit operator change selected the available 3.1 Flash-Lite model.

The same nominal mission then resumed from its existing graph after an API
restart, with fresh in-process agent histories. Both observations, the diagnosis,
delivered part and completed repair remained available. Its final verification
completed without resetting the mission or running the deterministic controller.

These interrupted attempts are retained separately rather than omitted:

- `artifacts/gemini-conversation-bug-attempt.json`
- `artifacts/gemini-provider-unavailable-attempt.json`
- `artifacts/gemini-35-provider-interruption.json`

The final report records provider interruptions, explicit model changes and the
model associated with each recorded tool result, including rejections. Model names are requested API
identifiers. A mixed-model resumed mission is not a single-model benchmark.

## Interpretation

These are three authored demonstrations, not a general-purpose agent evaluation
or an estimate of real-world reliability. A model-selected action may be rejected
by the validators and corrected on a later turn; rejected tool results are
reported, not counted as successful physical actions.

`seconds` is the sum of evaluator execution attempts, excluding operator pauses
between resumes. SDK generation retries can occur within a model turn; the report
does not claim to count every provider HTTP attempt. `reported_tokens` sums token
metadata present on tool receipts and is not an invoice or complete billing total.
Requests rejected before a tool receipt and plain-text turns may not be included.

Local `.env` credentials are ignored by Git. Before publishing, the staged secret
check compares all staged files against configured local secret values. The
model receives synthetic mission context, never the API key as prompt text.
