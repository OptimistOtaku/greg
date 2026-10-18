"""Local reproducible benchmarks against an isolated, real FalkorDB graph.

No provider calls, mocks, product-graph writes, or timing thresholds. Assertions
check correctness; measured speed depends on hardware and background load.
"""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import socket
import statistics
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from greg.controller import SimulationController
from greg.database import GraphStore
from greg.queries import CAPABLE_BODIES, IMPACT, READY_TASKS, ROUTE, SHARED_CAUSE
from greg.service import ActionRejected, CrewService


def distribution(samples):
    values = sorted(samples)
    return {"samples": len(values), "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(values[math.ceil(.95 * len(values)) - 1], 3),
            "min_ms": round(values[0], 3), "max_ms": round(values[-1], 3)}


def timed(call):
    started = time.perf_counter()
    value = call()
    return value, (time.perf_counter() - started) * 1000


def finish(service, run, controller=None, cargo_outage=False):
    controller = controller or SimulationController(service)
    injected = False
    for step in range(90):
        result = controller.step(run)
        if cargo_outage and not injected and service.require(run, "relay")["status"] == "carried":
            service.disable(run, "moss")
            injected = True
        if result.get("waiting"):
            return False, step + 1
        if service.require(run, run)["status"] == "complete":
            state = service.snapshot(run)
            assert state["progress"] == {"done": 7, "total": 7}
            assert service.require(run, "relay")["status"] == "installed"
            assert len([e for e in state["edges"] if e["type"] == "VERIFIED_BY"]) == 2
            assert not cargo_outage or injected
            return True, step + 1
    return False, 90


def prepare_evidence(service, run):
    controller = SimulationController(service)
    for _ in range(30):
        if len(service.store.nodes(run, "Observation")) == 2:
            assert service.store.read(SHARED_CAUSE, run=run)
            return controller
        controller.step(run)
    raise AssertionError("Crew never collected both observations")


def memory_checks(service, repeats):
    rows = []
    for trial in range(repeats):
        run = service.create()
        controller = prepare_evidence(service, run)
        before = service.store.nodes(run, "Observation")
        # Delete only the semantic links, retaining observation nodes/properties.
        service.store.query("MATCH (o:Observation {run_id:$run})-[r:ABOUT]->() DELETE r", run=run)
        assert len(service.store.nodes(run, "Observation")) == 2
        assert service.store.read(SHARED_CAUSE, run=run) == []
        rejected = False
        try:
            blocked, _ = finish(service, run, controller)
            assert not blocked
        except ActionRejected as exc:
            assert "shared cause" in str(exc)
            rejected = True
        assert rejected
        assert service.require(run, run)["status"] != "complete"
        for source, target in [("obs-coolant", "coolant"), ("obs-antenna", "antenna")]:
            service.store.link(run, source, target, "ABOUT")
        # Fresh client/service/controller: no old cursor or Python memory reused.
        fresh = CrewService(GraphStore(service.store.name))
        assert fresh.store.nodes(run, "Observation") == before
        candidate = fresh.store.read(SHARED_CAUSE, run=run)[0]
        assert candidate[0] == "bus" and set(candidate[2]) == {"obs-coolant", "obs-antenna"}
        recovered, steps = finish(fresh, run)
        assert recovered
        rows.append({"trial": trial + 1, "ablation_diagnosis_rejected": rejected,
                     "retained_observations": 2, "recreated_client_completed": recovered,
                     "remaining_controller_steps": steps})
    return rows


def contention_checks(service, repeats):
    rows = []
    for trial in range(repeats):
        run = service.create()
        def claim(agent):
            try:
                service.claim(run, agent, "scan-cooling")
                return True
            except ActionRejected:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            winners = sum(pool.map(claim, ["agent-scout", "agent-engineer"]))
        assert winners == 1
        rows.append({"trial": trial + 1, "contenders": 2, "successful_claims": winners})
    return rows


def query_benchmarks(service, samples):
    run = service.create()
    prepare_evidence(service, run)
    cases = {
        "open_route": (ROUTE, {"run": run, "start": "hub", "end": "power"}),
        "eligible_tasks": (READY_TASKS, {"run": run, "agent": "agent-scout"}),
        "shared_cause": (SHARED_CAUSE, {"run": run}),
        "dependency_impact": (IMPACT, {"run": run, "system": "bus"}),
        "replacement_body": (CAPABLE_BODIES, {"run": run, "required": ["cap-repair", "cap-analyze"]}),
    }
    result = {}
    for name, (query, params) in cases.items():
        for _ in range(10):
            assert service.store.read(query, **params)
        durations = []
        for _ in range(samples):
            value, elapsed = timed(lambda: service.store.read(query, **params))
            assert value, name
            durations.append(elapsed)
        result[name] = {**distribution(durations), "raw_ms": durations}
    count = service.store.read("MATCH (n) RETURN count(n)")[0][0]
    edges = service.store.read("MATCH ()-[r]->() RETURN count(r)")[0][0]
    runs = service.store.read("MATCH (n:Run) RETURN count(n)")[0][0]
    return {"nodes": count, "edges": edges, "missions": runs, "queries": result}


async def mcp_bench(base, run, samples):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = {**os.environ, "GREG_API_URL": base}
    params = StdioServerParameters(command=sys.executable, args=["-m", "greg.mcp_server"], cwd=str(ROOT), env=env)
    startup = time.perf_counter()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            startup_ms = (time.perf_counter() - startup) * 1000
            tools = await session.list_tools()
            durations = []
            for i in range(samples + 3):
                start = time.perf_counter()
                response = await session.call_tool("inspect_context", {"run": run, "agent": "agent-scout"})
                elapsed = (time.perf_counter() - start) * 1000
                assert not response.is_error
                if i >= 3:
                    durations.append(elapsed)
    # The production Gemini bridge creates a fresh MCP process for each call.
    from greg.mcp_client import call_crew_tool
    old = os.environ.get("GREG_API_URL")
    os.environ["GREG_API_URL"] = base
    cold = []
    try:
        for _ in range(3):
            start = time.perf_counter()
            value = await call_crew_tool(run, "agent-scout", "inspect_context", {})
            assert value["agent"]["id"] == "agent-scout"
            cold.append((time.perf_counter() - start) * 1000)
    finally:
        if old is None:
            os.environ.pop("GREG_API_URL", None)
        else:
            os.environ["GREG_API_URL"] = old
    return {"session_startup_ms": round(startup_ms, 3), "tools": len(tools.tools),
            "persistent_session": {**distribution(durations), "raw_ms": durations},
            "production_fresh_process_per_call": {**distribution(cold), "raw_ms": cold}}


def http_bench(service, samples, workers):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "FALKORDB_MISSION_GRAPH": service.store.name}
    log = ROOT / "artifacts" / "benchmark-server.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "greg.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"], cwd=ROOT, env=env, stdout=output, stderr=output,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
                for _ in range(100):
                    try:
                        response = client.get("/api/health")
                        response.raise_for_status()
                        assert response.json()["graph"] == service.store.name
                        break
                    except httpx.ConnectError:
                        if process.poll() is not None:
                            raise RuntimeError(log.read_text())
                        time.sleep(.1)
                else:
                    raise RuntimeError("Benchmark API did not become healthy")
                run = service.create()
                endpoints = {"health": "/api/health", "snapshot": f"/api/runs/{run}",
                             "agent_context": f"/api/runs/{run}/context/agent-scout"}
                results = {}
                for name, endpoint in endpoints.items():
                    for _ in range(5):
                        client.get(endpoint).raise_for_status()
                    durations = []
                    for _ in range(samples):
                        response, elapsed = timed(lambda: client.get(endpoint))
                        response.raise_for_status()
                        if name == "snapshot":
                            assert response.json()["run"]["id"] == run
                        durations.append(elapsed)
                    results[name] = {**distribution(durations), "raw_ms": durations}
                def read_snapshot(_):
                    response, elapsed = timed(lambda: client.get(endpoints["snapshot"]))
                    return response.status_code, elapsed, response.json()["run"]["id"] == run
                start = time.perf_counter()
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    responses = list(pool.map(read_snapshot, range(samples)))
                seconds = time.perf_counter() - start
                ok = sum(status == 200 and correct for status, _, correct in responses)
                assert ok == samples
                concurrent = {"workers": workers, "requests": samples, "successful": ok,
                              "requests_per_second": round(samples / seconds, 2),
                              **distribution([elapsed for _, elapsed, _ in responses])}
                start = time.perf_counter()
                with client.stream("GET", f"/api/runs/{run}/events") as stream:
                    stream.raise_for_status()
                    for line in stream.iter_lines():
                        if line.startswith("data: "):
                            assert json.loads(line[6:])["run"]["id"] == run
                            sse_ms = (time.perf_counter() - start) * 1000
                            break
                    else:
                        raise AssertionError("SSE emitted no snapshot")
                # Real network request to the isolated API must reject invalid work.
                rejected = client.post(f"/api/runs/{run}/tools", json={"agent": "agent-carrier", "name": "claim_task", "arguments": {"task_id": "repair"}})
                assert rejected.status_code == 200
                assert rejected.json()["ok"] is False and rejected.json()["error"]
                assert service.require(run, "repair")["status"] == "pending"
                assert service.require(run, "moss")["battery"] == 100
                mcp = asyncio.run(mcp_bench(base, run, min(samples, 20)))
                return {"transport": "real loopback HTTP, isolated uvicorn process, one worker", "sequential": results,
                        "concurrent_snapshot": concurrent, "first_sse_snapshot_ms": round(sse_ms, 3),
                        "invalid_action": {"http_status": rejected.status_code, "tool_ok": rejected.json()["ok"],
                                           "state_unchanged": True}, "mcp": mcp}
        finally:
            process.terminate()
            process.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--query-samples", type=int, default=200)
    parser.add_argument("--http-samples", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    assert min(args.repeats, args.query_samples, args.http_samples, args.workers) > 0
    started = time.perf_counter()
    store = GraphStore("greg_bench_" + uuid.uuid4().hex[:12])
    service = CrewService(store)
    destination = ROOT / "artifacts" / "benchmark-results.json"
    destination.parent.mkdir(exist_ok=True)
    report = {"schema_version": 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "configuration": vars(args), "environment": {"os": platform.platform(), "cpu": platform.processor(),
              "logical_cpus": os.cpu_count(), "python": platform.python_version(),
              "packages": {p: importlib.metadata.version(p) for p in ["falkordb", "redis", "fastapi", "uvicorn", "httpx", "mcp"]}},
              "scope": "deterministic authored simulation and local infrastructure; no LLM or competitor benchmark",
              "limitations": ["Repeated deterministic scenarios are not independent unseen tasks or a reliability estimate.",
                "Ablation removes ABOUT links; it demonstrates dependence on graph structure, not superiority over SQL, vector memory, or another agent system.",
                "Latency includes Python client and local Docker round trips; 10 warmups per Cypher query and 5 per HTTP endpoint.",
                "Percentiles use nearest rank; timing depends on background load. No orbital physics or physical robots are evaluated.",
                "Client reconstruction does not restart the database or establish disk/crash durability.",
                "Concurrency claims apply to one API/service process; the process lock is not a distributed transaction."]}
    try:
        assert store.health()
        report["environment"]["redis_version"] = store.client.connection.info("server")["redis_version"]
        cases = ["nominal", "blocked-corridor", "scout-outage", "engineer-outage", "carrier-outage", "cargo-outage"]
        schedule = cases * args.repeats
        random.Random(20261018).shuffle(schedule)
        trials = []
        for index, case in enumerate(schedule):
            start = time.perf_counter()
            run = service.create()
            if case == "blocked-corridor":
                service.corridor(run, "hub", "power", True)
                assert service.route(run, "hub", "power") == ["hub", "airlock", "power"]
            if case.endswith("-outage") and case != "cargo-outage":
                service.disable(run, {"scout-outage": "pip", "engineer-outage": "bolt", "carrier-outage": "moss"}[case])
            complete, steps = finish(service, run, cargo_outage=case == "cargo-outage")
            elapsed = (time.perf_counter() - start) * 1000
            assert complete, case
            state = service.snapshot(run)
            trials.append({"scenario": case, "completed": complete, "steps": steps, "elapsed_ms": elapsed, **state["metrics"]})
            if (index + 1) % 10 == 0:
                print(f"Recovery trials: {index + 1}/{len(schedule)}", flush=True)
        report["recovery_trials"] = trials
        report["recovery_summary"] = [{"scenario": case, "completed": sum(r["completed"] for r in trials if r["scenario"] == case),
            "trials": args.repeats, "steps": sorted(set(r["steps"] for r in trials if r["scenario"] == case)),
            **distribution([r["elapsed_ms"] for r in trials if r["scenario"] == case])} for case in cases]
        print("Checking memory ablation, client reconstruction and contention", flush=True)
        report["memory_checks"] = memory_checks(service, args.repeats)
        report["claim_contention"] = contention_checks(service, args.repeats * 2)
        report["graph_queries"] = query_benchmarks(service, args.query_samples)
        print("Measuring real HTTP, SSE and MCP transports", flush=True)
        report["infrastructure"] = http_bench(service, args.http_samples, args.workers)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
        raise
    finally:
        report["total_seconds"] = round(time.perf_counter() - started, 3)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        # Only this randomly generated benchmark graph is disposable.
        store.graph.delete()
        print(f"Report: {destination}; status={report['status']}", flush=True)


if __name__ == "__main__":
    main()
