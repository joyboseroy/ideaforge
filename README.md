# IdeaForge

**A Knowledge Graph-Grounded Multi-Agent Framework for Cross-Methodology Innovation Analysis and Patent Claim Generation**

Companion code for the paper:

**IdeaForge: A Knowledge Graph-Grounded Multi-Agent Framework for Cross-Methodology Innovation Analysis and Patent Claim Generation**
https://arxiv.org/abs/2605.13311

---

## What this is

Most AI innovation tools apply a single methodology (TRIZ, Design Thinking, or SCAMPER) in isolation and discard intermediate reasoning. IdeaForge is different:

1. Runs **multiple specialist agents** — TRIZ, Design Thinking, SCAMPER — each writing structured nodes and edges to a **persistent FalkorDB knowledge graph**
2. A **prior art agent** searches arXiv for related work and populates PriorArt nodes
3. An **embedding synthesis agent** uses sentence-transformer cosine similarity to detect claims independently derived by multiple methodologies — these are the strongest patent candidates
4. **InnovationScore** ranks all claims using a weighted formula combining convergence, diversity, strength, and prior art challenge count
5. A **patent agent** drafts structured claims grounded in the KG subgraph
6. A **visualizer** generates interactive HTML and static PNG graph images for demos and papers
7. An **MCP server** exposes KG tools to external agents

**The central novel contribution:** the `CONVERGENT` edge — connecting claims independently supported by multiple methodologies. Claims with high convergent count and methodology diversity are the strongest patent candidates.

---

## Architecture

```
Raw idea (text)
      |
      v
Problem node -> FalkorDB KG
      |
      +---> TRIZAgent              -> Contradiction, Principle, Claim nodes
      |
      +---> DesignThinkingAgent    -> UserNeed, Claim nodes
      |
      +---> SCAMPERAgent           -> Transformation, Claim nodes
      |
      +---> PriorArtAgent          -> PriorArt nodes (arXiv search)
      |
      v
EmbeddingSynthesisAgent            -> CONVERGENT edges (cosine similarity)
      |
      v
InnovationScore                    -> ranked claim list
      |
      v
PatentAgent                        -> Patent draft grounded in KG subgraph
      |
      v
MCP Server                         -> Exposes KG tools to external agents
Visualizer                         -> HTML + PNG graph image
```

---

## Knowledge Graph Schema

```
Nodes:
  Problem        (statement, domain)
  Contradiction  (improving, worsening)
  Principle      (name, triz_number, description)
  UserNeed       (persona, job_to_be_done, pain_level)
  Transformation (scamper_type, description)
  Analogy        (source_domain, mechanism) [reserved for future biomimicry agent]
  PriorArt       (title, source, similarity)
  Claim          (text, methodology, strength)

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

## InnovationScore

Claims are ranked by a weighted formula:

```
InnovationScore(c) = 0.4 * convergent_count
                   + 0.3 * methodology_diversity
                   + 0.2 * claim_strength
                   - 0.1 * prior_art_challenge_count
```

Where:
- `convergent_count` — CONVERGENT edges on this claim (cross-methodology support)
- `methodology_diversity` — distinct methodologies independently supporting the claim
- `claim_strength` — fixed by methodology: TRIZ=0.7, DesignThinking=0.65, SCAMPER=0.6
- `prior_art_challenge_count` — PriorArt nodes challenging this claim

The claim with highest InnovationScore becomes the primary independent claim in the patent draft.

---

## File structure

```
ideaforge/
├── kg/
│   ├── schema.py               # Node/edge types and Cypher templates
│   └── graph.py                # FalkorDB graph operations
├── agents/
│   ├── methodology_agents.py   # TRIZ, DesignThinking, SCAMPER agents
│   ├── prior_art_agent.py      # arXiv search -> PriorArt nodes
│   ├── embedding_synthesis.py  # Cosine similarity convergence detection
│   ├── innovation_score.py     # InnovationScore computation and ranking
│   └── patent_agent.py         # Patent claim drafting from KG
├── mcp_server/
│   └── server.py               # MCP server exposing KG tools
├── visualize.py                # pyvis HTML + networkx PNG graph visualization
├── run_experiments.py          # Multi-domain evaluation + threshold sensitivity
├── ideaforge.py                # Main pipeline entry point (8-step)
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

### Run the full pipeline

```bash
python ideaforge.py --idea "A voice-first legal assistant in Hindi for rural India"
```

### Save patent draft + visualize

```bash
python ideaforge.py \
  --idea "A voice-first legal assistant in Hindi for rural India" \
  --domain "legal technology" \
  --output patent_draft.txt

python visualize.py --static
```

### Dry run (no Ollama needed)

```bash
python ideaforge.py --idea "your idea" --dry-run
```

### Use a better model

```bash
OLLAMA_MODEL=llama3.2 python ideaforge.py --idea "your idea"
OLLAMA_MODEL=mistral python ideaforge.py --idea "your idea"
```

### Reproduce paper experiments

```bash
FALKORDB_PORT=6380 python run_experiments.py
```

---

## Pipeline steps

```
Step 1: Ingest idea into knowledge graph
Step 2: TRIZ contradiction analysis
Step 3: Design Thinking user needs analysis
Step 4: SCAMPER transformations
Step 5: Prior art search (arXiv)
Step 6: Embedding-based convergence detection
Step 7: InnovationScore ranking
Step 8: Patent draft from KG subgraph
```

---

## Example output (actual results, legal technology use case)

```
InnovationScore Report
============================================================
Rank  Score    Conv   Div   PA    Claim
------------------------------------------------------------
1     0.500    2      2     0     [TRIZ] A method for resolving the contradiction
                                  between accessibility and complexity of legal
                                  language, applying Segmentation and Preliminary
                                  Action principles to voice-based delivery
2     0.310    1      1     0     [DesignThinking] A user-centred system enabling
                                  rural citizens to query legal rights in Hindi
                                  via voice, without needing a lawyer
3     0.220    0      1     0     [SCAMPER] A transformed approach substituting
                                  text-based legal interfaces with voice-first
                                  interaction, adapting medical triage dialogue
                                  patterns to legal question routing

Convergent pairs detected: 3
  TRIZ + DesignThinking: 0.837
  TRIZ + SCAMPER:        0.817
  DesignThinking + SCAMPER: 0.819

Knowledge Graph: 16 nodes, 10 edges
```

---

## Multi-domain results (from paper)

| Use Case | Domain | Nodes | Conv. pairs | Top score |
|---|---|---|---|---|
| Voice-first legal assistant (Hindi) | Legal tech | 16 | 3 | 0.500 |
| Sepsis early warning (wearables) | Healthcare | 16 | 1 | 0.353 |
| Adaptive tutoring for dyscalculia | EdTech | 16 | 3 | 0.500 |
| Drone crop disease detection | Agriculture | 16 | 3 | 0.467 |
| Sign language interpretation | Accessibility | 16 | 3 | 0.500 |

---

## Visualization

```bash
# Interactive HTML (for demos)
python visualize.py

# Static PNG (for paper figure)
python visualize.py --static
```

CONVERGENT edges are shown in pink — they are the visual centrepiece of the graph and the paper's core contribution.

---

## MCP server tools

| Tool | Description |
|---|---|
| `get_all_claims` | All claims sorted by strength |
| `get_convergent_claims` | Claims with cross-methodology support |
| `get_strongest_claims` | Top 5 patent candidates |
| `get_kg_summary` | Node count summary |
| `add_claim` | Add a claim to the KG |

```bash
python mcp_server/server.py
```

---

## Why this is different from existing work

| System | Methodology | Persistent KG | Cross-methodology synthesis | InnovationScore | Patent draft |
|---|---|---|---|---|---|
| AutoTRIZ (2024) | TRIZ only | No | No | No | No |
| TRIZ Agents (ICAART 2025) | TRIZ only | No | No | No | No |
| LLM+TRIZ Patent (2026) | TRIZ only | No | No | No | Yes |
| **IdeaForge** | TRIZ + DT + SCAMPER | **Yes** | **Yes (embeddings)** | **Yes** | **Yes (KG-grounded)** |

The central argument: innovation methodologies can be interpreted as heterogeneous reasoning operators acting over a shared persistent innovation graph. Cross-methodology convergence — the same claim emerging independently from multiple operators — is a principled signal of non-obviousness.

---

## Limitations

- LLM quality affects agent outputs — TinyLlama produces basic results; larger models produce richer claims
- Convergence detection uses semantic similarity, not true logical equivalence
- Prior art search is limited to arXiv — patent database integration is future work
- No legal validation — this is a research prototype, not a patent filing tool
- InnovationScore weights are heuristic — formal novelty cannot be guaranteed

---

## Citation

```bibtex
@article{bose2026ideaforge,
  title={IdeaForge: A Knowledge Graph-Grounded Multi-Agent Framework for Cross-Methodology Innovation Analysis and Patent Claim Generation},
  author={Bose, Joy},
  journal={arXiv preprint arXiv:2605.13311},
  year={2026}
}
```
