"""These Cypher statements are executed in the product, not display examples."""

ROUTE = """
MATCH p=(a:Room {run_id: $run, id: $start})-[:CONNECTS*1..8]->(b:Room {run_id: $run, id: $end})
WHERE all(edge IN relationships(p) WHERE edge.blocked = false)
RETURN [node IN nodes(p) | node.id] AS route, length(p) AS hops
ORDER BY hops LIMIT 1
"""

READY_TASKS = """
MATCH (a:Agent {run_id: $run, id: $agent})-[:EMBODIES]->(b:Body)-[:HAS_CAPABILITY]->(cap:Capability)<-[:REQUIRES]-(t:Task)
WHERE b.status = 'online' AND (t.status = 'pending' OR (t.status = 'active' AND t.owner = $agent))
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dependency:Task)
WITH DISTINCT t, collect(dependency.status) AS dependencies
WHERE all(state IN dependencies WHERE state = 'done')
RETURN properties(t)
"""

SHARED_CAUSE = """
MATCH (o:Observation {run_id: $run})-[:ABOUT]->(s:System)-[:DEPENDS_ON*1..3]->(root:System)
WHERE o.signal = 'power_loss'
WITH root, collect(DISTINCT s.id) AS systems, collect(DISTINCT o.id) AS evidence
WHERE size(systems) >= 2
RETURN root.id, systems, evidence
"""

CLAIM = """
MATCH (t:Task {run_id: $run, id: $task})
WHERE t.status = 'pending'
SET t.status = 'active', t.owner = $agent
RETURN t.id
"""

IMPACT = """
MATCH p=(s:System {run_id: $run})-[:DEPENDS_ON*1..4]->(root:System {run_id: $run, id: $system})
RETURN s.id, [n IN nodes(p) | n.id]
"""

CAPABLE_BODIES = """
MATCH (b:Body {run_id: $run})-[:HAS_CAPABILITY]->(c:Capability)
WHERE b.status = 'standby' AND c.id IN $required
WITH b, collect(DISTINCT c.id) AS available
WHERE size(available) = size($required)
RETURN b.id
"""

QUERIES = {"route": ROUTE, "ready_tasks": READY_TASKS, "shared_cause": SHARED_CAUSE, "claim": CLAIM, "impact": IMPACT, "capable_bodies": CAPABLE_BODIES}
