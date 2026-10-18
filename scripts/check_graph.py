"""Verify real FalkorDB writes and two-hop reads; this is not the product agent."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from falkordb import FalkorDB
from redis.exceptions import RedisError


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    name = os.getenv("FALKORDB_GRAPH", "greg_setup")
    connection = {
        "host": os.getenv("FALKORDB_HOST", "127.0.0.1"),
        "port": int(os.getenv("FALKORDB_PORT", "6379")),
        "socket_connect_timeout": 5,
        "socket_timeout": 10,
        "ssl": os.getenv("FALKORDB_SSL", "false").lower() == "true",
    }
    for key in ("username", "password"):
        if value := os.getenv(f"FALKORDB_{key.upper()}"):
            connection[key] = value
    try:
        db = FalkorDB(**connection)
        graph = db.select_graph(name)
        # Isolated setup labels and MERGE keep repeated checks idempotent.
        graph.query(
            "MERGE (a:SetupCheck {id: $account}) "
            "MERGE (d:SetupCheck {id: $device}) "
            "MERGE (b:SetupCheck {id: $other}) "
            "MERGE (a)-[:SETUP_USES]->(d) "
            "MERGE (b)-[:SETUP_USES]->(d)",
            params={"account": "account-a", "device": "device-1", "other": "account-b"},
        )
        result = graph.ro_query(
            "MATCH p=(a:SetupCheck {id: $account})-[:SETUP_USES]->"
            "(d:SetupCheck)<-[:SETUP_USES]-(b:SetupCheck) "
            "WHERE b.id <> a.id "
            "RETURN [n IN nodes(p) | n.id], length(p)",
            params={"account": "account-a"},
        )
        expected = [[['account-a', 'device-1', 'account-b'], 2]]
        if result.result_set != expected:
            raise RuntimeError(f"Unexpected graph result: {result.result_set!r}")
        print(json.dumps({"status": "ok", "graph": name, "two_hop_path": result.result_set}))
        return 0
    except (RedisError, RuntimeError) as exc:
        print(f"FalkorDB check failed: {exc}", file=sys.stderr)
        print("Check connection settings, query results and: docker compose logs --tail 50 falkordb", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
