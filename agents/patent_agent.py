"""
agents/patent_agent.py

Patent claim drafting agent.

Queries the KG for strongest/convergent claims and drafts
a structured patent document with independent and dependent claims.

Paper reference: the patent draft is grounded in the KG subgraph —
not raw LLM hallucination — making it more defensible and traceable.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import ollama
except ImportError:
    print("ERROR: pip install ollama")
    sys.exit(1)

from kg.graph import IdeaGraph

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")


def call_llm(prompt: str, model: str = OLLAMA_MODEL) -> str:
    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.2, "num_predict": 600},
        )
        return response["response"].strip()
    except Exception as e:
        return f"LLM error: {e}"


class PatentAgent:
    """
    Drafts a structured patent document from the KG.

    Process:
    1. Retrieve strongest claims (by convergent count + strength)
    2. Draft independent claim from most convergent claim
    3. Draft dependent claims from supporting methodology claims
    4. Generate abstract and title
    5. Return structured patent draft
    """

    def __init__(self, graph: IdeaGraph):
        self.graph = graph

    def run(self, idea: str) -> dict:
        """
        Generate a patent draft from the KG.

        Returns dict with title, abstract, claims, field, background.
        """
        print("  [Patent Agent] Drafting patent from KG...")

        # Get strongest claims from KG
        strongest = self.graph.get_strongest_claims()
        all_claims = self.graph.get_all_claims()
        problem = self.graph.get_problem()

        if not strongest:
            strongest = all_claims[:3]

        # Build context string from KG claims
        claims_context = "\n".join([
            f"- [{c.get('methodology', '?')}] {c.get('text', '')}"
            for c in strongest[:5]
        ])

        prompt = f"""You are a patent attorney. Draft a patent based on this invention:

IDEA: {idea}

PROBLEM BEING SOLVED: {problem.get('statement', idea)}

KG-DERIVED CLAIMS (these are grounded in multi-methodology analysis):
{claims_context}

Write a patent draft with:
1. TITLE: (concise invention title)
2. FIELD: (technical field)
3. BACKGROUND: (2 sentences on problem)
4. ABSTRACT: (3 sentences describing the invention)
5. CLAIM 1: (independent claim — broadest novel feature)
6. CLAIM 2: (dependent on claim 1 — add specific detail)
7. CLAIM 3: (dependent on claim 1 — alternative embodiment)

Be specific and technical. Base claims on the KG analysis above."""

        raw = call_llm(prompt)

        # Parse sections
        sections = {
            "title": "",
            "field": "",
            "background": "",
            "abstract": "",
            "claims": [],
            "raw": raw,
            "generated_at": datetime.now().isoformat(),
            "kg_claims_used": len(strongest),
            "idea": idea,
        }

        lines = raw.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            upper = line.upper()
            if "TITLE:" in upper or line.startswith("1."):
                if "TITLE" in upper:
                    sections["title"] = line.replace("TITLE:", "").replace("1.", "").strip()
                    current_section = "title"
            elif "FIELD:" in upper:
                sections["field"] = line.replace("FIELD:", "").strip()
                current_section = "field"
            elif "BACKGROUND:" in upper:
                sections["background"] = line.replace("BACKGROUND:", "").strip()
                current_section = "background"
            elif "ABSTRACT:" in upper:
                sections["abstract"] = line.replace("ABSTRACT:", "").strip()
                current_section = "abstract"
            elif "CLAIM 1:" in upper or "CLAIM 2:" in upper or "CLAIM 3:" in upper:
                claim_text = line.split(":", 1)[-1].strip()
                if claim_text:
                    sections["claims"].append(claim_text)
            elif current_section in ["background", "abstract"] and line:
                if current_section == "background" and sections["background"]:
                    sections["background"] += " " + line
                elif current_section == "abstract" and sections["abstract"]:
                    sections["abstract"] += " " + line

        # Fallback if parsing failed
        if not sections["title"]:
            sections["title"] = f"System and Method for {idea[:50]}"
        if not sections["claims"]:
            sections["claims"] = [
                c.get("text", "") for c in strongest[:3]
                if c.get("text")
            ]

        print(f"  [Patent Agent] Draft complete: {sections['title']}")
        return sections

    def format_patent_document(self, patent: dict) -> str:
        """Format patent dict as a readable document."""
        lines = [
            "=" * 60,
            "PATENT DRAFT — IdeaForge",
            "=" * 60,
            "",
            f"TITLE: {patent.get('title', '')}",
            "",
            f"FIELD OF INVENTION",
            patent.get("field", ""),
            "",
            "BACKGROUND",
            patent.get("background", ""),
            "",
            "ABSTRACT",
            patent.get("abstract", ""),
            "",
            "CLAIMS",
        ]

        for i, claim in enumerate(patent.get("claims", []), 1):
            lines.append(f"{i}. {claim}")
            lines.append("")

        lines += [
            "=" * 60,
            f"Generated by IdeaForge at {patent.get('generated_at', '')}",
            f"Based on {patent.get('kg_claims_used', 0)} KG-derived claims",
            "NOTE: This is a draft for review — consult a patent attorney",
            "=" * 60,
        ]

        return "\n".join(lines)
