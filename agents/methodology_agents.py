"""
agents/methodology_agents.py

Specialist methodology agents for IdeaForge.

Each agent receives the raw idea + existing KG context,
applies its methodology, and writes nodes/edges to the KG.

Agents:
    TRIZAgent           — contradiction analysis + inventive principles
    DesignThinkingAgent — persona + HMW + user needs
    SCAMPERAgent        — 7 SCAMPER transformations
    PriorArtAgent       — identify existing solutions
    SynthesisAgent      — cross-methodology convergence detection
    PatentAgent         — draft patent claims from KG

Uses TinyLlama via Ollama. Model-agnostic — swap OLLAMA_MODEL env var.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import ollama
except ImportError:
    print("ERROR: pip install ollama")
    sys.exit(1)

from kg.graph import IdeaGraph

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")

# ── TRIZ contradiction matrix (40 principles, simplified) ─────────────────────

TRIZ_PRINCIPLES = {
    1: "Segmentation — divide object into independent parts",
    2: "Taking out — separate interfering part or property",
    3: "Local quality — transition from homogeneous to heterogeneous",
    4: "Asymmetry — replace symmetrical form with asymmetrical",
    10: "Preliminary action — perform required change in advance",
    13: "The other way round — invert the action",
    15: "Dynamics — allow characteristics to change to be optimal",
    25: "Self-service — make object serve itself",
    28: "Mechanics substitution — replace mechanical system",
    35: "Parameter changes — change physical state or concentration",
    40: "Composite materials — transition to composite materials",
}


def call_llm(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """Call TinyLlama via Ollama."""
    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.3, "num_predict": 400, "stop": ["```"]},
        )
        return response["response"].strip()
    except Exception as e:
        return f"LLM error: {e}"


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {}


# ── TRIZ Agent ─────────────────────────────────────────────────────────────────

class TRIZAgent:
    """
    Applies TRIZ contradiction analysis to the idea.
    Identifies improving/worsening parameters and inventive principles.
    """

    def __init__(self, graph: IdeaGraph):
        self.graph = graph

    def run(self, idea: str, problem_id: str) -> list[str]:
        """Run TRIZ analysis. Returns list of claim IDs created."""
        print("  [TRIZ] Analysing contradictions...")

        prompt = f"""Apply TRIZ methodology to this invention idea:
{idea}

Identify ONE key technical contradiction and suggest 2 inventive principles.
Return JSON only:
{{
  "improving_parameter": "what improves",
  "worsening_parameter": "what gets worse",
  "contradiction_description": "brief description",
  "principles": [
    {{"name": "principle name", "number": 1, "description": "how it applies"}},
    {{"name": "principle name", "number": 2, "description": "how it applies"}}
  ],
  "claim": "A method for [novel technical solution based on TRIZ principle]"
}}"""

        raw = call_llm(prompt)
        data = parse_json_response(raw)

        if not data:
            print("  [TRIZ] Could not parse response — using fallback")
            data = {
                "improving_parameter": "functionality",
                "worsening_parameter": "complexity",
                "contradiction_description": "improving functionality increases complexity",
                "principles": [
                    {"name": "Segmentation", "number": 1,
                     "description": "divide system into independent parts"},
                    {"name": "Preliminary action", "number": 10,
                     "description": "pre-configure components"},
                ],
                "claim": f"A method for resolving technical contradictions in: {idea[:50]}",
            }

        claim_ids = []

        # Add contradiction
        contra_id = self.graph.add_contradiction(
            improving=data.get("improving_parameter", ""),
            worsening=data.get("worsening_parameter", ""),
            description=data.get("contradiction_description", ""),
        )
        self.graph.link_problem_contradiction(problem_id, contra_id)

        # Add principles and claims
        for p in data.get("principles", [])[:2]:
            prin_id = self.graph.add_principle(
                name=p.get("name", ""),
                triz_number=p.get("number", 0),
                description=p.get("description", ""),
            )
            self.graph.link_contradiction_principle(contra_id, prin_id)

            claim_text = data.get("claim", f"A method applying {p.get('name', 'TRIZ principle')} to {idea[:40]}")
            claim_id = self.graph.add_claim(
                text=claim_text,
                claim_type="independent",
                methodology="TRIZ",
                strength=0.7,
            )
            self.graph.link_principle_claim(prin_id, claim_id)
            claim_ids.append(claim_id)
            print(f"  [TRIZ] Claim: {claim_text[:80]}...")

        return claim_ids


# ── Design Thinking Agent ──────────────────────────────────────────────────────

class DesignThinkingAgent:
    """
    Applies Design Thinking — empathy, define, ideate.
    Creates UserNeed nodes and HMW-derived claims.
    """

    def __init__(self, graph: IdeaGraph):
        self.graph = graph

    def run(self, idea: str, problem_id: str) -> list[str]:
        print("  [Design Thinking] Identifying user needs...")

        prompt = f"""Apply Design Thinking to this invention idea:
{idea}

Identify 2 user personas and their needs. Generate How Might We questions.
Return JSON only:
{{
  "personas": [
    {{
      "name": "persona name",
      "job_to_be_done": "what they need to do",
      "pain_level": 8,
      "hmw": "How might we [solve their problem]?"
    }},
    {{
      "name": "persona name",
      "job_to_be_done": "what they need to do",
      "pain_level": 6,
      "hmw": "How might we [solve their problem]?"
    }}
  ],
  "claim": "A system for [user-centred solution addressing primary need]"
}}"""

        raw = call_llm(prompt)
        data = parse_json_response(raw)

        if not data:
            data = {
                "personas": [
                    {
                        "name": "Primary User",
                        "job_to_be_done": f"solve the core problem in {idea[:40]}",
                        "pain_level": 8,
                        "hmw": f"How might we make {idea[:40]} easier?",
                    }
                ],
                "claim": f"A user-centred system for {idea[:50]}",
            }

        claim_ids = []

        for persona in data.get("personas", [])[:2]:
            need_id = self.graph.add_user_need(
                persona=persona.get("name", "User"),
                job_to_be_done=persona.get("job_to_be_done", ""),
                pain_level=persona.get("pain_level", 5),
            )
            self.graph.link_need_problem(need_id, problem_id)

        claim_text = data.get("claim", f"A user-centred approach for {idea[:40]}")
        claim_id = self.graph.add_claim(
            text=claim_text,
            claim_type="independent",
            methodology="DesignThinking",
            strength=0.65,
        )
        claim_ids.append(claim_id)
        print(f"  [DT] Claim: {claim_text[:80]}...")

        return claim_ids


# ── SCAMPER Agent ──────────────────────────────────────────────────────────────

class SCAMPERAgent:
    """
    Applies SCAMPER transformations to generate idea variants.
    S-Substitute C-Combine A-Adapt M-Modify P-Put E-Eliminate R-Reverse
    """

    SCAMPER_TYPES = ["Substitute", "Combine", "Adapt", "Modify", "Eliminate", "Reverse"]

    def __init__(self, graph: IdeaGraph):
        self.graph = graph

    def run(self, idea: str, problem_id: str) -> list[str]:
        print("  [SCAMPER] Generating transformations...")

        prompt = f"""Apply SCAMPER to this invention idea:
{idea}

Generate 3 SCAMPER transformations from: Substitute, Combine, Adapt, Modify, Eliminate, Reverse.
Return JSON only:
{{
  "transformations": [
    {{"type": "Substitute", "description": "what to substitute and with what"}},
    {{"type": "Combine", "description": "what to combine"}},
    {{"type": "Adapt", "description": "what to adapt from another domain"}}
  ],
  "claim": "A method that [most promising SCAMPER transformation as patent claim]"
}}"""

        raw = call_llm(prompt)
        data = parse_json_response(raw)

        if not data:
            data = {
                "transformations": [
                    {"type": "Substitute", "description": f"Replace manual process in {idea[:30]} with automated agent"},
                    {"type": "Combine", "description": f"Combine {idea[:30]} with knowledge graph"},
                    {"type": "Adapt", "description": f"Adapt biological pattern recognition to {idea[:30]}"},
                ],
                "claim": f"A transformed approach combining multiple SCAMPER principles for {idea[:40]}",
            }

        claim_ids = []

        for t in data.get("transformations", [])[:3]:
            trans_id = self.graph.add_transformation(
                scamper_type=t.get("type", "Modify"),
                description=t.get("description", ""),
            )

        claim_text = data.get("claim", f"A SCAMPER-derived method for {idea[:40]}")
        claim_id = self.graph.add_claim(
            text=claim_text,
            claim_type="independent",
            methodology="SCAMPER",
            strength=0.6,
        )

        if data.get("transformations"):
            last_trans_id = self.graph._id(
                "trans",
                data["transformations"][-1].get("type", "") +
                data["transformations"][-1].get("description", "")
            )
            try:
                self.graph.link_transformation_claim(last_trans_id, claim_id)
            except Exception:
                pass

        claim_ids.append(claim_id)
        print(f"  [SCAMPER] Claim: {claim_text[:80]}...")
        return claim_ids


# ── Synthesis Agent ────────────────────────────────────────────────────────────

class SynthesisAgent:
    """
    Cross-methodology convergence detection.

    Finds claims from different methodologies that address
    the same underlying innovation. Creates CONVERGENT edges.

    This is the key novel contribution of IdeaForge.
    """

    def __init__(self, graph: IdeaGraph):
        self.graph = graph

    def run(self) -> list[dict]:
        """
        Compare all claims across methodologies.
        Create CONVERGENT edges between semantically similar claims
        from different methodologies.
        """
        print("  [Synthesis] Detecting cross-methodology convergence...")

        all_claims = self.graph.get_all_claims()
        if len(all_claims) < 2:
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

        # Compare claims across different methodologies
        for i, m1 in enumerate(methodologies):
            for m2 in methodologies[i+1:]:
                for c1 in by_methodology[m1]:
                    for c2 in by_methodology[m2]:
                        prompt = f"""Do these two patent claims address the same core innovation?

Claim 1 ({m1}): {c1['text']}
Claim 2 ({m2}): {c2['text']}

Answer with JSON only:
{{"convergent": true/false, "reason": "brief explanation"}}"""

                        raw = call_llm(prompt)
                        data = parse_json_response(raw)

                        if data.get("convergent", False):
                            self.graph.link_convergent_claims(c1["id"], c2["id"])
                            convergent_pairs.append({
                                "claim1": c1["text"][:60],
                                "claim2": c2["text"][:60],
                                "methodologies": [m1, m2],
                                "reason": data.get("reason", ""),
                            })
                            print(f"  [Synthesis] Convergent: {m1} + {m2}")

        return convergent_pairs
