"""Behavioral checks against a real FalkorDB, never an in-memory substitute."""
from concurrent.futures import ThreadPoolExecutor
import uuid

import pytest

from greg.controller import SimulationController
from greg.database import GraphStore
from greg.service import ActionRejected, CrewService


@pytest.fixture(scope="module")
def service():
    store = GraphStore("greg_test_" + uuid.uuid4().hex[:10])
    # Missing FalkorDB is a failed integration precondition, not a skipped success.
    assert store.health()
    instance = CrewService(store)
    yield instance
    store.graph.delete()


def complete(service, run):
    controller = SimulationController(service)
    for _ in range(90):
        result = controller.step(run)
        assert not result.get("waiting"), result
        if service.require(run, run)["status"] == "complete":
            return service.snapshot(run)
    pytest.fail("The crew did not finish within the action budget")


def test_full_recovery_requires_shared_evidence_and_delivery(service):
    run = service.create()
    state = complete(service, run)
    assert state["progress"] == {"done": 7, "total": 7}
    assert state["metrics"]["observations"] == 2
    assert service.require(run, "relay")["status"] == "installed"
    assert service.require(run, "bus")["status"] == "operational"
    assert {"shared_cause", "impact"}.issubset({e["query"] for e in state["events"]})
    diagnosis = next(e for e in state["events"] if e["query"] == "shared_cause")
    assert {"obs-antenna", "obs-coolant", "bus"}.issubset(diagnosis["evidence"])
    assert len([e for e in state["edges"] if e["type"] == "VERIFIED_BY"]) == 2
    assert not any(n["kind"] == "Fault" for n in state["nodes"])


def test_capability_prerequisite_and_location_guards(service):
    run = service.create()
    with pytest.raises(ActionRejected):
        service.claim(run, "agent-carrier", "repair")
    with pytest.raises(ActionRejected):
        service.claim(run, "agent-engineer", "repair")
    service.claim(run, "agent-scout", "scan-cooling")
    before = service.require(run, "pip")["battery"]
    with pytest.raises(ActionRejected):
        service.act(run, "agent-scout", "inspect", "scan-cooling")
    assert service.require(run, "pip")["battery"] == before
    assert service.require(run, "scan-cooling")["status"] == "active"


def test_graph_edge_changes_routing_and_rejects_closed_moves(service):
    run = service.create()
    assert service.route(run, "hub", "power") == ["hub", "power"]
    service.corridor(run, "hub", "power", True)
    assert service.route(run, "hub", "power") == ["hub", "airlock", "power"]
    with pytest.raises(ActionRejected):
        service.act(run, "agent-scout", "move", target="power")
    assert service.location(run, "pip") == "hub"
    assert complete(service, run)["run"]["status"] == "complete"


@pytest.mark.parametrize("body,agent", [("pip", "agent-scout"), ("bolt", "agent-engineer"), ("moss", "agent-carrier")])
def test_agent_inherits_reserve_body_and_finishes(service, body, agent):
    run = service.create()
    service.disable(run, body)
    state = complete(service, run)
    assert state["metrics"]["handoffs"] == 1
    assert service.body(run, agent)["id"] == "echo"
    assert service.location(run, body) in {"hub", "stores"}


def test_down_carrier_drops_cargo_for_replacement(service):
    run = service.create()
    controller = SimulationController(service)
    for _ in range(50):
        controller.step(run)
        if service.require(run, "relay")["status"] == "carried":
            break
    assert service.require(run, "relay")["status"] == "carried"
    location = service.location(run, "moss")
    service.disable(run, "moss")
    assert service.location(run, "relay") == location
    assert complete(service, run)["run"]["status"] == "complete"


def test_exclusive_claim_under_concurrent_requests(service):
    run = service.create()
    def claim(agent):
        try:
            service.claim(run, agent, "scan-cooling")
            return True
        except ActionRejected:
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ["agent-scout", "agent-engineer"]))
    assert results.count(True) == 1
    assert service.require(run, "scan-cooling")["owner"] in {"agent-scout", "agent-engineer"}


def test_incomplete_evidence_cannot_produce_diagnosis(service):
    run = service.create()
    # No fabricated observation can enter through the crew action API.
    assert service.store.read(__import__("greg.queries", fromlist=["SHARED_CAUSE"]).SHARED_CAUSE, run=run) == []
    with pytest.raises(ActionRejected):
        service.claim(run, "agent-scout", "correlate")
