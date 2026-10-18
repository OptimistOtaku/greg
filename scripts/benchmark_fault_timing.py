"""Sweep body-failure timing across the authored mission, using real FalkorDB."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.benchmark import finish
from greg.controller import SimulationController
from greg.database import GraphStore, ROOT
from greg.service import CrewService


def main():
    store = GraphStore("greg_timing_bench_" + uuid.uuid4().hex[:12])
    service = CrewService(store)
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "18 predetermined body/timing combinations within one authored deterministic mission; not unseen task generalization",
              "database": "real FalkorDB", "results": []}
    try:
        for body in ["pip", "bolt", "moss"]:
            for inject_after in [0, 4, 8, 12, 16, 20]:
                start = time.perf_counter()
                run = service.create()
                controller = SimulationController(service)
                for _ in range(inject_after):
                    assert not controller.step(run).get("waiting")
                assert service.require(run, run)["status"] != "complete"
                before = service.snapshot(run)
                location = service.location(run, body)
                service.disable(run, body)
                complete, remaining = finish(service, run, controller)
                after = service.snapshot(run)
                row = {"body": body, "injected_after_controller_steps": inject_after,
                       "failure_room": location, "observations_at_failure": before["metrics"]["observations"],
                       "tasks_done_at_failure": before["progress"]["done"], "completed": complete,
                       "remaining_steps": remaining, "handoffs": after["metrics"]["handoffs"],
                       "elapsed_ms": round((time.perf_counter() - start) * 1000, 3)}
                report["results"].append(row)
                print(f"{body} after {inject_after} steps: completed={complete}", flush=True)
                assert complete
                assert after["metrics"]["handoffs"] == 1
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
        raise
    finally:
        destination = ROOT / "artifacts" / "fault-timing-results.json"
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        store.graph.delete()
        print(f"Report: {destination}; status={report['status']}", flush=True)


if __name__ == "__main__":
    main()
