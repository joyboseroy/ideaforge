"""
agents/innovation_score.py

InnovationScore — weighted scoring of patent claims.

Formula (Section 6.2 of paper):

    InnovationScore(c) = w1 * convergent_count
                       + w2 * methodology_diversity
                       + w3 * claim_strength
                       - w4 * prior_art_challenge_count

Where:
    convergent_count        = number of CONVERGENT edges on this claim
    methodology_diversity   = number of distinct methodologies supporting claim
    claim_strength          = agent-assigned strength score (0-1)
    prior_art_challenge_count = number of PriorArt nodes challenging this claim

Default weights: w1=0.4, w2=0.3, w3=0.2, w4=0.1

The claim with highest InnovationScore is the recommended
primary independent claim for the patent draft.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kg.graph import IdeaGraph


# Default weights
W_CONVERGENT = 0.4
W_DIVERSITY = 0.3
W_STRENGTH = 0.2
W_PRIOR_ART_PENALTY = 0.1


def compute_innovation_scores(
    graph: IdeaGraph,
    w_convergent: float = W_CONVERGENT,
    w_diversity: float = W_DIVERSITY,
    w_strength: float = W_STRENGTH,
    w_prior_art: float = W_PRIOR_ART_PENALTY,
) -> list[dict]:
    """
    Compute InnovationScore for all claims in the KG.

    Returns list of scored claims sorted by InnovationScore descending.
    """
    all_claims = graph.get_all_claims()
    convergent_claims = {
        c["claim_id"]: c for c in graph.get_convergent_claims()
    }

    # Get prior art challenge counts via raw query
    try:
        prior_art_counts = {}
        result = graph.graph.query("""
            MATCH (pa:PriorArt)-[:CHALLENGES]->(cl:Claim)
            RETURN cl.id AS claim_id, COUNT(pa) AS challenge_count
        """)
        for row in result.result_set:
            prior_art_counts[row[0]] = row[1]
    except Exception:
        prior_art_counts = {}

    # Get methodology diversity per claim via raw query
    try:
        diversity_counts = {}
        result = graph.graph.query("""
            MATCH (pr:Principle)-[:SUPPORTS]->(cl:Claim)
            RETURN cl.id AS claim_id, COUNT(DISTINCT pr.name) AS diversity
            UNION
            MATCH (t:Transformation)-[:GENERATES]->(cl:Claim)
            RETURN cl.id AS claim_id, COUNT(DISTINCT t.scamper_type) AS diversity
        """)
        for row in result.result_set:
            cid = row[0]
            diversity_counts[cid] = diversity_counts.get(cid, 0) + row[1]
    except Exception:
        diversity_counts = {}

    scored = []
    for claim in all_claims:
        cid = claim["id"]

        convergent_count = convergent_claims.get(cid, {}).get("convergent_count", 0)
        methodology_diversity = diversity_counts.get(cid, 1)
        claim_strength = float(claim.get("strength") or 0.5)
        prior_art_count = prior_art_counts.get(cid, 0)

        # Normalise convergent count (cap at 5)
        norm_convergent = min(convergent_count / 5.0, 1.0)
        # Normalise diversity (cap at 3 methodologies)
        norm_diversity = min(methodology_diversity / 3.0, 1.0)
        # Normalise prior art penalty (cap at 3)
        norm_prior_art = min(prior_art_count / 3.0, 1.0)

        score = (
            w_convergent * norm_convergent
            + w_diversity * norm_diversity
            + w_strength * claim_strength
            - w_prior_art * norm_prior_art
        )

        scored.append({
            "id": cid,
            "text": claim.get("text", ""),
            "methodology": claim.get("methodology", ""),
            "innovation_score": round(score, 4),
            "convergent_count": convergent_count,
            "methodology_diversity": methodology_diversity,
            "claim_strength": claim_strength,
            "prior_art_challenges": prior_art_count,
        })

    scored.sort(key=lambda x: x["innovation_score"], reverse=True)
    return scored


def print_innovation_report(scored_claims: list[dict]) -> None:
    """Print a formatted innovation score report."""
    print("\nInnovationScore Report")
    print("=" * 60)
    print(f"{'Rank':<5} {'Score':<8} {'Conv':<6} {'Div':<5} {'PA':<5} Claim")
    print("-" * 60)

    for i, c in enumerate(scored_claims, 1):
        text_preview = c["text"][:40] + "..." if len(c["text"]) > 40 else c["text"]
        print(
            f"{i:<5} "
            f"{c['innovation_score']:<8.3f} "
            f"{c['convergent_count']:<6} "
            f"{c['methodology_diversity']:<5} "
            f"{c['prior_art_challenges']:<5} "
            f"[{c['methodology']}] {text_preview}"
        )

    if scored_claims:
        best = scored_claims[0]
        print(f"\nTop candidate: [{best['methodology']}] {best['text'][:70]}")
        print(f"InnovationScore: {best['innovation_score']:.3f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python agents/innovation_score.py <graph_name>")
        sys.exit(1)

    graph_name = sys.argv[1]
    graph = IdeaGraph(graph_name=graph_name)
    scores = compute_innovation_scores(graph)
    print_innovation_report(scores)
