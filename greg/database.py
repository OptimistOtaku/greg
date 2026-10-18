"""Small parameterized graph repository. FalkorDB is the only world store."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from falkordb import FalkorDB

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

RELATIONSHIPS = {
    "CONNECTS", "LOCATED_IN", "DEPENDS_ON", "REQUIRES", "HAS_CAPABILITY",
    "EMBODIES", "ASSIGNED_TO", "ABOUT", "SUPPORTED_BY", "AFFECTS", "CARRIES",
    "RESOLVES", "OBSERVED_BY", "USES", "VERIFIED_BY",
}


class GraphStore:
    def __init__(self, graph_name: str | None = None):
        options: dict[str, Any] = {
            "host": os.getenv("FALKORDB_HOST", "127.0.0.1"),
            "port": int(os.getenv("FALKORDB_PORT", "6379")),
            "ssl": os.getenv("FALKORDB_SSL", "false").lower() == "true",
            "socket_connect_timeout": 3,
            "socket_timeout": 10,
        }
        for key in ("username", "password"):
            if value := os.getenv(f"FALKORDB_{key.upper()}"):
                options[key] = value
        self.options = options
        self._client = None
        self._graph = None
        self.name = graph_name or os.getenv("FALKORDB_MISSION_GRAPH", "greg_crew")

    @property
    def client(self):
        if self._client is None:
            self._client = FalkorDB(**self.options)
        return self._client

    @property
    def graph(self):
        if self._graph is None:
            self._graph = self.client.select_graph(self.name)
        return self._graph

    def query(self, cypher: str, **params: Any) -> list[list[Any]]:
        return self.graph.query(cypher, params=params).result_set

    def read(self, cypher: str, **params: Any) -> list[list[Any]]:
        return self.graph.ro_query(cypher, params=params).result_set

    def health(self) -> bool:
        return bool(self.client.connection.ping())

    def add(self, run: str, node_id: str, kind: str, **properties: Any) -> None:
        if kind not in {"Run", "Room", "System", "Body", "Agent", "Capability", "Task", "Item", "Observation", "Event", "Fault", "Hypothesis"}:
            raise ValueError("Unknown entity kind")
        props = {"id": node_id, "run_id": run, "kind": kind, **properties}
        assignments = ", ".join(f"n.{key} = ${key}" for key in props)
        self.query(f"MERGE (n:Entity:{kind} {{run_id: $run_id, id: $id}}) SET {assignments}", **props)

    def update(self, run: str, node_id: str, **props: Any) -> None:
        if not props or any(not key.replace("_", "").isalnum() for key in props):
            raise ValueError("Invalid property update")
        clause = ", ".join(f"n.{key} = $v_{key}" for key in props)
        self.query(f"MATCH (n:Entity {{run_id: $run, id: $id}}) SET {clause}", run=run, id=node_id, **{f"v_{k}": v for k, v in props.items()})

    def get(self, run: str, node_id: str) -> dict[str, Any] | None:
        rows = self.read("MATCH (n:Entity {run_id: $run, id: $id}) RETURN properties(n)", run=run, id=node_id)
        return rows[0][0] if rows else None

    def link(self, run: str, source: str, target: str, relationship: str, **props: Any) -> None:
        if relationship not in RELATIONSHIPS:
            raise ValueError("Unknown relationship")
        suffix = " SET " + ", ".join(f"r.{key} = $v_{key}" for key in props) if props else ""
        self.query(
            f"MATCH (a:Entity {{run_id: $run, id: $source}}), (b:Entity {{run_id: $run, id: $target}}) "
            f"MERGE (a)-[r:{relationship}]->(b){suffix}",
            run=run, source=source, target=target, **{f"v_{k}": v for k, v in props.items()},
        )

    def unlink(self, run: str, source: str, target: str | None, relationship: str) -> None:
        if relationship not in RELATIONSHIPS:
            raise ValueError("Unknown relationship")
        end = "(b:Entity {run_id: $run, id: $target})" if target else "(b)"
        self.query(f"MATCH (a:Entity {{run_id: $run, id: $source}})-[r:{relationship}]->{end} DELETE r", run=run, source=source, target=target or "")

    def nodes(self, run: str, kind: str | None = None) -> list[dict[str, Any]]:
        rows = self.read(
            "MATCH (n:Entity {run_id: $run}) WHERE $kind = '' OR n.kind = $kind RETURN properties(n)",
            run=run, kind=kind or "",
        )
        return [row[0] for row in rows]

    def edges(self, run: str) -> list[dict[str, Any]]:
        return [dict(source=a, target=b, type=t, **props) for a, b, t, props in self.read(
            "MATCH (a:Entity {run_id: $run})-[r]->(b:Entity {run_id: $run}) RETURN a.id, b.id, type(r), properties(r)", run=run,
        )]
