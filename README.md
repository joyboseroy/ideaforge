# IdeaForge

**A Knowledge Graph-Grounded Multi-Methodology Agent Framework for Innovation Analysis and Patent Claim Generation**

Companion code for the paper:

> *IdeaForge: Cross-Methodology Convergent Novelty Detection via Knowledge Graph for Automated Patent Claim Generation*
> Joy Bose — arXiv (forthcoming)

---

## What this is

Most innovation AI tools apply a single methodology (TRIZ, Design Thinking, or SCAMPER) in isolation. IdeaForge is different:

1. Runs **multiple specialist agents** — TRIZ, Design Thinking, SCAMPER — in parallel
2. Stores every insight as a node in a **persistent FalkorDB knowledge graph**
3. A **synthesis agent** traverses the KG to find claims independently derived by multiple methodologies — these are the strongest patent candidates
4. A **patent agent** drafts structured claims grounded in the KG subgraph — not raw LLM hallucination
5. An **MCP server** exposes KG tools to external agents

The key novel contribution: the **CONVERGENT edge** — connecting claims supported independently by multiple methodologies. Higher convergent count = stronger patent candidate.

---

## Architecture

```
Raw idea (text)
      |
      v
Problem node -> FalkorDB KG
      |
      +---> TRIZAgent          -> Contradiction, Principle, Claim nodes
      |
      +---> DesignThinkingAgent -> UserNeed, Claim nodes
      |
      +---> SCAMPERAgent        -> Transformation, Claim nodes
      |
      v
SynthesisAgent   -> CONVERGENT edges between cross-methodology claims
      |
      v
PatentAgent      -> Patent draft grounded in KG subgraph
      |
      v
MCP Server       -> Exposes KG tools to external agents
```

---

## Knowledge Graph Schema

```
Nodes:
  Problem(statement, domain)
  Contradiction(improving, worsening)
  Principle(name, triz_number, description)
  UserNeed(persona, job_to_be_done, pain_level)
  Transformation(scamper_type, description)
  Analogy(source_domain, mechanism)
  PriorArt(title, source, similarity)
  Claim(text, methodology, strength)

Edges:
  (Problem)-[:HAS_CONTRADICTION]->(Contradiction)
  (Contradiction)-[:RESOLVED_BY]->(Principle)
  (Principle)-[:SUPPORTS]->(Claim)
  (UserNeed)-[:MOTIVATES]->(Problem)
  (Transformation)-[:GENERATES]->(Claim)
  (Analogy)-[:INSPIRES]->(Claim)
  (PriorArt)-[:CHALLENGES]->(Claim)
  (Claim)-[:CONVERGENT {count}]->(Claim)   <-- key novel contribution
```

---

## File structure

```
ideaforge/
├── kg/
│   ├── schema.py               # Node/edge types and Cypher templates
│   └── graph.py                # FalkorDB graph operations
├── agents/
│   ├── methodology_agents.py   # TRIZ, DesignThinking, SCAMPER, Synthesis agents
│   └── patent_agent.py         # Patent claim drafting from KG
├── mcp_server/
│   └── server.py               # MCP server exposing KG tools
├── ideaforge.py                # Main pipeline entry point
├── docker-compose.yml
└── requirements.txt
```

---

## Setup

```bash
# Start FalkorDB
docker-compose up -d

# Install dependencies
pip install -r requirements.txt

# Install Ollama + TinyLlama
# https://ollama.com
ollama pull tinyllama
ollama serve
```

---

## Usage

```bash
# Run on your idea
python ideaforge.py --idea "A voice-first legal assistant in Hindi for rural India"

# Save patent draft to file
python ideaforge.py \
  --idea "A voice-first legal assistant in Hindi for rural India" \
  --domain "legal technology" \
  --output patent_draft.txt

# Dry run (no Ollama needed — test pipeline only)
python ideaforge.py --idea "your idea" --dry-run

# Use a better model
OLLAMA_MODEL=llama3.2 python ideaforge.py --idea "your idea"
```

---

## Example output

```
IdeaForge Complete
=======================================================
Knowledge Graph summary:
  Claim: 3 nodes
  Contradiction: 1 nodes
  Principle: 2 nodes
  Problem: 1 nodes
  Transformation: 3 nodes
  UserNeed: 2 nodes

Top patent candidates:
  [TRIZ] A method for resolving the contradiction between...
  Convergent support: 2

  [DesignThinking] A system enabling rural users to...
  Convergent support: 1

PATENT DRAFT — IdeaForge
=======================================================
TITLE: Voice-Enabled Legal Assistance System for Low-Resource Languages
...
CLAIM 1: A method comprising...
CLAIM 2: The method of claim 1, wherein...
```

---

## MCP server tools

| Tool | Description |
|---|---|
| `get_all_claims` | All claims sorted by strength |
| `get_convergent_claims` | Claims with cross-methodology support |
| `get_strongest_claims` | Top 5 patent candidates |
| `get_kg_summary` | Node count summary |
| `add_claim` | Add a claim to the KG |

Start the MCP server:
```bash
python mcp_server/server.py
```

---

## Why this is different from existing work

| System | Methodology | KG | Cross-methodology synthesis | Patent draft |
|---|---|---|---|---|
| AutoTRIZ (2024) | TRIZ only | No | No | No |
| TRIZ Agents (2025) | TRIZ only | No | No | No |
| LLM+TRIZ Patent (2026) | TRIZ only | No | No | Yes |
| **IdeaForge** | TRIZ + DT + SCAMPER | **Yes** | **Yes** | **Yes (KG-grounded)** |

The key contribution is cross-methodology convergence detection via the CONVERGENT edge — finding claims that emerge independently from multiple methodologies, which are the strongest patent candidates.

---

## Note on TinyLlama

The framework is model-agnostic. TinyLlama (1.1B) produces basic outputs. Better results with larger models:

```bash
OLLAMA_MODEL=llama3.2 python ideaforge.py --idea "your idea"
OLLAMA_MODEL=mistral python ideaforge.py --idea "your idea"
```

---

## Citation

To be updated when published on arXiv.

```
Bose, J. IdeaForge: Cross-Methodology Convergent Novelty Detection
via Knowledge Graph for Automated Patent Claim Generation.
arXiv (forthcoming).
```
