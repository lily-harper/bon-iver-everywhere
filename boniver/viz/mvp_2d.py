from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from boniver.config import OUTPUT_DIR


def _node_sizes(graph: nx.Graph) -> list[float]:
    sizes = []
    for node in graph.nodes:
        if graph.nodes[node].get("is_bon_iver"):
            sizes.append(1200)
        else:
            sizes.append(300 + graph.nodes[node].get("song_count", 1) * 120)
    return sizes


def _node_colors(graph: nx.Graph) -> list[str]:
    colors = []
    for node in graph.nodes:
        if graph.nodes[node].get("is_bon_iver"):
            colors.append("#E4572E")
        else:
            colors.append("#4E8098")
    return colors


def _edge_widths(graph: nx.Graph) -> list[float]:
    return [1.0 + graph[u][v].get("weight", 1) * 1.5 for u, v in graph.edges]


def render_2d(
    graph: nx.Graph,
    output_path: Path | None = None,
    title: str = "Bon Iver Collaboration Network (2D MVP)",
    show_labels: bool = True,
) -> Path:
    """Static 2D matplotlib visualization — fastest MVP."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = output_path or OUTPUT_DIR / "collaboration_graph_2d.png"

    layout = nx.spring_layout(graph, seed=42, k=1.4, weight="weight")

    fig, ax = plt.subplots(figsize=(14, 10), facecolor="#0F1115")
    ax.set_facecolor("#0F1115")

    nx.draw_networkx_edges(
        graph,
        layout,
        ax=ax,
        width=_edge_widths(graph),
        edge_color="#6C7A89",
        alpha=0.65,
    )
    nx.draw_networkx_nodes(
        graph,
        layout,
        ax=ax,
        node_size=_node_sizes(graph),
        node_color=_node_colors(graph),
        alpha=0.95,
    )

    if show_labels:
        labels = {node: node for node in graph.nodes}
        nx.draw_networkx_labels(
            graph,
            layout,
            labels=labels,
            font_size=9,
            font_color="#F5F5F5",
            ax=ax,
        )

    ax.set_title(title, color="#F5F5F5", fontsize=16, pad=16)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out
