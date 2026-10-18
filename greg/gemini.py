"""Real model-selected function calls. Missing keys/errors never select simulation."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from google import genai
from google.genai import types

from .service import CrewService
from .tools import TOOL_DECLARATIONS
from .mcp_client import call_crew_tool
from .queries import CAPABLE_BODIES

SYSTEM = """You are one member of GREG's robot crew in a bounded synthetic orbital station.
Use the graph tools to restore cooling and communications and preserve research samples.
You act only through your current body's capabilities and location. Shared graph observations
are available to all agents; never invent observations or claim an unexecuted action.
Prefer tasks whose preferred_role matches your role, while helping unavailable teammates.
Tasks require an exclusive claim before execution. Movement is one open corridor per action.
Delivery requires reaching the Item.room, picking up the relay, moving to power, and dropping it.
Diagnose only after two observed subsystem failures support a common upstream cause.
Repair only with the delivered part, and verify subsystems afterward. If your body is offline,
inhabit a standby body with the capabilities your role requires. Retain uncertainty and report
blocked paths or unavailable bodies. Tool errors are observations, not successful actions.
Make at most one state-changing tool call per turn. Provide a short reason in execute_action.
"""


class GeminiController:
    def __init__(self, service: CrewService):
        self.service = service
        self.histories: dict[tuple[str, str], list[Any]] = {}
        self.cursor: dict[str, int] = {}

    def step(self, run: str) -> dict:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("Gemini mode requires GEMINI_API_KEY in the local .env. Choose Simulation for a deterministic graph-driven crew.")
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        turn = int(self.service.require(run, run, "Run").get("model_turns", 0))
        if turn >= int(os.getenv("GEMINI_MAX_TURNS", "60")):
            raise RuntimeError("Gemini mission turn budget reached. Pause and inspect the mission before creating a new one.")
        agents = sorted(self.service.store.nodes(run, "Agent"), key=lambda a: a["id"])
        index = self.cursor.get(run, 0) % len(agents)
        bodies = {a["id"]: self.service.body(run, a["id"]) for a in agents}
        online_roles = {a["role"] for a in agents if bodies[a["id"]] and bodies[a["id"]]["status"] == "online"}
        selected = None
        for offset in range(len(agents)):
            position = (index + offset) % len(agents)
            member = agents[position]
            body = bodies[member["id"]]
            if not body or body["status"] != "online":
                required = {"scout": ["scan", "analyze"], "engineer": ["scan", "analyze", "repair"], "carrier": ["scan", "carry"]}[member["role"]]
                eligible = bool(self.service.store.read(CAPABLE_BODIES, run=run, required=["cap-" + c for c in required]))
            else:
                eligible = any(t["status"] == "active" or t["preferred_role"] == member["role"] or t["preferred_role"] not in online_roles
                               for t in self.service.ready(run, member["id"]))
            if eligible:
                selected = member
                self.cursor[run] = position + 1
                break
        if not selected:
            return {"ok": False, "waiting": True, "detail": "No graph-eligible crew member. Check prerequisites, bodies and connectivity."}
        agent = selected["id"]
        self.service.store.update(run, run, model_turns=turn + 1)
        history = self.histories.setdefault((run, agent), [])
        context = self.service.context(run, agent)
        # Current graph context is injected each turn; history is conversational state only.
        user_content = types.Content(role="user", parts=[types.Part(text="Current graph context:\n" + json.dumps(context) + "\nChoose your next tool call. Prefer your active task, otherwise claim an eligible task matching your role. The current graph context already contains shared evidence; do not repeatedly inspect unchanged context or query source.")])
        contents = [*history, user_content]
        client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=30000,
            retry_options=types.HttpRetryOptions(attempts=3, initial_delay=1, max_delay=4,
                http_status_codes=[429, 500, 502, 503, 504]),
        ))
        try:
            response = client.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in TOOL_DECLARATIONS])],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    temperature=0.2, max_output_tokens=1800,
                ),
            )
        finally:
            client.close()
        candidate = response.candidates[0].content if response.candidates else None
        if not candidate:
            raise RuntimeError("Gemini returned no action content")
        function_parts = [p for p in candidate.parts or [] if p.function_call]
        if not function_parts:
            text = " ".join(p.text for p in candidate.parts or [] if p.text)
            self.service.event(run, "reasoning", agent, "Crew observation", text[:1200] or "No tool was selected.")
            history[:] = [user_content, candidate]
            return {"ok": True, "model": model, "agent": agent, "text": text}
        function = function_parts[0].function_call
        # Preserve only the call being serviced; parallel mutations are never silently executed.
        call_content = types.Content(role="model", parts=[function_parts[0]])
        arguments = dict(function.args or {})
        result = asyncio.run(call_crew_tool(run, agent, function.name, arguments))
        usage = response.usage_metadata
        self.service.event(run, "tool", agent, f"Gemini → MCP → {function.name}", json.dumps({"arguments": arguments, "ok": result.get("ok", True)}, ensure_ascii=False)[:1500], query=result.get("query", ""), data={"tool": function.name, "transport": "MCP stdio → local API", "arguments": arguments, "model": model, "tokens": usage.total_token_count if usage else 0, "result_summary": result.get("error", "Tool returned graph evidence or an action receipt.")})
        # Keep one complete previous turn, including its originating user message.
        # Starting a retained conversation with a model function call is invalid.
        # Durable mission memory remains the graph, not an ever-growing transcript.
        history[:] = [user_content, call_content, types.Content(role="user", parts=[types.Part.from_function_response(name=function.name, response=result)])]
        return {"ok": result.get("ok", True), "agent": agent, "model": model, "tool": function.name, "result": result}
