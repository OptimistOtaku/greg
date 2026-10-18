"""Graph-owned world, validated body actions and inspectable action receipts.

One API process serializes world transitions. MCP calls this process over HTTP.
LLMs never write Cypher or mutate the simulator directly.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from .database import GraphStore
from .queries import CAPABLE_BODIES, CLAIM, IMPACT, READY_TASKS, ROUTE, SHARED_CAUSE
from .scenario import seed


class ActionRejected(ValueError):
    pass


class CrewService:
    def __init__(self, store: GraphStore):
        self.store = store
        self.lock = threading.RLock()

    def require(self, run: str, node: str, kind: str | None = None) -> dict[str, Any]:
        value = self.store.get(run, node)
        if not value or (kind and value["kind"] != kind):
            raise ActionRejected(f"Unknown {kind or 'entity'}: {node}")
        return value

    def create(self, mode: str = "simulation") -> str:
        if mode not in {"simulation", "gemini"}:
            raise ActionRejected("Choose simulation or gemini")
        with self.lock:
            run = "mission-" + uuid.uuid4().hex[:12]
            seed(self.store, run, mode)
            self.event(run, "mission", "MISSION CONTROL", "Two systems offline. One crew.", "Cooling and communications are degraded. Investigate, coordinate a repair, and verify recovery. All station data is synthetic.")
            return run

    def event(self, run: str, category: str, actor: str, title: str, detail: str, evidence: list[str] | None = None, query: str = "", data: dict | None = None) -> dict:
        meta = self.require(run, run, "Run")
        tick = int(meta["tick"]) + 1
        self.store.update(run, run, tick=tick)
        event_id = f"event-{tick:05d}"
        props = dict(name=title, category=category, actor=actor, detail=detail, tick=tick, timestamp=datetime.now(timezone.utc).isoformat(), query=query, data=json.dumps(data or {}))
        self.store.add(run, event_id, "Event", **props)
        for node in evidence or []:
            self.store.link(run, event_id, node, "SUPPORTED_BY")
        return {"id": event_id, **props, "data": data or {}}

    def location(self, run: str, entity: str) -> str | None:
        rows = self.store.read("MATCH (:Entity {run_id: $run, id: $id})-[:LOCATED_IN]->(r:Room) RETURN r.id", run=run, id=entity)
        return rows[0][0] if rows else None

    def body(self, run: str, agent: str) -> dict | None:
        self.require(run, agent, "Agent")
        rows = self.store.read("MATCH (:Agent {run_id: $run, id: $id})-[:EMBODIES]->(b:Body) RETURN properties(b)", run=run, id=agent)
        return rows[0][0] if rows else None

    def capabilities(self, run: str, body: str) -> list[str]:
        return [row[0] for row in self.store.read("MATCH (:Body {run_id: $run, id: $id})-[:HAS_CAPABILITY]->(c:Capability) RETURN c.name", run=run, id=body)]

    def route(self, run: str, start: str, end: str) -> list[str]:
        self.require(run, start, "Room")
        self.require(run, end, "Room")
        if start == end:
            return [start]
        rows = self.store.read(ROUTE, run=run, start=start, end=end)
        return rows[0][0] if rows else []

    def ready(self, run: str, agent: str) -> list[dict]:
        return [row[0] for row in self.store.read(READY_TASKS, run=run, agent=agent)]

    def snapshot(self, run: str, include_events: bool = True) -> dict:
        with self.lock:
            self.require(run, run, "Run")
            nodes = self.store.nodes(run)
            visible = [node for node in nodes if node["kind"] not in {"Fault", "Event"}]
            ids = {n["id"] for n in visible}
            all_edges = self.store.edges(run)
            edges = [edge for edge in all_edges if edge["source"] in ids and edge["target"] in ids]
            for node in visible:
                if node["kind"] in {"Body", "System", "Item"}:
                    node["room"] = next((e["target"] for e in edges if e["source"] == node["id"] and e["type"] == "LOCATED_IN"), None)
                if node["kind"] == "Body":
                    node["capabilities"] = [e["target"].removeprefix("cap-") for e in edges if e["source"] == node["id"] and e["type"] == "HAS_CAPABILITY"]
                    node["agent"] = next((e["source"] for e in edges if e["target"] == node["id"] and e["type"] == "EMBODIES"), None)
                    node["carrying"] = [e["target"] for e in edges if e["source"] == node["id"] and e["type"] == "CARRIES"]
            meta = next(n for n in visible if n["kind"] == "Run")
            tasks = [n for n in visible if n["kind"] == "Task"]
            return {
                "run": meta, "nodes": visible, "edges": edges,
                "events": sorted([dict(n, data=json.loads(n.get("data", "{}")), evidence=[e["target"] for e in all_edges if e["source"] == n["id"] and e["type"] == "SUPPORTED_BY"]) for n in nodes if n["kind"] == "Event"], key=lambda n: n["tick"])[-180:] if include_events else [],
                "progress": {"done": sum(t["status"] == "done" for t in tasks), "total": len(tasks)},
                "metrics": {"actions": sum(n["kind"] == "Event" and n.get("category") == "action" for n in nodes), "observations": sum(n["kind"] == "Observation" for n in nodes), "handoffs": sum(n["kind"] == "Event" and n.get("category") == "handoff" for n in nodes)},
            }

    def context(self, run: str, agent: str) -> dict:
        state = self.snapshot(run, include_events=False)
        body = self.body(run, agent)
        room = self.location(run, body["id"]) if body else None
        return {
            "agent": self.require(run, agent, "Agent"), "body": body,
            "room": room, "capabilities": self.capabilities(run, body["id"]) if body else [],
            "ready_tasks": self.ready(run, agent) if body and body["status"] == "online" else [],
            "world": state,
        }

    def claim(self, run: str, agent: str, task_id: str) -> dict:
        with self.lock:
            task = self.require(run, task_id, "Task")
            body = self.body(run, agent)
            if not body or body["status"] != "online":
                raise ActionRejected("An online body is required")
            if task.get("owner") == agent and task["status"] == "active":
                return {"ok": True, "already_claimed": True, "task": task_id}
            occupied = self.store.read("MATCH (t:Task {run_id: $run, status: 'active', owner: $agent}) RETURN t.id", run=run, agent=agent)
            if occupied:
                raise ActionRejected("Finish your currently reserved task before claiming another")
            if task_id not in {t["id"] for t in self.ready(run, agent)}:
                raise ActionRejected("Task is reserved, prerequisites are incomplete, or this body lacks a required capability")
            if not self.store.query(CLAIM, run=run, task=task_id, agent=agent):
                raise ActionRejected("Another agent already claimed this task")
            self.store.link(run, task_id, agent, "ASSIGNED_TO")
            self.event(run, "coordination", agent, "Task reserved", task["name"] + ". Capability and prerequisite paths checked in FalkorDB.", [task_id, body["id"]], "ready_tasks,claim")
            return {"ok": True, "task": task_id}

    def switch_body(self, run: str, agent: str, body_id: str) -> dict:
        with self.lock:
            role = self.require(run, agent, "Agent")["role"]
            target = self.require(run, body_id, "Body")
            old = self.body(run, agent)
            if old and old["status"] == "online":
                raise ActionRejected("The current body is still online; disable it before transferring this agent")
            required = {"scout": ["scan", "analyze"], "engineer": ["scan", "analyze", "repair"], "carrier": ["scan", "carry"]}[role]
            available = self.store.read(CAPABLE_BODIES, run=run, required=["cap-" + cap for cap in required])
            if body_id not in {row[0] for row in available} or target["battery"] < 15:
                raise ActionRejected("This body is unavailable or lacks the capabilities needed by this agent")
            self.store.unlink(run, agent, None, "EMBODIES")
            self.store.link(run, agent, body_id, "EMBODIES")
            self.store.update(run, body_id, status="online")
            self.event(run, "handoff", agent, "Same mind. New body.", f"Agent transferred to {target['name']} at {self.location(run, body_id)}. Shared evidence is retained; location, battery and capabilities come from the new body.", [agent, body_id], "capable_bodies")
            return {"ok": True, "body": body_id}

    def disable(self, run: str, body_id: str) -> dict:
        with self.lock:
            meta = self.require(run, run, "Run")
            if meta["status"] == "complete":
                raise ActionRejected("Start a new mission to inject another fault")
            body = self.require(run, body_id, "Body")
            if body["status"] != "online":
                raise ActionRejected("This body is not online")
            room = self.location(run, body_id)
            self.store.update(run, body_id, status="offline")
            rows = self.store.read("MATCH (a:Agent {run_id: $run})-[:EMBODIES]->(:Body {id: $body, run_id: $run}) RETURN a.id", run=run, body=body_id)
            for [agent] in rows:
                for task in self.store.nodes(run, "Task"):
                    if task["status"] == "active" and task.get("owner") == agent:
                        self.store.update(run, task["id"], status="pending", owner="")
                        self.store.unlink(run, task["id"], agent, "ASSIGNED_TO")
            for [item] in self.store.read("MATCH (:Body {run_id: $run, id: $body})-[:CARRIES]->(i:Item) RETURN i.id", run=run, body=body_id):
                self.store.unlink(run, body_id, item, "CARRIES")
                self.store.link(run, item, room, "LOCATED_IN")
                self.store.update(run, item, status="available")
            self.event(run, "fault", "MISSION CONTROL", f"{body['name']} is unresponsive", "The body is offline. Its unfinished task reservations are released and carried cargo is recoverable at its last location.", [body_id])
            return {"ok": True}

    def corridor(self, run: str, start: str, end: str, blocked: bool) -> dict:
        with self.lock:
            rows = self.store.read("MATCH (a:Room {run_id: $run, id: $a})-[r:CONNECTS]->(b:Room {run_id: $run, id: $b}) RETURN r.blocked", run=run, a=start, b=end)
            if not rows:
                raise ActionRejected("No corridor joins these rooms")
            for a, b in [(start, end), (end, start)]:
                self.store.link(run, a, b, "CONNECTS", blocked=blocked)
            self.event(run, "fault" if blocked else "coordination", "MISSION CONTROL", "Corridor sealed" if blocked else "Corridor reopened", f"{start} / {end}. Movement queries now use the current corridor graph.", [start, end], "route")
            return {"ok": True}

    def _complete_task(self, run: str, task: dict, agent: str) -> None:
        self.store.update(run, task["id"], status="done", completed_by=agent)

    def _spend(self, run: str, body: dict, cost: int) -> None:
        self.store.update(run, body["id"], battery=int(body["battery"]) - cost)

    def act(self, run: str, agent: str, action: str, task_id: str = "", target: str = "", reason: str = "") -> dict:
        with self.lock:
            meta = self.require(run, run, "Run")
            if meta["status"] == "complete":
                raise ActionRejected("The mission is already complete")
            body = self.body(run, agent)
            if not body or body["status"] != "online":
                raise ActionRejected("The agent needs an online body")
            room = self.location(run, body["id"])
            caps = self.capabilities(run, body["id"])
            cost = {"move": 2, "inspect": 3, "diagnose": 2, "pick_up": 1, "drop": 1, "repair": 8, "verify": 2}.get(action)
            if cost is None:
                raise ActionRejected("Unknown action")
            if body["battery"] < cost:
                raise ActionRejected("Insufficient battery")
            evidence = [agent, body["id"]]
            data = {"action": action, "body": body["id"], "from": room, "task": task_id, "reason": reason}
            query = ""
            if action == "move":
                path = self.route(run, room, target)
                if len(path) != 2:
                    raise ActionRejected("Move one adjacent, open corridor at a time; use the route tool for a full path")
                self.store.unlink(run, body["id"], None, "LOCATED_IN")
                self.store.link(run, body["id"], target, "LOCATED_IN")
                title, detail = "Moving through the station", f"{body['name']}: {room} → {target}."
                evidence += path
                data["to"] = target
                query = "route"
            else:
                task = self.require(run, task_id, "Task")
                if task["status"] != "active" or task.get("owner") != agent:
                    raise ActionRejected("Claim this task before acting; task ownership is exclusive")
                evidence.append(task_id)
                required_rows = self.store.read("MATCH (:Task {run_id: $run, id: $id})-[:REQUIRES]->(c:Capability) RETURN c.name", run=run, id=task_id)
                if any(row[0] not in caps for row in required_rows):
                    raise ActionRejected("The body lacks this task's capability")
                if action not in {task["action"], *(["pick_up", "drop"] if task["action"] == "deliver" else [])}:
                    raise ActionRejected("This action does not match the task")
                if action not in {"pick_up", "drop"} and room != task["room"]:
                    raise ActionRejected("The body must reach the task location first")
                if action == "inspect":
                    system = self.require(run, task["target"], "System")
                    fault = self.require(run, "fault-relay", "Fault")
                    observation_id = "obs-" + system["id"]
                    signal = "power_loss" if fault["active"] else "nominal"
                    description = "Undervoltage at the subsystem input. Local hardware responds normally." if fault["active"] else "Supply voltage and local hardware are nominal."
                    self.store.add(run, observation_id, "Observation", name=system["name"] + " reading", signal=signal, detail=description, observed_by=agent, status="verified")
                    self.store.link(run, observation_id, system["id"], "ABOUT")
                    self.store.link(run, observation_id, agent, "OBSERVED_BY")
                    self._complete_task(run, task, agent)
                    title, detail = "New evidence shared with the crew", f"{system['name']}: {description}"
                    evidence += [system["id"], observation_id]
                elif action == "diagnose":
                    candidates = self.store.read(SHARED_CAUSE, run=run)
                    if not candidates:
                        raise ActionRejected("No shared cause is supported by two independent subsystem observations yet")
                    root, systems, observations = candidates[0]
                    self.store.add(run, "hypothesis-bus", "Hypothesis", name="Shared upstream power failure", status="supported", detail="Two observed power-loss symptoms share an upstream bus. This is a supported diagnosis in the bounded simulator, not universal causal proof.")
                    self.store.link(run, "hypothesis-bus", root, "ABOUT")
                    for obs in observations:
                        self.store.link(run, "hypothesis-bus", obs, "SUPPORTED_BY")
                    self.store.update(run, root, status="diagnosed")
                    self._complete_task(run, task, agent)
                    title, detail = "Two failures. One shared dependency.", f"The observed systems {', '.join(systems)} both depend on {root}. A single relay repair can address both symptoms."
                    evidence += [root, "hypothesis-bus", *observations]
                    query = "shared_cause"
                    data["systems"] = systems
                elif action == "pick_up":
                    item = self.require(run, "relay", "Item")
                    if item["status"] != "available" or self.location(run, "relay") != room:
                        raise ActionRejected("The replacement relay is not available at this body's location")
                    self.store.unlink(run, "relay", None, "LOCATED_IN")
                    self.store.link(run, body["id"], "relay", "CARRIES")
                    self.store.update(run, "relay", status="carried")
                    title, detail = "Replacement relay secured", f"{body['name']} picked up the relay at {room}."
                    evidence.append("relay")
                elif action == "drop":
                    carried = self.store.read("MATCH (:Body {run_id: $run, id: $id})-[:CARRIES]->(:Item {id: 'relay'}) RETURN 1", run=run, id=body["id"])
                    if not carried or room != task["room"]:
                        raise ActionRejected("Carry the relay to the repair site before delivering it")
                    self.store.unlink(run, body["id"], "relay", "CARRIES")
                    self.store.link(run, "relay", room, "LOCATED_IN")
                    self.store.update(run, "relay", status="available")
                    self._complete_task(run, task, agent)
                    title, detail = "Repair prerequisite satisfied", "The replacement relay is physically at the power core. The engineering task is now eligible."
                    evidence.append("relay")
                elif action == "repair":
                    item = self.require(run, "relay", "Item")
                    if item["status"] != "available" or self.location(run, "relay") != room or self.require(run, "bus", "System")["status"] != "diagnosed":
                        raise ActionRejected("Repair needs a supported diagnosis and an available relay at the power core")
                    affected = self.store.read(IMPACT, run=run, system="bus")
                    self.store.update(run, "relay", status="installed")
                    self.store.update(run, "fault-relay", active=False)
                    self.store.update(run, "bus", status="operational")
                    for system, _ in affected:
                        self.store.update(run, system, status="operational" if system != "samples" else "stable")
                    self._complete_task(run, task, agent)
                    title, detail = "Shared power restored", "Relay replaced. The dependency traversal identifies cooling, communications and the research samples downstream. Verification tasks remain required."
                    evidence += ["bus", "relay", *[row[0] for row in affected]]
                    query = "impact"
                elif action == "verify":
                    system = self.require(run, task["target"], "System")
                    if system["status"] != "operational" or self.require(run, "fault-relay", "Fault")["active"]:
                        raise ActionRejected("The system has not recovered")
                    self._complete_task(run, task, agent)
                    self.store.link(run, system["id"], agent, "VERIFIED_BY")
                    title, detail = "Recovery independently verified", f"{system['name']} is operational. Verification was performed at the subsystem after repair."
                    evidence.append(system["id"])
                else:
                    raise ActionRejected("Delivery requires pick_up or drop")
            self._spend(run, body, cost)
            event = self.event(run, "action", agent, title, detail, evidence, query, data)
            tasks = self.store.nodes(run, "Task")
            if all(t["status"] == "done" for t in tasks):
                self.store.update(run, run, status="complete")
                self.event(run, "complete", "MISSION CONTROL", "Station recovered. Mission verified.", "Cooling and communications were verified operational. The graph retains every observation, assignment and action receipt.", ["coolant", "antenna", "samples"])
            elif meta["status"] == "ready":
                self.store.update(run, run, status="running")
            return {"ok": True, "event": event}
