# Benchmark methodology

Run `uv run python scripts/benchmark.py` with FalkorDB running. The benchmark
creates a randomly named `greg_bench_*` graph, launches a separate loopback API
process on an available port, writes `artifacts/benchmark-results.json`, stops
its API process and deletes only its own test graph. It does not inject faults
into the demo mission, stop Docker, or call an LLM provider.

The JSON contains environment/package versions, configuration, raw latency
samples, per-trial outcomes and summaries. A failed assertion produces a failed
report and a nonzero exit status. `artifacts/benchmark-server.log` contains the
temporary server's diagnostics. Command-line options control repeat counts,
query/HTTP sample counts and concurrent HTTP workers.

## What each measurement establishes

| Measurement | Workload and correctness condition |
| --- | --- |
| Recovery | Ten repeats each of six authored scenarios, in a fixed shuffled order. Every completed mission must finish all seven tasks, install the relay and retain two verification edges. Timing includes graph seeding, fault injection, controller execution and the final verification snapshot; excludes UI animation and LLM inference. |
| Failure-timing sweep | `scripts/benchmark_fault_timing.py` tests each of three active bodies failing after 0, 4, 8, 12, 16 or 20 controller steps: 18 predetermined combinations. It records failure location, observations and completed tasks at failure. Each must finish all tasks with two verification edges and exactly one body handoff. Raw results are in `artifacts/fault-timing-results.json`. |
| Evidence-link ablation | Gather two genuine simulated observations, then remove their `ABOUT` relationships while retaining both observation nodes. The same controller must fail to diagnose. Restore the links, recreate the database client/service/controller, and require full recovery. This checks whether semantic relationships matter. |
| Memory reconstruction | After restoring links, new application objects must retrieve the same two observations and derive the bus diagnosis from the graph, then complete without the original controller cursor. This is client reconstruction, not a database restart or crash-durability test. |
| Claim contention | Two different agents concurrently attempt to reserve the same eligible task. Exactly one must succeed. Twenty races use the production service lock and real graph writes. This is a single-process guarantee. |
| Cypher latency | Five actual product read queries, each with ten untimed warmups followed by 200 timed sequential requests. All measured queries must return nonempty results. Measurements include Python SDK, network round trip and FalkorDB execution; they are not server-only execution time. The report records total graph size. |
| HTTP | An actual separate single-worker uvicorn process serves loopback requests against the benchmark graph. Each endpoint has five warmups and 100 sequential timed requests. Eight client threads then request 100 snapshots, checking status and mission identity. Throughput is observed throughput at that load, not maximum capacity. |
| SSE | Measure receipt of the first valid graph snapshot over the streaming endpoint. This single sample is a functionality and startup-latency check, not a streaming-latency distribution. |
| Rejected work | Attempt to claim the repair task with an incapable carrier before prerequisites complete. The tool endpoint must return its documented HTTP 200 structured `{ok: false}` result, with the task still pending and the carrier battery unchanged. |
| MCP | Real stdio negotiation and `inspect_context` calls through MCP → HTTP → FalkorDB. Measure 20 calls on a persistent session after three warmups, then three calls using the production bridge, which starts a fresh MCP process per call. Startup and process teardown are included in the latter. |

Latency summaries use median and nearest-rank p95. Raw measurements are in
milliseconds. Tests run on the participant's Windows machine with local Docker;
background desktop activity and the live demo server can affect timing. Workloads
run sequentially rather than concurrently with the test suite.

The initial benchmark harness incorrectly expected HTTP 409 from the tool
dispatcher. Its interrupted report is retained as
`artifacts/benchmark-harness-first-attempt.json`; it is excluded from published
numbers. The harness now checks the actual structured tool-result contract and
unchanged state. Direct service/API actions can separately use HTTP 409; agent
tool errors are returned to the caller as structured results.

A second interrupted run (`artifacts/benchmark-endpoint-bug-attempt.json`) exposed
a genuine configuration issue: the production MCP bridge did not forward
`GREG_API_URL` through MCP's restricted child environment. The bridge now passes
that endpoint explicitly without forwarding provider credentials. The benchmark
uses a nondefault API port, so a successful full run validates this fix through
the actual production bridge.

## How to describe the results

Use “60/60 authored deterministic recovery runs completed” rather than “100%
reliable agents.” Repeats exercise the same six fixed scenarios, not 60 independent
unseen tasks. They check repeatability and implementation behavior.

The evidence ablation establishes that GREG's diagnosis depends on graph links.
It does **not** establish that graph memory beats vector retrieval, SQL, a plain
event log or another agent framework. No equivalent competitor baseline has been
implemented, and no LLM reasoning accuracy, hallucination rate, token savings,
production scalability or real robot performance is measured here.

Client reconstruction checks that mission evidence lives outside Python object
memory. It does not test disk persistence, power loss, database restart, backup
restoration, distributed locking or multi-worker writes. The local prototype
requires one API writer process.

The most useful demo evidence is the combination of full mission completion,
two physical verification receipts, a blocked diagnosis when relationships are
removed, and successful recovery after graph memory is made available again.
