"""
kg/schema.py

IdeaForge Knowledge Graph Schema.

Node types:
    Problem         — the core problem or challenge
    Contradiction   — TRIZ-style technical contradiction
    Principle       — TRIZ inventive principle resolving contradiction
    UserNeed        — Design Thinking persona + job-to-be-done
    Analogy         — biomimicry or cross-domain analogy
    Transformation  — SCAMPER transformation of the idea
    PriorArt        — existing patents or solutions
    Claim           — candidate patent claim

Edge types:
    HAS_CONTRADICTION   Problem -> Contradiction
    RESOLVED_BY         Contradiction -> Principle
    MOTIVATES           UserNeed -> Problem
    INSPIRES            Analogy -> Claim
    GENERATES           Transformation -> Claim
    SUPPORTS            Principle -> Claim
    CHALLENGES          PriorArt -> Claim
    CONVERGENT          Claim -> Claim (cross-methodology support)

The CONVERGENT edge is the key novel contribution:
it connects claims supported independently by multiple methodologies.
Higher convergent_count = stronger patent candidate.
"""

# Node labels
NODE_PROBLEM = "Problem"
NODE_CONTRADICTION = "Contradiction"
NODE_PRINCIPLE = "Principle"
NODE_USER_NEED = "UserNeed"
NODE_ANALOGY = "Analogy"
NODE_TRANSFORMATION = "Transformation"
NODE_PRIOR_ART = "PriorArt"
NODE_CLAIM = "Claim"

# Edge types
EDGE_HAS_CONTRADICTION = "HAS_CONTRADICTION"
EDGE_RESOLVED_BY = "RESOLVED_BY"
EDGE_MOTIVATES = "MOTIVATES"
EDGE_INSPIRES = "INSPIRES"
EDGE_GENERATES = "GENERATES"
EDGE_SUPPORTS = "SUPPORTS"
EDGE_CHALLENGES = "CHALLENGES"
EDGE_CONVERGENT = "CONVERGENT"

# ── Cypher: Create nodes ───────────────────────────────────────────────────────

CREATE_PROBLEM = (
    "MERGE (p:Problem {id: $id}) "
    "SET p.statement = $statement, p.domain = $domain, "
    "p.created_at = $created_at RETURN p"
)

CREATE_CONTRADICTION = (
    "MERGE (c:Contradiction {id: $id}) "
    "SET c.improving = $improving, c.worsening = $worsening, "
    "c.description = $description, c.created_at = $created_at RETURN c"
)

CREATE_PRINCIPLE = (
    "MERGE (pr:Principle {id: $id}) "
    "SET pr.name = $name, pr.triz_number = $triz_number, "
    "pr.description = $description, pr.created_at = $created_at RETURN pr"
)

CREATE_USER_NEED = (
    "MERGE (u:UserNeed {id: $id}) "
    "SET u.persona = $persona, u.job_to_be_done = $job_to_be_done, "
    "u.pain_level = $pain_level, u.created_at = $created_at RETURN u"
)

CREATE_ANALOGY = (
    "MERGE (a:Analogy {id: $id}) "
    "SET a.source_domain = $source_domain, a.mechanism = $mechanism, "
    "a.relevance = $relevance, a.created_at = $created_at RETURN a"
)

CREATE_TRANSFORMATION = (
    "MERGE (t:Transformation {id: $id}) "
    "SET t.scamper_type = $scamper_type, t.description = $description, "
    "t.created_at = $created_at RETURN t"
)

CREATE_PRIOR_ART = (
    "MERGE (pa:PriorArt {id: $id}) "
    "SET pa.title = $title, pa.source = $source, "
    "pa.similarity = $similarity, pa.created_at = $created_at RETURN pa"
)

CREATE_CLAIM = (
    "MERGE (cl:Claim {id: $id}) "
    "SET cl.text = $text, cl.claim_type = $claim_type, "
    "cl.methodology = $methodology, cl.strength = $strength, "
    "cl.created_at = $created_at RETURN cl"
)

# ── Cypher: Create edges ───────────────────────────────────────────────────────

CREATE_EDGE_HAS_CONTRADICTION = (
    "MATCH (p:Problem {id: $problem_id}), (c:Contradiction {id: $contradiction_id}) "
    "MERGE (p)-[:HAS_CONTRADICTION]->(c)"
)

CREATE_EDGE_RESOLVED_BY = (
    "MATCH (c:Contradiction {id: $contradiction_id}), (pr:Principle {id: $principle_id}) "
    "MERGE (c)-[:RESOLVED_BY]->(pr)"
)

CREATE_EDGE_MOTIVATES = (
    "MATCH (u:UserNeed {id: $need_id}), (p:Problem {id: $problem_id}) "
    "MERGE (u)-[:MOTIVATES]->(p)"
)

CREATE_EDGE_SUPPORTS = (
    "MATCH (pr:Principle {id: $principle_id}), (cl:Claim {id: $claim_id}) "
    "MERGE (pr)-[:SUPPORTS]->(cl)"
)

CREATE_EDGE_INSPIRES = (
    "MATCH (a:Analogy {id: $analogy_id}), (cl:Claim {id: $claim_id}) "
    "MERGE (a)-[:INSPIRES]->(cl)"
)

CREATE_EDGE_GENERATES = (
    "MATCH (t:Transformation {id: $transformation_id}), (cl:Claim {id: $claim_id}) "
    "MERGE (t)-[:GENERATES]->(cl)"
)

CREATE_EDGE_CHALLENGES = (
    "MATCH (pa:PriorArt {id: $prior_art_id}), (cl:Claim {id: $claim_id}) "
    "MERGE (pa)-[:CHALLENGES]->(cl)"
)

CREATE_EDGE_CONVERGENT = (
    "MATCH (c1:Claim {id: $claim1_id}), (c2:Claim {id: $claim2_id}) "
    "MERGE (c1)-[r:CONVERGENT]->(c2) "
    "ON CREATE SET r.count = 1 "
    "ON MATCH SET r.count = r.count + 1"
)

# ── Cypher: Queries ────────────────────────────────────────────────────────────

QUERY_ALL_CLAIMS = """
MATCH (cl:Claim)
RETURN cl.id AS id, cl.text AS text,
       cl.claim_type AS claim_type,
       cl.methodology AS methodology,
       cl.strength AS strength
ORDER BY cl.strength DESC
"""

QUERY_CONVERGENT_CLAIMS = """
MATCH (cl:Claim)-[r:CONVERGENT]->(cl2:Claim)
RETURN cl.id AS claim_id, cl.text AS claim_text,
       COUNT(r) AS convergent_count,
       COLLECT(cl2.methodology) AS supporting_methodologies
ORDER BY convergent_count DESC
"""

QUERY_STRONGEST_CLAIMS = """
MATCH (cl:Claim)
OPTIONAL MATCH (cl)-[r:CONVERGENT]->()
WITH cl, COUNT(r) AS convergent_count
RETURN cl.id AS id, cl.text AS text,
       cl.methodology AS methodology,
       cl.strength AS strength,
       convergent_count
ORDER BY convergent_count DESC, cl.strength DESC
LIMIT 5
"""

QUERY_SUMMARY = """
MATCH (n)
RETURN labels(n)[0] AS node_type, COUNT(n) AS count
ORDER BY node_type
"""

QUERY_PROBLEM = """
MATCH (p:Problem)
RETURN p.id AS id, p.statement AS statement, p.domain AS domain
"""
