"""Verify actual MCP stdio negotiation and a read-only graph tool via the API."""
import asyncio
import json
import sys
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("http://127.0.0.1:8000/api/runs/latest")
        response.raise_for_status()
        latest = response.json()
    if not latest.get("run"):
        raise RuntimeError("Open the app once to create a mission before checking MCP")
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "greg.mcp_server"], cwd=str(root))
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("inspect_context", {"run": latest["run"]["id"], "agent": "agent-scout"})
            assert not result.is_error, result
            print(json.dumps({"server": initialized.server_info.name, "tools": [t.name for t in tools.tools], "context_tool": "ok"}))


if __name__ == "__main__":
    asyncio.run(main())
