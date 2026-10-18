"""Regression for the nondefault endpoint bug found by the real MCP benchmark."""
import asyncio
from contextlib import asynccontextmanager

import pytest

from greg import mcp_client


def test_custom_api_endpoint_reaches_child_without_provider_secret(monkeypatch):
    endpoint = "http://127.0.0.1:18081"
    monkeypatch.setenv("GREG_API_URL", endpoint)
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-not-a-real-key")
    captured = []

    class ChildIntercepted(Exception):
        pass

    @asynccontextmanager
    async def child(parameters):
        captured.append(parameters)
        raise ChildIntercepted
        yield  # Makes this a context manager without starting a child process.

    monkeypatch.setattr(mcp_client, "stdio_client", child)
    with pytest.raises(ChildIntercepted):
        asyncio.run(mcp_client.call_crew_tool("mission-test", "agent-scout", "inspect_context", {}))
    assert captured[0].env["GREG_API_URL"] == endpoint
    assert "GEMINI_API_KEY" not in captured[0].env
