from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from redis.exceptions import RedisError, ResponseError
from google.genai.errors import APIError

from .controller import SimulationController
from .database import ROOT, GraphStore
from .gemini import GeminiController
from .queries import QUERIES
from .service import ActionRejected, CrewService
from .tools import dispatch


class Runtime:
    def __init__(self):
        self.service = CrewService(GraphStore())
        self.sim = SimulationController(self.service)
        self.gemini = GeminiController(self.service)
        self.active_run: str | None = None
        self.auto = False
        self.error = ""
        self.step_lock = asyncio.Lock()
        self.interval = 1.6

    async def step(self, run: str) -> dict:
        if self.step_lock.locked():
            raise HTTPException(409, "A crew turn is already running")
        async with self.step_lock:
            meta = await asyncio.to_thread(self.service.require, run, run, "Run")
            if meta["status"] == "complete":
                self.auto = False
                return {"ok": True, "complete": True}
            controller = self.gemini if meta["mode"] == "gemini" else self.sim
            try:
                result = await asyncio.to_thread(controller.step, run)
            except APIError as exc:
                self.auto = False
                code = int(exc.code or 502)
                self.error = f"Gemini request failed ({code}). Graph state is preserved; retry or check provider availability."
                raise HTTPException(503 if code == 429 or code >= 500 else 502,
                                    detail={"type": "provider_error", "provider_status": code,
                                            "message": self.error}) from None
            if result.get("waiting"):
                self.auto = False
                self.error = result["detail"]
            return result


runtime = Runtime()


async def heartbeat():
    while True:
        await asyncio.sleep(runtime.interval)
        if runtime.auto and runtime.active_run and not runtime.step_lock.locked():
            try:
                await runtime.step(runtime.active_run)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                runtime.auto = False
                # Provider messages can echo credentials/URLs. Keep secrets out of UI.
                runtime.error = "Crew paused: " + (str(exc)[:400] if isinstance(exc, ActionRejected) else f"{type(exc).__name__}. Check the local server log/configuration and database connection.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(heartbeat())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="GREG Crew API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(ActionRejected)
async def rejected(request: Request, exc: ActionRejected):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RedisError)
async def db_unavailable(request: Request, exc: RedisError):
    return JSONResponse(status_code=503, content={"detail": "FalkorDB is unavailable. Start Docker and run docker compose up -d --wait. Crew state is not substituted with fixture data."})


class CreateRun(BaseModel):
    mode: str = "simulation"


class AutoRequest(BaseModel):
    enabled: bool
    interval: float = Field(default=1.6, ge=0.4, le=10)


class CorridorRequest(BaseModel):
    start: str
    end: str
    blocked: bool


class ToolRequest(BaseModel):
    agent: str
    name: str
    arguments: dict = Field(default_factory=dict)


@app.get("/api/health")
def health():
    load_dotenv(ROOT / ".env")
    try:
        database = "connected" if runtime.service.store.health() else "unavailable"
    except RedisError:
        database = "unavailable"
    return {"database": database, "graph": runtime.service.store.name, "model_available": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")), "model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")}


@app.get("/api/queries")
def queries():
    return QUERIES


@app.post("/api/runs")
async def create_run(payload: CreateRun):
    if runtime.step_lock.locked():
        raise HTTPException(409, "Pause and wait for the current crew turn before starting a new mission")
    if payload.mode == "gemini" and not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        raise HTTPException(400, "Set GEMINI_API_KEY locally before choosing Gemini mode")
    runtime.auto = False
    run = await asyncio.to_thread(runtime.service.create, payload.mode)
    runtime.active_run = run
    runtime.error = ""
    return await get_run(run)


@app.get("/api/runs/latest")
async def latest():
    try:
        rows = await asyncio.to_thread(runtime.service.store.read, "MATCH (r:Run) RETURN r.id ORDER BY r.created_at DESC LIMIT 1")
    except ResponseError as exc:
        if "empty key" in str(exc).lower() or "does not exist" in str(exc).lower():
            return {"run": None}
        raise
    if not rows:
        return {"run": None}
    runtime.active_run = rows[0][0]
    return await get_run(rows[0][0])


@app.get("/api/runs/{run}")
async def get_run(run: str):
    snapshot = await asyncio.to_thread(runtime.service.snapshot, run)
    return dict(snapshot, auto=runtime.auto and runtime.active_run == run, error=runtime.error)


@app.post("/api/runs/{run}/step")
async def step(run: str):
    runtime.error = ""
    return await runtime.step(run)


@app.post("/api/runs/{run}/auto")
async def auto(run: str, payload: AutoRequest):
    await asyncio.to_thread(runtime.service.require, run, run, "Run")
    if runtime.step_lock.locked() and run != runtime.active_run:
        raise HTTPException(409, "Another mission turn is in progress")
    runtime.active_run = run
    runtime.auto = payload.enabled
    runtime.interval = payload.interval
    runtime.error = ""
    return {"auto": runtime.auto}


@app.post("/api/runs/{run}/bodies/{body}/disable")
async def disable(run: str, body: str):
    return await asyncio.to_thread(runtime.service.disable, run, body)


@app.post("/api/runs/{run}/corridor")
async def corridor(run: str, payload: CorridorRequest):
    return await asyncio.to_thread(runtime.service.corridor, run, payload.start, payload.end, payload.blocked)


@app.get("/api/runs/{run}/context/{agent}")
async def context(run: str, agent: str):
    return await asyncio.to_thread(runtime.service.context, run, agent)


@app.post("/api/runs/{run}/tools")
async def tool(run: str, payload: ToolRequest):
    return await asyncio.to_thread(dispatch, runtime.service, run, payload.agent, payload.name, payload.arguments)


@app.get("/api/runs/{run}/events")
async def events(run: str, request: Request):
    async def stream():
        previous = ""
        while not await request.is_disconnected():
            try:
                state = await get_run(run)
                serialized = json.dumps(state)
                if serialized != previous:
                    yield "data: " + serialized + "\n\n"
                    previous = serialized
                else:
                    yield ": keep-alive\n\n"
            except (RedisError, ActionRejected) as exc:
                yield "event: error\ndata: " + json.dumps({"error": "Graph connection lost. Live state is unavailable."}) + "\n\n"
            await asyncio.sleep(0.8)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


frontend = ROOT / "web" / "dist"
if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="mission-control")
