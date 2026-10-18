"""Real Gemini demo trials through HTTP -> model -> MCP -> HTTP -> FalkorDB.

Calls the configured provider (billable). Missions are retained for demo replay.
No deterministic fallback or direct task completion is used.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", nargs="+", default=["nominal", "blocked-corridor", "mid-mission-body-outage"],
                        choices=["nominal", "blocked-corridor", "mid-mission-body-outage"])
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--resume", action="store_true", help="Continue unfinished retained missions from the report")
    args = parser.parse_args()
    destination = ROOT / "artifacts" / "gemini-evaluation.json"
    destination.parent.mkdir(exist_ok=True)
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "controller": "live Gemini, no simulation fallback",
              "configuration": vars(args), "results": [], "scope": "Three authored demo trials; not a statistical model benchmark"}
    if args.resume and destination.exists():
        report = json.loads(destination.read_text(encoding="utf-8"))
        report["resumed_at_utc"] = datetime.now(timezone.utc).isoformat()
    def save():
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with httpx.Client(base_url=args.base_url, timeout=120, trust_env=False) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        assert health.json()["database"] == "connected" and health.json()["model_available"]
        current_model = health.json()["model"]
        if report.get("model") and report["model"] != current_model:
            report.setdefault("model_changes", []).append({"from": report["model"], "to": current_model,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(), "reason": "Explicit operator configuration change; no automatic fallback"})
        report["model"] = current_model
        for scenario in args.scenarios:
            started = time.perf_counter()
            row = next((r for r in report["results"] if r["scenario"] == scenario), None)
            if row and row["completed"]:
                continue
            if row:
                run = row["run_id"]
                if "failure" in row:
                    row.setdefault("interruptions", []).append(row.pop("failure"))
            else:
                created = client.post("/api/runs", json={"mode": "gemini"})
                created.raise_for_status()
                run = created.json()["run"]["id"]
                row = {"scenario": scenario, "run_id": run, "turns": [], "completed": False}
                report["results"].append(row)
                if scenario == "blocked-corridor":
                    client.post(f"/api/runs/{run}/corridor", json={"start": "hub", "end": "power", "blocked": True}).raise_for_status()
            row["demo_url"] = args.base_url + "/?run=" + run
            previous_seconds = row.get("seconds", 0)
            injected = "fault_after_turn" in row
            initial = client.get(f"/api/runs/{run}")
            initial.raise_for_status()
            initial_turn = initial.json()["run"].get("model_turns", 0)
            for turn in range(initial_turn, args.max_turns):
                start = time.perf_counter()
                try:
                    for request_attempt in range(3):
                        response = client.post(f"/api/runs/{run}/step")
                        detail = response.json().get("detail", {}) if response.status_code == 503 else {}
                        retryable = isinstance(detail, dict) and detail.get("type") == "provider_error"
                        if retryable and request_attempt < 2:
                            row.setdefault("interruptions", []).append({"type": "provider_error", "provider_status": detail.get("provider_status"), "after_recorded_turns": len(row["turns"])})
                            save()
                            time.sleep(2)
                            continue
                        break
                    response.raise_for_status()
                except Exception as exc:
                    # Never persist raw provider errors/headers or credentials.
                    row["failure"] = {"type": type(exc).__name__, "http_status": getattr(locals().get("response"), "status_code", None)}
                    break
                result = response.json()
                row["turns"].append({"turn": turn + 1, "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
                    "agent": result.get("agent"), "model": result.get("model"), "tool": result.get("tool"), "ok": result.get("ok"),
                    "error": result.get("result", {}).get("error")})
                snapshot = client.get(f"/api/runs/{run}").json()
                if scenario == "mid-mission-body-outage" and not injected and snapshot["metrics"]["observations"] >= 1 and snapshot["run"]["status"] != "complete":
                    client.post(f"/api/runs/{run}/bodies/bolt/disable").raise_for_status()
                    injected = True
                    row["fault_after_turn"] = turn + 1
                print(f"{scenario} {turn + 1}: {result.get('agent')} {result.get('tool', 'text')} ok={result.get('ok')} tasks={snapshot['progress']['done']}/7", flush=True)
                save()
                if snapshot["run"]["status"] == "complete":
                    row["completed"] = True
                    break
            final = client.get(f"/api/runs/{run}")
            final.raise_for_status()
            state = final.json()
            row.update({"seconds": round(previous_seconds + time.perf_counter() - started, 3), "progress": state["progress"],
                        "metrics": state["metrics"], "model_turns": state["run"].get("model_turns", 0),
                        "verification_edges": sum(e["type"] == "VERIFIED_BY" for e in state["edges"]),
                        "reported_tokens": sum(e.get("data", {}).get("tokens", 0) for e in state["events"]),
                        "fault_injected": injected if scenario == "mid-mission-body-outage" else scenario == "blocked-corridor"})
            models = {}
            for event in state["events"]:
                model = event.get("data", {}).get("model")
                if model:
                    models[model] = models.get(model, 0) + 1
            row["model_tool_receipts"] = models
            if row["completed"]:
                assert row["progress"] == {"done": 7, "total": 7} and row["verification_edges"] == 2
                assert scenario != "mid-mission-body-outage" or injected
            (ROOT / "artifacts" / f"gemini-{scenario}-replay.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            save()
            if "failure" in row:
                break
    report["status"] = "passed" if len(report["results"]) == len(args.scenarios) and all(r["completed"] for r in report["results"]) else "incomplete"
    save()
    print(f"Live evaluation: {report['status']}. Report: {destination}")
    if report["status"] != "passed":
        sys.exit(1)


if __name__ == "__main__":
    main()
