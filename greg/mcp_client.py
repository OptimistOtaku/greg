"""Actual stdio MCP transport for model-selected tools, through the API writer."""
from __future__ import annotations

import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .database import ROOT


async def call_crew_tool(run: str, agent: str, name: str, arguments: dict) -> dict:
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "greg.mcp_server"], cwd=str(ROOT),
        # MCP's default child environment omits application-specific variables.
        # Forward the endpoint explicitly, without forwarding provider secrets.
        env={"GREG_API_URL": os.getenv("GREG_API_URL", "http://127.0.0.1:8000")},
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, {**arguments, "run": run, "agent": agent})
            if result.is_error:
                raise RuntimeError("MCP crew tool failed; inspect the local API and MCP server")
            structured = getattr(result, "structured_content", None)
            if isinstance(structured, dict):
                return structured.get("result", structured)
            for block in result.content:
                if block.type == "text":
                    value = json.loads(block.text)
                    if isinstance(value, dict):
                        return value
            raise RuntimeError("MCP returned no structured crew-tool result")
