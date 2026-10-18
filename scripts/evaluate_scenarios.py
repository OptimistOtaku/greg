"""Reproducible simulation stress report; not a comparative research benchmark."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from greg.controller import SimulationController
from greg.database import GraphStore
from greg.service import CrewService


def main():
    store = GraphStore("greg_eval_" + uuid.uuid4().hex[:10])
    service = CrewService(store)
    cases = ["nominal", "blocked-corridor", "scout-outage", "engineer-outage", "carrier-outage", "cargo-outage"]
    results = []
    try:
        for case in cases:
            started = time.perf_counter()
            run = service.create()
            controller = SimulationController(service)
            if case == "blocked-corridor":
                service.corridor(run, "hub", "power", True)
            if case in {"scout-outage", "engineer-outage", "carrier-outage"}:
                service.disable(run, {"scout-outage": "pip", "engineer-outage": "bolt", "carrier-outage": "moss"}[case])
            injected = False
            for step in range(90):
                result = controller.step(run)
                if result.get("waiting"):
                    break
                if case == "cargo-outage" and not injected and service.require(run, "relay")["status"] == "carried":
                    service.disable(run, "moss")
                    injected = True
                if service.require(run, run)["status"] == "complete":
                    break
            snapshot = service.snapshot(run)
            results.append({"scenario": case, "completed": snapshot["run"]["status"] == "complete", "controller_steps": step + 1, **snapshot["metrics"], "seconds": round(time.perf_counter() - started, 3)})
        report = {"controller": "deterministic simulation", "database": "real FalkorDB", "comparative_benchmark": False, "results": results}
        destination = Path(__file__).resolve().parents[1] / "artifacts" / "simulation-evaluation.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        if not all(row["completed"] for row in results):
            raise SystemExit(1)
    finally:
        store.graph.delete()


if __name__ == "__main__":
    main()
