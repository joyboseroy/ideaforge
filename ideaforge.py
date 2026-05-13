"""
ideaforge.py

Main IdeaForge pipeline.

Usage:
    python ideaforge.py --idea "your invention idea here"
    python ideaforge.py --idea "your idea" --dry-run
    python ideaforge.py --idea "your idea" --output patent_draft.txt

Runs all methodology agents sequentially, then synthesis,
then generates patent draft. Writes everything to FalkorDB.
"""

import argparse
import os
import sys
from datetime import datetime

from kg.graph import IdeaGraph
from agents.methodology_agents import (
    TRIZAgent,
    DesignThinkingAgent,
    SCAMPERAgent,
)
from agents.patent_agent import PatentAgent
from agents.prior_art_agent import PriorArtAgent
from agents.embedding_synthesis import EmbeddingSynthesisAgent
from agents.innovation_score import compute_innovation_scores, print_innovation_report
from agents.prior_art_agent import PriorArtAgent
from agents.embedding_synthesis import EmbeddingSynthesisAgent
from agents.innovation_score import compute_innovation_scores, print_innovation_report
_PLACEHOLDER = (
    TRIZAgent,
    DesignThinkingAgent,
    SCAMPERAgent,
    SynthesisAgent,
)
from agents.patent_agent import PatentAgent

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("GRAPH_NAME", "ideaforge")


def run_ideaforge(
    idea: str,
    domain: str = "",
    output_file: str = None,
    dry_run: bool = False,
    clear_graph: bool = True,
) -> dict:
    """
    Run the full IdeaForge pipeline.

    1. Ingest idea into KG
    2. TRIZ agent
    3. Design Thinking agent
    4. SCAMPER agent
    5. Synthesis agent (convergence detection)
    6. Patent agent (draft from KG)
    """

    print(f"\nIdeaForge — Multi-Methodology Innovation Agent")
    print(f"{'=' * 55}")
    print(f"Idea: {idea}")
    print(f"FalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print(f"Model: {os.getenv('OLLAMA_MODEL', 'tinyllama')}")
    print(f"{'=' * 55}\n")

    # Connect to graph
    graph = IdeaGraph(
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
        graph_name=GRAPH_NAME,
    )

    if clear_graph:
        graph.clear()
        print("Graph cleared for fresh run.\n")

    # Step 1: Add problem node
    print("Step 1: Ingesting idea into knowledge graph...")
    problem_id = graph.add_problem(statement=idea, domain=domain)
    print(f"  Problem node created: {problem_id}\n")

    all_claim_ids = []

    if dry_run:
        print("DRY RUN — skipping LLM calls\n")
        # Add placeholder claims
        for methodology in ["TRIZ", "DesignThinking", "SCAMPER"]:
            cid = graph.add_claim(
                text=f"[{methodology}] A method for {idea[:50]}",
                methodology=methodology,
                strength=0.6,
            )
            all_claim_ids.append(cid)
    else:
        # Step 2: TRIZ
        print("Step 2: TRIZ contradiction analysis...")
        triz = TRIZAgent(graph)
        ids = triz.run(idea, problem_id)
        all_claim_ids.extend(ids)
        print(f"  TRIZ: {len(ids)} claims added\n")

        # Step 3: Design Thinking
        print("Step 3: Design Thinking — user needs analysis...")
        dt = DesignThinkingAgent(graph)
        ids = dt.run(idea, problem_id)
        all_claim_ids.extend(ids)
        print(f"  Design Thinking: {len(ids)} claims added\n")

        # Step 4: SCAMPER
        print("Step 4: SCAMPER transformations...")
        scamper = SCAMPERAgent(graph)
        ids = scamper.run(idea, problem_id)
        all_claim_ids.extend(ids)
        print(f"  SCAMPER: {len(ids)} claims added\n")

        # Step 5: Synthesis
        print("Step 5: Cross-methodology convergence detection...")
        synthesis = SynthesisAgent(graph)
        convergent_pairs = synthesis.run()
        print(f"  Convergent pairs found: {len(convergent_pairs)}\n")

    # Step 6: Patent draft
    print("Step 6: Drafting patent from knowledge graph...")
    patent_agent = PatentAgent(graph)
    patent = patent_agent.run(idea)
    patent_doc = patent_agent.format_patent_document(patent)

    # KG summary
    summary = graph.get_summary()
    strongest = graph.get_strongest_claims()

    print(f"\n{'=' * 55}")
    print("IdeaForge Complete")
    print(f"{'=' * 55}")
    print("\nKnowledge Graph summary:")
    for row in summary:
        print(f"  {row['node_type']}: {row['count']} nodes")

    print(f"\nTop patent candidates:")
    for c in strongest[:3]:
        print(f"  [{c.get('methodology', '?')}] {c.get('text', '')[:70]}...")
        print(f"  Convergent support: {c.get('convergent_count', 0)}")

    print(f"\n{patent_doc}")

    if output_file:
        with open(output_file, "w") as f:
            f.write(patent_doc)
        print(f"\nPatent draft saved to: {output_file}")

    return {
        "patent": patent,
        "patent_doc": patent_doc,
        "kg_summary": summary,
        "strongest_claims": strongest,
        "total_claims": len(all_claim_ids),
    }


def main():
    parser = argparse.ArgumentParser(
        description="IdeaForge — KG-grounded multi-methodology innovation agent"
    )
    parser.add_argument(
        "--idea",
        required=True,
        help="Your invention idea in plain language"
    )
    parser.add_argument(
        "--domain",
        default="",
        help="Technical domain (optional)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save patent draft to file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip LLM calls — test pipeline only"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear graph before running"
    )
    args = parser.parse_args()

    run_ideaforge(
        idea=args.idea,
        domain=args.domain,
        output_file=args.output,
        dry_run=args.dry_run,
        clear_graph=not args.no_clear,
    )


if __name__ == "__main__":
    main()
