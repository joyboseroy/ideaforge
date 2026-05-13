"""
visualize.py

Knowledge graph visualization for IdeaForge.

Generates an interactive HTML visualization using pyvis
and a static PNG using networkx + matplotlib.

Usage:
    python visualize.py                    # saves ideaforge_graph.html
    python visualize.py --static           # also saves ideaforge_graph.png
    python visualize.py --graph ideaforge  # specify graph name

The HTML visualization is the one to use in demos.
The PNG is for the paper figure.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from kg.graph import IdeaGraph

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    print("pyvis not available — pip install pyvis")

try:
    import networkx as nx
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False

# Node colours per type
NODE_COLORS = {
    "Problem":        "#e74c3c",   # red
    "Contradiction":  "#e67e22",   # orange
    "Principle":      "#f1c40f",   # yellow
    "UserNeed":       "#2ecc71",   # green
    "Transformation": "#1abc9c",   # teal
    "Analogy":        "#3498db",   # blue
    "PriorArt":       "#9b59b6",   # purple
    "Claim":          "#ecf0f1",   # white
}

NODE_SIZES = {
    "Problem":        40,
    "Contradiction":  25,
    "Principle":      25,
    "UserNeed":       20,
    "Transformation": 20,
    "Analogy":        20,
    "PriorArt":       20,
    "Claim":          30,
}

EDGE_COLORS = {
    "HAS_CONTRADICTION": "#e67e22",
    "RESOLVED_BY":       "#f1c40f",
    "MOTIVATES":         "#2ecc71",
    "SUPPORTS":          "#3498db",
    "INSPIRES":          "#1abc9c",
    "GENERATES":         "#9b59b6",
    "CHALLENGES":        "#e74c3c",
    "CONVERGENT":        "#ff69b4",  # pink — stands out
}


def fetch_graph_data(graph: IdeaGraph) -> tuple[list, list]:
    """Fetch all nodes and edges from FalkorDB."""
    nodes = []
    edges = []

    # Fetch nodes
    node_types = [
        "Problem", "Contradiction", "Principle",
        "UserNeed", "Transformation", "Analogy",
        "PriorArt", "Claim"
    ]

    # Property to use as label for each node type
    label_prop = {
        "Problem":        "statement",
        "Contradiction":  "improving",
        "Principle":      "name",
        "UserNeed":       "persona",
        "Transformation": "scamper_type",
        "Analogy":        "source_domain",
        "PriorArt":       "title",
        "Claim":          "text",
    }

    for node_type in node_types:
        prop = label_prop.get(node_type, "id")
        try:
            result = graph.graph.query(
                f"MATCH (n:{node_type}) RETURN n.id, n.{prop}"
            )
            for row in result.result_set:
                node_id = row[0] if row[0] else f"{node_type}_{len(nodes)}"
                raw_label = row[1] if row[1] else node_id
                nodes.append({
                    "id": node_id,
                    "label": str(raw_label)[:35],
                    "type": node_type,
                })
        except Exception as e:
            print(f"  [Visualize] Node query error ({node_type}): {e}")

    # Fetch edges
    edge_types = [
        ("HAS_CONTRADICTION", "Problem", "Contradiction"),
        ("RESOLVED_BY", "Contradiction", "Principle"),
        ("MOTIVATES", "UserNeed", "Problem"),
        ("SUPPORTS", "Principle", "Claim"),
        ("INSPIRES", "Analogy", "Claim"),
        ("GENERATES", "Transformation", "Claim"),
        ("CHALLENGES", "PriorArt", "Claim"),
        ("CONVERGENT", "Claim", "Claim"),
    ]

    for edge_type, from_type, to_type in edge_types:
        try:
            result = graph.graph.query(
                f"MATCH (a:{from_type})-[r:{edge_type}]->(b:{to_type}) "
                f"RETURN a.id AS from_id, b.id AS to_id"
            )
            for row in result.result_set:
                edges.append({
                    "from": row[0],
                    "to": row[1],
                    "type": edge_type,
                })
        except Exception:
            pass

    return nodes, edges


def visualize_pyvis(
    nodes: list,
    edges: list,
    output_file: str = "ideaforge_graph.html",
) -> None:
    """Generate interactive HTML visualization."""
    if not PYVIS_AVAILABLE:
        print("pyvis not available")
        return

    net = Network(
        height="750px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="white",
        directed=True,
    )

    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 150
        },
        "solver": "forceAtlas2Based"
      },
      "edges": {
        "arrows": {"to": {"enabled": true}},
        "smooth": {"type": "curvedCW", "roundness": 0.2}
      }
    }
    """)

    # Add nodes
    for node in nodes:
        color = NODE_COLORS.get(node["type"], "#cccccc")
        size = NODE_SIZES.get(node["type"], 20)
        net.add_node(
            node["id"],
            label=node["label"],
            color=color,
            size=size,
            title=f"{node['type']}: {node['label']}",
        )

    # Add edges
    for edge in edges:
        color = EDGE_COLORS.get(edge["type"], "#888888")
        width = 3 if edge["type"] == "CONVERGENT" else 1
        net.add_edge(
            edge["from"],
            edge["to"],
            color=color,
            width=width,
            title=edge["type"],
            label=edge["type"] if edge["type"] == "CONVERGENT" else "",
        )

    net.save_graph(output_file)
    print(f"Interactive graph saved: {output_file}")


def visualize_static(
    nodes: list,
    edges: list,
    output_file: str = "ideaforge_graph.png",
) -> None:
    """Generate static PNG for paper figure."""
    if not NX_AVAILABLE:
        print("networkx/matplotlib not available")
        return

    G = nx.DiGraph()

    for node in nodes:
        G.add_node(node["id"], node_type=node["type"], label=node["label"])

    for edge in edges:
        G.add_edge(edge["from"], edge["to"], edge_type=edge["type"])

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    pos = nx.spring_layout(G, k=2, seed=42)

    # Draw by node type
    for node_type, color in NODE_COLORS.items():
        node_list = [n for n, d in G.nodes(data=True) if d.get("node_type") == node_type]
        if node_list:
            size = NODE_SIZES.get(node_type, 20) * 20
            nx.draw_networkx_nodes(
                G, pos, nodelist=node_list,
                node_color=color, node_size=size,
                alpha=0.9, ax=ax
            )

    # Draw edges by type
    for edge_type, color in EDGE_COLORS.items():
        edge_list = [(u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == edge_type]
        if edge_list:
            width = 3 if edge_type == "CONVERGENT" else 1
            nx.draw_networkx_edges(
                G, pos, edgelist=edge_list,
                edge_color=color, width=width,
                alpha=0.8, arrows=True,
                arrowsize=15, ax=ax
            )

    # Labels
    labels = {n: d.get("label", n)[:15] for n, d in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, font_color="white", ax=ax)

    # Legend
    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=color, markersize=10, label=node_type)
        for node_type, color in NODE_COLORS.items()
    ]
    legend_elements.append(
        plt.Line2D([0], [0], color=EDGE_COLORS["CONVERGENT"],
                   linewidth=3, label="CONVERGENT edge")
    )
    ax.legend(handles=legend_elements, loc="upper left",
              facecolor="#2d2d4e", labelcolor="white", fontsize=8)

    ax.set_title("IdeaForge Knowledge Graph", color="white", fontsize=14, pad=20)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight",
                facecolor="#1a1a2e")
    plt.close()
    print(f"Static graph saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Visualize IdeaForge KG")
    parser.add_argument("--graph", default="ideaforge", help="Graph name")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=int(os.getenv("FALKORDB_PORT", "6379")))
    parser.add_argument("--output", default="ideaforge_graph.html")
    parser.add_argument("--static", action="store_true",
                        help="Also generate static PNG")
    args = parser.parse_args()

    graph = IdeaGraph(host=args.host, port=args.port, graph_name=args.graph)
    nodes, edges = fetch_graph_data(graph)

    print(f"Fetched {len(nodes)} nodes, {len(edges)} edges from KG")

    if not nodes:
        print("No data in graph. Run ideaforge.py first.")
        return

    visualize_pyvis(nodes, edges, args.output)

    if args.static:
        png_file = args.output.replace(".html", ".png")
        visualize_static(nodes, edges, png_file)


if __name__ == "__main__":
    main()
