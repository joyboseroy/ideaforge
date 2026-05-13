"""
mcp_server/server.py

MCP server exposing IdeaForge KG tools.

Tools:
    get_all_claims          — all claims in KG by strength
    get_convergent_claims   — cross-methodology convergent claims
    get_strongest_claims    — top 5 patent candidates
    get_kg_summary          — node count summary
    add_claim               — add a claim to the KG
    run_synthesis           — trigger convergence detection

Run: python mcp_server/server.py
"""

import sys
import os
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import mcp.server.stdio
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: pip install mcp")
    sys.exit(1)

from kg.graph import IdeaGraph

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("GRAPH_NAME", "ideaforge")

app = Server("ideaforge-server")


def get_graph() -> IdeaGraph:
    return IdeaGraph(
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
        graph_name=GRAPH_NAME,
    )


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_all_claims",
            description="Get all patent claims in the KG sorted by strength.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_convergent_claims",
            description=(
                "Get claims with cross-methodology convergent support. "
                "Higher convergent_count = stronger patent candidate. "
                "These are claims independently derived by multiple methodologies."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_strongest_claims",
            description="Get top 5 strongest patent candidates from the KG.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_kg_summary",
            description="Get node count summary of the idea knowledge graph.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="add_claim",
            description="Add a new patent claim to the KG.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Claim text"},
                    "methodology": {"type": "string", "description": "Source methodology"},
                    "claim_type": {"type": "string", "description": "independent or dependent"},
                    "strength": {"type": "number", "description": "0.0 to 1.0"},
                },
                "required": ["text", "methodology"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "get_all_claims":
        graph = get_graph()
        claims = graph.get_all_claims()
        return [TextContent(type="text", text=json.dumps(claims, indent=2))]

    elif name == "get_convergent_claims":
        graph = get_graph()
        claims = graph.get_convergent_claims()
        return [TextContent(type="text", text=json.dumps(claims, indent=2))]

    elif name == "get_strongest_claims":
        graph = get_graph()
        claims = graph.get_strongest_claims()
        return [TextContent(type="text", text=json.dumps(claims, indent=2))]

    elif name == "get_kg_summary":
        graph = get_graph()
        summary = graph.get_summary()
        return [TextContent(type="text", text=json.dumps(summary, indent=2))]

    elif name == "add_claim":
        graph = get_graph()
        claim_id = graph.add_claim(
            text=arguments["text"],
            methodology=arguments.get("methodology", "manual"),
            claim_type=arguments.get("claim_type", "independent"),
            strength=float(arguments.get("strength", 0.5)),
        )
        return [TextContent(
            type="text",
            text=json.dumps({"status": "added", "claim_id": claim_id})
        )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    print(
        f"IdeaForge MCP server starting...\n"
        f"FalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT}, graph: {GRAPH_NAME}\n",
        file=sys.stderr,
    )
    async with mcp.server.stdio.stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
