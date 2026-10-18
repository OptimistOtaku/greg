"""The same bounded tool dispatcher serves the Gemini loop and MCP surface."""
from __future__ import annotations

from typing import Any

from .queries import QUERIES
from .service import ActionRejected, CrewService

TOOL_DECLARATIONS = [
    {"name": "inspect_context", "description": "Read your body, capabilities, room, shared observations and eligible graph-derived tasks.", "parameters": {"type": "object", "properties": {}}},
    {"name": "find_route", "description": "Return the shortest open corridor route from your current room to a destination.", "parameters": {"type": "object", "properties": {"destination": {"type": "string"}}, "required": ["destination"]}},
    {"name": "claim_task", "description": "Reserve an eligible task exclusively. Capability and dependency checks run in FalkorDB.", "parameters": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "execute_action", "description": "Perform one physical action. move requires an adjacent destination; other actions need an owned task. Available actions: move, inspect, diagnose, pick_up, drop, repair, verify. Cargo delivery requires pick_up then drop at power. Supply pickup location is returned in world Item.room.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["move", "inspect", "diagnose", "pick_up", "drop", "repair", "verify"]}, "task_id": {"type": "string"}, "target": {"type": "string"}, "reason": {"type": "string"}}, "required": ["action", "reason"]}},
    {"name": "inhabit_body", "description": "Transfer into an available standby body after your current body goes offline. Agent knowledge persists; physical location and capabilities change.", "parameters": {"type": "object", "properties": {"body_id": {"type": "string"}}, "required": ["body_id"]}},
    {"name": "read_graph_query", "description": "Inspect the exact Cypher behind a graph tool.", "parameters": {"type": "object", "properties": {"name": {"type": "string", "enum": list(QUERIES)}}, "required": ["name"]}},
]


def dispatch(service: CrewService, run: str, agent: str, name: str, arguments: dict[str, Any]) -> dict:
    try:
        if name == "inspect_context":
            return service.context(run, agent)
        if name == "find_route":
            body = service.body(run, agent)
            if not body:
                raise ActionRejected("No body is bound")
            return {"route": service.route(run, service.location(run, body["id"]), arguments["destination"]), "query": "route"}
        if name == "claim_task":
            return service.claim(run, agent, arguments["task_id"])
        if name == "execute_action":
            return service.act(run, agent, arguments["action"], arguments.get("task_id", ""), arguments.get("target", ""), arguments.get("reason", ""))
        if name == "inhabit_body":
            return service.switch_body(run, agent, arguments["body_id"])
        if name == "read_graph_query":
            return {"cypher": QUERIES[arguments["name"]]}
        raise ActionRejected("Unknown tool")
    except (ActionRejected, KeyError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}
