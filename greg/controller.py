"""A transparent deterministic policy for reproducible simulation runs."""
from __future__ import annotations

from .queries import CAPABLE_BODIES
from .service import ActionRejected, CrewService


class SimulationController:
    def __init__(self, service: CrewService):
        self.service = service
        self.cursor: dict[str, int] = {}

    def step(self, run: str) -> dict:
        s = self.service
        with s.lock:
            meta = s.require(run, run, "Run")
            if meta["status"] == "complete":
                return {"ok": True, "complete": True}
            agents = sorted(s.store.nodes(run, "Agent"), key=lambda a: a["id"])
            offset = self.cursor.get(run, 0) % len(agents)
            ordered = agents[offset:] + agents[:offset]
            for agent in ordered:
                body = s.body(run, agent["id"])
                self.cursor[run] = agents.index(agent) + 1
                if not body or body["status"] != "online":
                    required = {"scout": ["scan", "analyze"], "engineer": ["scan", "analyze", "repair"], "carrier": ["scan", "carry"]}[agent["role"]]
                    spares = s.store.read(CAPABLE_BODIES, run=run, required=["cap-" + cap for cap in required])
                    if spares:
                        return s.switch_body(run, agent["id"], spares[0][0])
                    continue
                tasks = s.ready(run, agent["id"])
                tasks.sort(key=lambda t: (t["status"] != "active", t["preferred_role"] != agent["role"], t["id"]))
                # Distinct roles avoid stealing a teammate's work while they are en route.
                task = next((t for t in tasks if t["status"] == "active" or t["preferred_role"] == agent["role"] or self._preferred_unavailable(run, t["preferred_role"])), None)
                if not task:
                    continue
                if task["status"] == "pending":
                    return s.claim(run, agent["id"], task["id"])
                room = s.location(run, body["id"])
                destination = task["room"]
                if task["action"] == "deliver":
                    item = s.require(run, "relay", "Item")
                    carrying = s.store.read("MATCH (:Body {run_id: $run, id: $body})-[:CARRIES]->(:Item {id: 'relay'}) RETURN 1", run=run, body=body["id"])
                    if not carrying:
                        destination = s.location(run, "relay")
                        if item["status"] != "available" or not destination:
                            continue
                        action = "pick_up"
                    else:
                        action = "drop"
                else:
                    action = task["action"]
                if room != destination:
                    route = s.route(run, room, destination)
                    if len(route) < 2:
                        continue
                    return s.act(run, agent["id"], "move", task["id"], route[1], "Shortest currently open corridor path returned by FalkorDB.")
                return s.act(run, agent["id"], action, task["id"], reason="Deterministic simulation policy using current graph eligibility and evidence.")
            return {"ok": False, "waiting": True, "detail": "No executable action. Check body availability, cargo and corridor connectivity."}

    def _preferred_unavailable(self, run: str, role: str) -> bool:
        body = self.service.body(run, "agent-" + role)
        return not body or body["status"] != "online"
