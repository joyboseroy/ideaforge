"""
ideaforge.py

Main IdeaForge pipeline.

Usage:
    python ideaforge.py --idea "your invention idea here"
    python ideaforge.py --idea "your idea" --dry-run
    python ideaforge.py --idea "your idea" --output patent_draft.txt
"""

import argparse
import os
from kg.graph import IdeaGraph
from agents.methodology_agents import TRIZAgent, DesignThinkingAgent, SCAMPERAgent
from agents.patent_agent import PatentAgent
from agents.prior_art_agent import PriorArtAgent
from agents.embedding_synthesis import EmbeddingSynthesisAgent
from agents.innovation_score import compute_innovation_scores, print_innovation_report

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("GRAPH_NAME", "ideaforge")


def run_ideaforge(idea, domain="", output_file=None, dry_run=False, clear_graph=True):
    print(f"\nIdeaForge — Multi-Methodology Innovation Agent")
    print(f"{'=' * 55}")
    print(f"Idea: {idea}")
    print(f"FalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print(f"Model: {os.getenv('OLLAMA_MODEL', 'tinyllama')}")
    print(f"Dry run: {dry_run}")
    print(f"{'=' * 55}\n")

    graph = IdeaGraph(host=FALKORDB_HOST, port=FALKORDB_PORT, graph_name=GRAPH_NAME)

    if clear_graph:
        graph.clear()
        print("Graph cleared for fresh run.\n")

    # Step 1
    print("Step 1: Ingesting idea into knowledge graph...")
    problem_id = graph.add_problem(statement=idea, domain=domain)
    print(f"  Problem node created: {problem_id}\n")

    all_claim_ids = []

    if dry_run:
        print("DRY RUN — skipping LLM calls, adding placeholder claims\n")
        for methodology in ["TRIZ", "DesignThinking", "SCAMPER"]:
            cid = graph.add_claim(
                text=f"A method for {idea}",
                methodology=methodology,
                strength=0.6,
            )
            all_claim_ids.append(cid)
            print(f"  Placeholder claim added [{methodology}]")
        print()
    else:
        # Step 2
        print("Step 2: TRIZ contradiction analysis...")
        ids = TRIZAgent(graph).run(idea, problem_id)
        all_claim_ids.extend(ids)
        print(f"  TRIZ: {len(ids)} claims added\n")

        # Step 3
        print("Step 3: Design Thinking — user needs analysis...")
        ids = DesignThinkingAgent(graph).run(idea, problem_id)
        all_claim_ids.extend(ids)
        print(f"  Design Thinking: {len(ids)} claims added\n")

        # Step 4
        print("Step 4: SCAMPER transformations...")
        ids = SCAMPERAgent(graph).run(idea, problem_id)
        all_claim_ids.extend(ids)
        print(f"  SCAMPER: {len(ids)} claims added\n")

    # Step 5 — runs in both modes
    print("Step 5: Searching for prior art (arXiv)...")
    PriorArtAgent(graph).run(idea, problem_id)
    print()

    # Step 6 — runs in both modes
    print("Step 6: Cross-methodology convergence detection...")
    convergent_pairs = EmbeddingSynthesisAgent(graph, threshold=0.65).run()
    print(f"  Convergent pairs found: {len(convergent_pairs)}\n")

    # Step 7 — runs in both modes
    print("Step 7: Computing InnovationScore for all claims...")
    scored_claims = compute_innovation_scores(graph)
    print_innovation_report(scored_claims)
    print()

    # Step 8 — runs in both modes
    print("Step 8: Drafting patent from knowledge graph...")
    patent_agent = PatentAgent(graph)
    patent = patent_agent.run(idea)
    patent_doc = patent_agent.format_patent_document(patent)

    summary = graph.get_summary()

    print(f"\n{'=' * 55}")
    print("IdeaForge Complete")
    print(f"{'=' * 55}")
    print("\nKnowledge Graph summary:")
    for row in summary:
        print(f"  {row['node_type']}: {row['count']} nodes")

    print(f"\nTop patent candidates:")
    for c in scored_claims[:3]:
        print(f"  [{c.get('methodology', '?')}] {c.get('text', '')[:70]}")
        print(f"  InnovationScore: {c.get('innovation_score', 0):.3f}")

    print(f"\n{patent_doc}")

    if output_file:
        with open(output_file, "w") as f:
            f.write(patent_doc)
        print(f"\nPatent draft saved to: {output_file}")
        print("Run: python visualize.py --static  to generate graph image")

    return {"patent": patent, "scored_claims": scored_claims}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--idea", required=True)
    parser.add_argument("--domain", default="")
    parser.add_argument("--output", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-clear", action="store_true")
    args = parser.parse_args()
    run_ideaforge(
        idea=args.idea, domain=args.domain,
        output_file=args.output, dry_run=args.dry_run,
        clear_graph=not args.no_clear,
    )


if __name__ == "__main__":
    main()
