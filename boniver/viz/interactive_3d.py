from __future__ import annotations

from pathlib import Path

import networkx as nx
import plotly.graph_objects as go

from boniver.config import OUTPUT_DIR


def _spring_layout_3d(graph: nx.Graph, seed: int = 42) -> dict[str, tuple[float, float, float]]:
    """Project a 2D spring layout into 3D using node metrics as the z-axis."""
    layout_2d = nx.spring_layout(graph, seed=seed, dim=2, weight="weight")
    positions: dict[str, tuple[float, float, float]] = {}
    for node in graph.nodes:
        x, y = layout_2d[node]
        z = float(graph.nodes[node].get("song_count", 1)) * 0.15
        if graph.nodes[node].get("is_bon_iver"):
            z += 0.5
        positions[node] = (float(x), float(y), z)
    return positions


def render_interactive_3d(
    graph: nx.Graph,
    output_path: Path | None = None,
    title: str = "Bon Iver Collaboration Network (Interactive 3D)",
) -> Path:
    """Interactive 3D graph exported as a standalone HTML file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = output_path or OUTPUT_DIR / "collaboration_graph_3d.html"

    positions = _spring_layout_3d(graph)
    node_x, node_y, node_z, node_text, node_size, node_color = [], [], [], [], [], []

    for node in graph.nodes:
        x, y, z = positions[node]
        attrs = graph.nodes[node]
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        node_text.append(
            f"<b>{node}</b><br>"
            f"Songs: {attrs.get('song_count', 0)}<br>"
            f"Roles: {', '.join(attrs.get('roles', [])) or 'n/a'}"
        )
        node_size.append(18 if attrs.get("is_bon_iver") else 10 + attrs.get("song_count", 1) * 2)
        node_color.append("#E4572E" if attrs.get("is_bon_iver") else "#76B7B2")

    edge_x, edge_y, edge_z, edge_hover = [], [], [], []
    for source, target, data in graph.edges(data=True):
        x0, y0, z0 = positions[source]
        x1, y1, z1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])
        songs = data.get("songs", [])
        hover = f"{source} ↔ {target}<br>Weight: {data.get('weight', 1)}"
        if songs:
            hover += "<br>Songs: " + ", ".join(songs[:5])
            if len(songs) > 5:
                hover += f" (+{len(songs) - 5} more)"
        edge_hover.append(hover)

    edge_trace = go.Scatter3d(
        x=edge_x,
        y=edge_y,
        z=edge_z,
        mode="lines",
        line=dict(color="#AAB7C4", width=3),
        hoverinfo="skip",
        name="collaborations",
    )

    node_trace = go.Scatter3d(
        x=node_x,
        y=node_y,
        z=node_z,
        mode="markers+text",
        text=[node for node in graph.nodes],
        textposition="top center",
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(width=1, color="#FFFFFF"),
            opacity=0.95,
        ),
        hovertext=node_text,
        hoverinfo="text",
        name="artists",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=dict(text=title, x=0.5),
        template="plotly_dark",
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(title="collaboration depth"),
            bgcolor="#0F1115",
        ),
        paper_bgcolor="#0F1115",
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
    )
    fig.write_html(out, include_plotlyjs="cdn", full_html=True)
    return out
