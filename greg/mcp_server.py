"""MCP 2.x stdio adapter. All mutations pass through the single API writer."""
from __future__ import annotations

import os

import httpx
from mcp.server.mcpserver import MCPServer

server = MCPServer("GREG crew tools", instructions="Coordinate synthetic robot crews through FalkorDB. Run the local GREG API first. Tools validate embodiment, location and exclusive task ownership.")
BASE = os.getenv("GREG_API_URL", "http://127.0.0.1:8000")


async def call(run: str, agent: str, name: str, arguments: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{BASE}/api/runs/{run}/tools", json={"agent": agent, "name": name, "arguments": arguments})
        response.raise_for_status()
        return response.json()


@server.tool()
async def inspect_context(run: str, agent: str) -> dict:
    """Read body capabilities, shared evidence, graph-derived eligible tasks and world state."""
    return await call(run, agent, "inspect_context", {})


@server.tool()
async def find_route(run: str, agent: str, destination: str) -> dict:
    """Find an open corridor route using FalkorDB's current connectivity graph."""
    return await call(run, agent, "find_route", {"destination": destination})


@server.tool()
async def claim_task(run: str, agent: str, task_id: str) -> dict:
    """Reserve an eligible task after checking capabilities and completed prerequisites."""
    return await call(run, agent, "claim_task", {"task_id": task_id})


@server.tool()
async def execute_action(run: str, agent: str, action: str, reason: str, task_id: str = "", target: str = "") -> dict:
    """Execute one validated body action; every successful action writes a graph receipt."""
    return await call(run, agent, "execute_action", {"action": action, "task_id": task_id, "target": target, "reason": reason})


@server.tool()
async def inhabit_body(run: str, agent: str, body_id: str) -> dict:
    """Transfer an offline agent to a capable standby body without losing shared mission evidence."""
    return await call(run, agent, "inhabit_body", {"body_id": body_id})


@server.tool()
async def read_graph_query(run: str, agent: str, name: str) -> dict:
    """Read the parameterized Cypher source behind an actual crew tool."""
    return await call(run, agent, "read_graph_query", {"name": name})


if __name__ == "__main__":
    server.run()
