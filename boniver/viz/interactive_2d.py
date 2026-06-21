from __future__ import annotations

from pathlib import Path

import networkx as nx
import plotly.graph_objects as go

from boniver.config import OUTPUT_DIR


def render_interactive_2d(
    graph: nx.Graph,
    output_path: Path | None = None,
    title: str = "Bon Iver Collaboration Network (Interactive 2D)",
) -> Path:
    """Interactive 2D graph — a stepping stone before the 3D view."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = output_path or OUTPUT_DIR / "collaboration_graph_2d.html"

    layout = nx.spring_layout(graph, seed=42, weight="weight")
    edge_x, edge_y = [], []
    edge_hover: list[str] = []

    for source, target, data in graph.edges(data=True):
        x0, y0 = layout[source]
        x1, y1 = layout[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        songs = data.get("songs", [])
        label = f"{source} ↔ {target} (×{data.get('weight', 1)})"
        if songs:
            label += "<br>" + "<br>".join(songs[:6])
        edge_hover.append(label)

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.5, color="#8899A6"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
    for node in graph.nodes:
        x, y = layout[node]
        attrs = graph.nodes[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(
            f"<b>{node}</b><br>Songs: {attrs.get('song_count', 0)}"
        )
        node_size.append(26 if attrs.get("is_bon_iver") else 14 + attrs.get("song_count", 1))
        node_color.append("#E4572E" if attrs.get("is_bon_iver") else "#4E8098")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[node for node in graph.nodes],
        textposition="top center",
        hovertext=node_text,
        hoverinfo="text",
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color="#FFFFFF")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor="#0F1115",
        plot_bgcolor="#0F1115",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    fig.write_html(out, include_plotlyjs="cdn", full_html=True)
    return out
