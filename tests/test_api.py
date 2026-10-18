"""HTTP contract checks; separate ephemeral graph from product missions."""
import uuid

from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from greg.database import GraphStore
from greg.main import app, runtime
from greg.service import CrewService


def test_first_launch_and_missing_key(monkeypatch):
    old_service = runtime.service
    store = GraphStore("greg_api_test_" + uuid.uuid4().hex[:8])
    runtime.service = CrewService(store)
    try:
        with TestClient(app) as client:
            response = client.get("/api/runs/latest")
            assert response.status_code == 200
            assert response.json() == {"run": None}
            created = client.post("/api/runs", json={"mode": "simulation"})
            assert created.status_code == 200
            state = created.json()
            assert state["run"]["mode"] == "simulation"
            assert state["progress"] == {"done": 0, "total": 7}
            assert next(n for n in state["nodes"] if n["id"] == "samples")["status"] == "at_risk"
            assert not any(n["kind"] == "Fault" for n in state["nodes"])
            rejected = client.post(f"/api/runs/{state['run']['id']}/tools", json={
                "agent": "agent-carrier", "name": "claim_task", "arguments": {"task_id": "repair"},
            })
            # Tool failures are structured results for the agent, not HTTP errors.
            assert rejected.status_code == 200
            assert rejected.json()["ok"] is False
            assert "capability" in rejected.json()["error"]
            assert runtime.service.require(state["run"]["id"], "repair")["status"] == "pending"
            monkeypatch.delenv("GEMINI_API_KEY", raising=False)
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
            assert client.post("/api/runs", json={"mode": "gemini"}).status_code == 400
    finally:
        store.graph.delete()
        runtime.service = old_service
        runtime.active_run = None
        runtime.auto = False


def test_graph_outage_is_not_presented_as_live_data(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ConnectionError("test-only disconnected database")
    monkeypatch.setattr(runtime.service.store, "read", unavailable)
    with TestClient(app) as client:
        response = client.get("/api/runs/latest")
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"]


def test_provider_outage_is_sanitized_and_preserves_mode(monkeypatch):
    from google.genai.errors import ServerError
    from greg.controller import SimulationController
    previous = runtime.service, runtime.sim, runtime.gemini
    store = GraphStore("greg_provider_test_" + uuid.uuid4().hex[:8])
    runtime.service = CrewService(store)
    runtime.sim = SimulationController(runtime.service)
    try:
        run = runtime.service.create("gemini")
        def unavailable(run):
            raise ServerError(503, {"error": {"message": "provider-test-secret-must-not-leak"}})
        monkeypatch.setattr(runtime.gemini, "step", unavailable)
        with TestClient(app) as client:
            response = client.post(f"/api/runs/{run}/step")
            assert response.status_code == 503
            assert response.json()["detail"]["provider_status"] == 503
            assert "provider-test-secret" not in response.text
            state = client.get(f"/api/runs/{run}").json()
            assert state["run"]["mode"] == "gemini"
            assert state["progress"]["done"] == 0
    finally:
        store.graph.delete()
        runtime.service, runtime.sim, runtime.gemini = previous
        runtime.active_run = None
        runtime.auto = False
        runtime.error = ""
