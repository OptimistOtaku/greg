"""Adapter checks without claiming live provider validation."""
from types import SimpleNamespace

import pytest
from google.genai import types

from greg.gemini import GeminiController


class Store:
    def __init__(self):
        self.turns = 0

    def nodes(self, run, kind):
        return [{"id": "agent-scout", "role": "scout"}]

    def update(self, run, node, **props):
        self.turns = props["model_turns"]


class Service:
    def __init__(self):
        self.store = Store()
        self.receipts = []

    def require(self, run, node, kind):
        return {"model_turns": self.store.turns}

    def context(self, run, agent):
        return {"agent": agent, "body": "pip", "ready_tasks": []}

    def body(self, run, agent):
        return {"id": "pip", "status": "online"}

    def ready(self, run, agent):
        return [{"id": "scan-cooling", "status": "pending", "preferred_role": "scout"}]

    def event(self, *args, **kwargs):
        self.receipts.append((args, kwargs))


def test_missing_key_never_falls_back_to_simulation(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    service = Service()
    with pytest.raises(RuntimeError, match="requires GEMINI_API_KEY"):
        GeminiController(service).step("mission-test")
    assert service.store.turns == 0


def test_model_selected_call_uses_mcp_and_preserves_tool_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-not-a-real-key")
    called = []
    async def mcp(run, agent, name, arguments):
        called.append((run, agent, name, arguments))
        return {"route": ["hub", "power"], "query": "route"}
    monkeypatch.setattr("greg.gemini.call_crew_tool", mcp)
    response = SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="find_route", args={"destination": "power"}))]))], usage_metadata=SimpleNamespace(total_token_count=42))
    requests = []
    def generate(**kwargs):
        requests.append(kwargs["contents"])
        return response
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate), close=lambda: None)
    monkeypatch.setattr("greg.gemini.genai.Client", lambda **kwargs: client)
    service = Service()
    controller = GeminiController(service)
    result = controller.step("mission-test")
    assert called == [("mission-test", "agent-scout", "find_route", {"destination": "power"})]
    assert result["tool"] == "find_route"
    assert controller.histories[("mission-test", "agent-scout")][-1].role == "user"
    assert service.receipts[0][1]["data"]["transport"].startswith("MCP")
    assert controller.histories[("mission-test", "agent-scout")][0].role == "user"
    controller.step("mission-test")
    assert len(called) == 2
    assert len(controller.histories[("mission-test", "agent-scout")]) == 3
    assert requests[1][0].role == "user"
    assert requests[1][1].parts[0].function_call.name == "find_route"


def test_graph_ineligible_agent_does_not_spend_a_model_turn(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-not-a-real-key")
    service = Service()
    service.ready = lambda run, agent: []
    monkeypatch.setattr("greg.gemini.genai.Client", lambda **kwargs: pytest.fail("No model request should be made"))
    result = GeminiController(service).step("mission-test")
    assert result["waiting"]
    assert service.store.turns == 0


def test_model_turn_budget_stops_provider_calls(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-not-a-real-key")
    monkeypatch.setenv("GEMINI_MAX_TURNS", "1")
    service = Service()
    service.store.turns = 1
    with pytest.raises(RuntimeError, match="budget"):
        GeminiController(service).step("mission-test")
