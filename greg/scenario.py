"""Original, synthetic station. Coordinates are presentation metadata only."""
from __future__ import annotations

from .database import GraphStore

ROOMS = [
    ("hub", "Nexus", "COMMAND", 0, 0, 0),
    ("power", "Power core", "ENERGY", -8, 0, -5),
    ("comms", "Array control", "COMMS", 8, 0, -5),
    ("cooling", "Life support", "THERMAL", 8, 0, 5),
    ("lab", "Research bay", "SCIENCE", -8, 0, 5),
    ("stores", "Supply dock", "LOGISTICS", 0, 0, 10),
    ("airlock", "Airlock 02", "TRANSIT", 0, 0, -10),
]
CORRIDORS = [("hub", "power"), ("hub", "comms"), ("hub", "cooling"), ("hub", "lab"), ("hub", "stores"), ("hub", "airlock"), ("power", "airlock"), ("comms", "airlock"), ("cooling", "stores"), ("lab", "stores")]
BODIES = [
    ("pip", "PIP", "scout", "hub", ["scan", "analyze"], "#7ee4c5"),
    ("bolt", "BOLT", "engineer", "hub", ["scan", "analyze", "repair"], "#f6b66b"),
    ("moss", "MOSS", "carrier", "stores", ["carry", "scan"], "#a9b6ff"),
    ("echo", "ECHO", "reserve", "airlock", ["scan", "analyze", "repair", "carry"], "#f2e7d1"),
]
TASKS = [
    ("scan-cooling", "Inspect cooling failure", "inspect", "scan", "coolant", "cooling", [], "scout"),
    ("scan-comms", "Inspect communication failure", "inspect", "scan", "antenna", "comms", [], "engineer"),
    ("correlate", "Find a shared cause", "diagnose", "analyze", "hub", "hub", ["scan-cooling", "scan-comms"], "scout"),
    ("supply", "Deliver a replacement relay", "deliver", "carry", "relay", "power", ["correlate"], "carrier"),
    ("repair", "Restore the shared power bus", "repair", "repair", "bus", "power", ["supply"], "engineer"),
    ("verify-cooling", "Verify cooling recovered", "verify", "scan", "coolant", "cooling", ["repair"], "scout"),
    ("verify-comms", "Verify communications recovered", "verify", "scan", "antenna", "comms", ["repair"], "engineer"),
]


def seed(store: GraphStore, run: str, mode: str, scenario: str = "shared-power") -> None:
    store.add(run, run, "Run", name="ORPHEUS / Recovery 07", mode=mode, scenario=scenario, status="ready", tick=0, created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat())
    for node_id, name, sector, x, y, z in ROOMS:
        store.add(run, node_id, "Room", name=name, sector=sector, x=x, y=y, z=z)
    for a, b in CORRIDORS:
        store.link(run, a, b, "CONNECTS", blocked=False)
        store.link(run, b, a, "CONNECTS", blocked=False)
    for cap in ["scan", "analyze", "repair", "carry"]:
        store.add(run, "cap-" + cap, "Capability", name=cap)
    for node_id, name, role, room, caps, color in BODIES:
        store.add(run, node_id, "Body", name=name, role=role, status="standby" if role == "reserve" else "online", battery=100, color=color)
        store.link(run, node_id, room, "LOCATED_IN")
        for cap in caps:
            store.link(run, node_id, "cap-" + cap, "HAS_CAPABILITY")
        if role != "reserve":
            agent = "agent-" + role
            store.add(run, agent, "Agent", name={"scout": "Navigator", "engineer": "Mechanic", "carrier": "Quartermaster"}[role], role=role)
            store.link(run, agent, node_id, "EMBODIES")
    for node_id, name, room, status in [("bus", "Primary relay bus", "power", "unknown"), ("coolant", "Cooling loop", "cooling", "degraded"), ("antenna", "Communication array", "comms", "degraded"), ("samples", "Research samples", "lab", "at_risk")]:
        store.add(run, node_id, "System", name=name, status=status)
        store.link(run, node_id, room, "LOCATED_IN")
    store.link(run, "coolant", "bus", "DEPENDS_ON")
    store.link(run, "antenna", "bus", "DEPENDS_ON")
    store.link(run, "samples", "coolant", "DEPENDS_ON")
    store.add(run, "fault-relay", "Fault", name="Relay contact failure", active=True)
    store.link(run, "fault-relay", "bus", "AFFECTS")
    store.add(run, "relay", "Item", name="Replacement relay", status="available")
    store.link(run, "relay", "stores", "LOCATED_IN")
    for node_id, name, action, cap, target, room, deps, preferred in TASKS:
        store.add(run, node_id, "Task", name=name, action=action, target=target, room=room, status="pending", preferred_role=preferred)
        store.link(run, node_id, "cap-" + cap, "REQUIRES")
        for dependency in deps:
            store.link(run, node_id, dependency, "DEPENDS_ON")
