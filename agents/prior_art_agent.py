"""
agents/prior_art_agent.py

Prior Art Agent — searches arXiv and semantic similarity
to find existing work that challenges or supports claims.

Uses web search via arxiv API (no key needed) and
semantic similarity to find relevant prior art.

Paper reference: Section 5.3 — Prior Art Retrieval
"""

import sys
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kg.graph import IdeaGraph

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")


def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """
    Search arXiv for related papers using the free arXiv API.
    No API key needed.
    """
    base_url = "http://export.arxiv.org/api/query?"
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "relevance",
    })
    url = base_url + params

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8")

        # Parse Atom XML simply
        results = []
        entries = content.split("<entry>")[1:]
        for entry in entries:
            title = ""
            summary = ""
            arxiv_id = ""

            if "<title>" in entry:
                title = entry.split("<title>")[1].split("</title>")[0].strip()
            if "<summary>" in entry:
                summary = entry.split("<summary>")[1].split("</summary>")[0].strip()[:200]
            if "<id>" in entry:
                arxiv_id = entry.split("<id>")[1].split("</id>")[0].strip()

            if title:
                results.append({
                    "title": title,
                    "summary": summary,
                    "source": arxiv_id,
                    "similarity": 0.0,
                })

        return results

    except Exception as e:
        print(f"  [PriorArt] arXiv search failed: {e}")
        return []


def estimate_similarity(idea: str, paper_title: str, paper_summary: str) -> float:
    """
    Estimate similarity between idea and paper using simple keyword overlap.
    Falls back to LLM scoring if Ollama available.
    """
    # Simple keyword overlap as baseline
    idea_words = set(idea.lower().split())
    paper_words = set((paper_title + " " + paper_summary).lower().split())
    overlap = len(idea_words & paper_words)
    keyword_score = min(overlap / max(len(idea_words), 1), 1.0)

    if not OLLAMA_AVAILABLE or keyword_score < 0.1:
        return keyword_score

    try:
        prompt = f"""Rate similarity between 0.0 and 1.0:

Idea: {idea[:100]}
Paper: {paper_title}

Return only a number between 0.0 and 1.0"""

        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"temperature": 0.1, "num_predict": 10},
        )
        text = response["response"].strip()
        # Extract first float found
        import re
        nums = re.findall(r"0\.\d+|1\.0", text)
        if nums:
            return float(nums[0])
    except Exception:
        pass

    return keyword_score


class PriorArtAgent:
    """
    Searches for prior art relevant to the idea and its claims.

    Populates PriorArt nodes in the KG and links them
    to claims they challenge via CHALLENGES edges.

    Paper reference: Section 5.3
    """

    def __init__(self, graph: IdeaGraph):
        self.graph = graph

    def run(self, idea: str, problem_id: str) -> list[str]:
        """
        Search for prior art and add to KG.
        Returns list of prior art node IDs added.
        """
        print("  [PriorArt] Searching arXiv for related work...")

        # Build search query from idea
        # Use key technical terms
        query_terms = " ".join(idea.split()[:6])

        papers = search_arxiv(query_terms, max_results=5)

        if not papers:
            print("  [PriorArt] No results found (arXiv unreachable or no matches)")
            return []

        prior_art_ids = []
        all_claims = self.graph.get_all_claims()

        for paper in papers:
            similarity = estimate_similarity(
                idea, paper["title"], paper["summary"]
            )
            paper["similarity"] = round(similarity, 3)

            # Add to KG regardless of similarity
            pa_id = self.graph.add_prior_art(
                title=paper["title"],
                source=paper["source"],
                similarity=similarity,
            )
            prior_art_ids.append(pa_id)

            # Link to claims with high similarity (challenges them)
            if similarity > 0.3:
                for claim in all_claims[:2]:
                    try:
                        self.graph.link_prior_art_claim(pa_id, claim["id"])
                    except Exception:
                        pass

            print(f"  [PriorArt] {paper['title'][:60]}... (similarity: {similarity:.2f})")

        print(f"  [PriorArt] Added {len(prior_art_ids)} prior art nodes")
        return prior_art_ids
