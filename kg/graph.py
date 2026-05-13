"""
kg/graph.py

FalkorDB graph operations for IdeaForge.
Wraps all node/edge creation and queries.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb")
    sys.exit(1)

from kg.schema import *


class IdeaGraph:
    """
    Wrapper around FalkorDB for IdeaForge knowledge graph.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        graph_name: str = "ideaforge",
    ):
        self.db = FalkorDB(host=host, port=port)
        self.graph = self.db.select_graph(graph_name)
        self.graph_name = graph_name

    def _now(self):
        return datetime.now().isoformat()

    def _id(self, prefix: str, text: str) -> str:
        """Generate a simple ID from prefix + text hash."""
        return f"{prefix}_{abs(hash(text)) % 100000}"

    # ── Node creation ──────────────────────────────────────────────────────────

    def add_problem(self, statement: str, domain: str = "") -> str:
        id_ = self._id("prob", statement)
        self.graph.query(CREATE_PROBLEM, {
            "id": id_, "statement": statement,
            "domain": domain, "created_at": self._now()
        })
        return id_

    def add_contradiction(
        self, improving: str, worsening: str, description: str = ""
    ) -> str:
        id_ = self._id("contra", improving + worsening)
        self.graph.query(CREATE_CONTRADICTION, {
            "id": id_, "improving": improving,
            "worsening": worsening,
            "description": description, "created_at": self._now()
        })
        return id_

    def add_principle(
        self, name: str, triz_number: int = 0, description: str = ""
    ) -> str:
        id_ = self._id("prin", name)
        self.graph.query(CREATE_PRINCIPLE, {
            "id": id_, "name": name,
            "triz_number": triz_number,
            "description": description, "created_at": self._now()
        })
        return id_

    def add_user_need(
        self, persona: str, job_to_be_done: str, pain_level: int = 5
    ) -> str:
        id_ = self._id("need", persona + job_to_be_done)
        self.graph.query(CREATE_USER_NEED, {
            "id": id_, "persona": persona,
            "job_to_be_done": job_to_be_done,
            "pain_level": pain_level, "created_at": self._now()
        })
        return id_

    def add_analogy(
        self, source_domain: str, mechanism: str, relevance: float = 0.5
    ) -> str:
        id_ = self._id("anal", source_domain + mechanism)
        self.graph.query(CREATE_ANALOGY, {
            "id": id_, "source_domain": source_domain,
            "mechanism": mechanism,
            "relevance": relevance, "created_at": self._now()
        })
        return id_

    def add_transformation(self, scamper_type: str, description: str) -> str:
        id_ = self._id("trans", scamper_type + description)
        self.graph.query(CREATE_TRANSFORMATION, {
            "id": id_, "scamper_type": scamper_type,
            "description": description, "created_at": self._now()
        })
        return id_

    def add_prior_art(
        self, title: str, source: str = "", similarity: float = 0.5
    ) -> str:
        id_ = self._id("pa", title)
        self.graph.query(CREATE_PRIOR_ART, {
            "id": id_, "title": title,
            "source": source,
            "similarity": similarity, "created_at": self._now()
        })
        return id_

    def add_claim(
        self,
        text: str,
        claim_type: str = "independent",
        methodology: str = "",
        strength: float = 0.5,
    ) -> str:
        id_ = self._id("claim", text + methodology)
        self.graph.query(CREATE_CLAIM, {
            "id": id_, "text": text,
            "claim_type": claim_type,
            "methodology": methodology,
            "strength": strength, "created_at": self._now()
        })
        return id_

    # ── Edge creation ──────────────────────────────────────────────────────────

    def link_problem_contradiction(self, problem_id: str, contradiction_id: str):
        self.graph.query(CREATE_EDGE_HAS_CONTRADICTION, {
            "problem_id": problem_id,
            "contradiction_id": contradiction_id
        })

    def link_contradiction_principle(
        self, contradiction_id: str, principle_id: str
    ):
        self.graph.query(CREATE_EDGE_RESOLVED_BY, {
            "contradiction_id": contradiction_id,
            "principle_id": principle_id
        })

    def link_need_problem(self, need_id: str, problem_id: str):
        self.graph.query(CREATE_EDGE_MOTIVATES, {
            "need_id": need_id, "problem_id": problem_id
        })

    def link_principle_claim(self, principle_id: str, claim_id: str):
        self.graph.query(CREATE_EDGE_SUPPORTS, {
            "principle_id": principle_id, "claim_id": claim_id
        })

    def link_analogy_claim(self, analogy_id: str, claim_id: str):
        self.graph.query(CREATE_EDGE_INSPIRES, {
            "analogy_id": analogy_id, "claim_id": claim_id
        })

    def link_transformation_claim(
        self, transformation_id: str, claim_id: str
    ):
        self.graph.query(CREATE_EDGE_GENERATES, {
            "transformation_id": transformation_id,
            "claim_id": claim_id
        })

    def link_prior_art_claim(self, prior_art_id: str, claim_id: str):
        self.graph.query(CREATE_EDGE_CHALLENGES, {
            "prior_art_id": prior_art_id, "claim_id": claim_id
        })

    def link_convergent_claims(self, claim1_id: str, claim2_id: str):
        """
        Create or increment CONVERGENT edge between two claims.
        This is the core novelty detection mechanism.
        """
        self.graph.query(CREATE_EDGE_CONVERGENT, {
            "claim1_id": claim1_id, "claim2_id": claim2_id
        })

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_all_claims(self) -> list[dict]:
        result = self.graph.query(QUERY_ALL_CLAIMS)
        return [
            {
                "id": r[0], "text": r[1],
                "claim_type": r[2],
                "methodology": r[3],
                "strength": r[4],
            }
            for r in result.result_set
        ]

    def get_convergent_claims(self) -> list[dict]:
        """
        Get claims with cross-methodology convergent support.
        These are the strongest patent candidates.
        """
        result = self.graph.query(QUERY_CONVERGENT_CLAIMS)
        return [
            {
                "claim_id": r[0],
                "claim_text": r[1],
                "convergent_count": r[2],
                "supporting_methodologies": r[3],
            }
            for r in result.result_set
        ]

    def get_strongest_claims(self) -> list[dict]:
        result = self.graph.query(QUERY_STRONGEST_CLAIMS)
        return [
            {
                "id": r[0], "text": r[1],
                "methodology": r[2],
                "strength": r[3],
                "convergent_count": r[4],
            }
            for r in result.result_set
        ]

    def get_summary(self) -> list[dict]:
        result = self.graph.query(QUERY_SUMMARY)
        return [
            {"node_type": r[0], "count": r[1]}
            for r in result.result_set
        ]

    def get_problem(self) -> dict:
        result = self.graph.query(QUERY_PROBLEM)
        if result.result_set:
            r = result.result_set[0]
            return {"id": r[0], "statement": r[1], "domain": r[2]}
        return {}

    def clear(self):
        """Clear the graph — use for fresh runs."""
        self.graph.query("MATCH (n) DETACH DELETE n")
