"""
agents/embedding_synthesis.py

Embedding-based convergence detection.

Replaces the LLM yes/no convergence check in SynthesisAgent
with sentence-transformer cosine similarity.

Paper reference: Section 6.1 — Structural Triangulation

Algorithm:
    For each pair of claims from different methodologies:
        embed(claim1), embed(claim2)
        similarity = cosine_similarity(embed1, embed2)
        if similarity > threshold:
            create CONVERGENT edge
            record reason

This is more robust than LLM-based similarity because:
    - Deterministic
    - Fast
    - Not sensitive to LLM prompt variation
    - Produces a continuous similarity score for InnovationScore

Falls back to keyword overlap if sentence-transformers not available.
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kg.graph import IdeaGraph

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
    _model = None

    def get_model():
        global _model
        if _model is None:
            print("  [Embeddings] Loading sentence-transformers model...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model

except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("  [Embeddings] sentence-transformers not available — using keyword fallback")


def cosine_similarity(v1: list, v2: list) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def keyword_similarity(text1: str, text2: str) -> float:
    """Fallback: keyword overlap similarity."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity between two claim texts.
    Uses sentence-transformers if available, else keyword overlap.
    """
    if EMBEDDINGS_AVAILABLE:
        model = get_model()
        embeddings = model.encode([text1, text2])
        return float(cosine_similarity(
            embeddings[0].tolist(),
            embeddings[1].tolist()
        ))
    return keyword_similarity(text1, text2)


class EmbeddingSynthesisAgent:
    """
    Embedding-based cross-methodology convergence detection.

    Stronger than LLM-based synthesis because:
    - Deterministic and reproducible
    - Continuous similarity score feeds into InnovationScore
    - Works without Ollama

    Paper reference: Section 6.1
    """

    def __init__(
        self,
        graph: IdeaGraph,
        threshold: float = 0.75,
    ):
        self.graph = graph
        self.threshold = threshold

    def run(self) -> list[dict]:
        """
        Detect convergent claims using embedding similarity.

        Returns list of convergent pairs with similarity scores.
        """
        print(f"  [EmbeddingSynthesis] Detecting convergence (threshold={self.threshold})...")
        print(f"  Method: {'sentence-transformers' if EMBEDDINGS_AVAILABLE else 'keyword overlap'}")

        all_claims = self.graph.get_all_claims()
        if len(all_claims) < 2:
            print("  [EmbeddingSynthesis] Not enough claims for synthesis")
            return []

        # Group by methodology
        by_methodology = {}
        for claim in all_claims:
            m = claim.get("methodology", "unknown")
            if m not in by_methodology:
                by_methodology[m] = []
            by_methodology[m].append(claim)

        methodologies = list(by_methodology.keys())
        convergent_pairs = []

        for i, m1 in enumerate(methodologies):
            for m2 in methodologies[i+1:]:
                for c1 in by_methodology[m1]:
                    for c2 in by_methodology[m2]:
                        sim = compute_similarity(
                            c1.get("text", ""),
                            c2.get("text", "")
                        )

                        if sim >= self.threshold:
                            self.graph.link_convergent_claims(
                                c1["id"], c2["id"]
                            )
                            pair = {
                                "claim1_id": c1["id"],
                                "claim2_id": c2["id"],
                                "claim1_text": c1["text"][:60],
                                "claim2_text": c2["text"][:60],
                                "methodologies": [m1, m2],
                                "similarity": round(sim, 4),
                            }
                            convergent_pairs.append(pair)
                            print(
                                f"  [EmbeddingSynthesis] CONVERGENT "
                                f"({m1} + {m2}): {sim:.3f}"
                            )

        print(
            f"  [EmbeddingSynthesis] "
            f"{len(convergent_pairs)} convergent pairs found"
        )
        return convergent_pairs
