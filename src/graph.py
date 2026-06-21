import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.artist_metadata import enrich_artists

HUB_ARTIST = "Bon Iver"


def load_collaborations(path) -> pd.DataFrame:
    return pd.read_csv(path)


def graph_artists(collab_df: pd.DataFrame) -> list[str]:
    artists = set(collab_df["source_artist"]).union(set(collab_df["target_artist"]))
    return sorted(artists)


def build_adjacency_matrix(collab_df: pd.DataFrame) -> pd.DataFrame:
    artists = graph_artists(collab_df)
    matrix = pd.DataFrame(0, index=artists, columns=artists, dtype=int)

    grouped = (
        collab_df.groupby(["source_artist", "target_artist"])
        .size()
        .reset_index(name="weight")
    )

    for _, row in grouped.iterrows():
        source = row["source_artist"]
        target = row["target_artist"]
        weight = int(row["weight"])
        matrix.loc[source, target] += weight
        matrix.loc[target, source] += weight

    return matrix


def build_network(collab_df: pd.DataFrame, artists_df: pd.DataFrame) -> nx.Graph:
    genre_map = artists_df.set_index("artist_name")["main_genre"].to_dict()
    graph = nx.Graph()

    for artist in graph_artists(collab_df):
        graph.add_node(artist, main_genre=genre_map.get(artist, "unknown"))

    for _, row in collab_df.iterrows():
        source = row["source_artist"]
        target = row["target_artist"]
        track_title = row["track_title"]
        album = row["album"] if pd.notna(row.get("album")) else ""
        year = row["release_year"] if pd.notna(row.get("release_year")) else ""

        if graph.has_edge(source, target):
            graph[source][target]["tracks"].append(
                {"track_title": track_title, "album": album, "release_year": year}
            )
        else:
            graph.add_edge(
                source,
                target,
                tracks=[{"track_title": track_title, "album": album, "release_year": year}],
            )

    return graph


def _node_color(artist: str) -> str:
    if artist == HUB_ARTIST:
        return "#c0392b"
    return "#3498db"


def _node_size(artist: str, degree: int) -> float:
    if artist == HUB_ARTIST:
        return 28
    return 12 + min(degree * 2, 18)


def _format_year(year) -> str:
    if pd.isna(year) or year == "":
        return "unknown"
    return str(int(float(year)))


def draw_interactive_graph(
    graph: nx.Graph,
    output_path,
    hub_artist: str = HUB_ARTIST,
) -> None:
    positions = nx.spring_layout(graph, seed=42, k=1.8 / np.sqrt(max(len(graph.nodes), 1)))

    edge_mid_x, edge_mid_y, edge_hover = [], [], []
    edge_line_x, edge_line_y = [], []

    for source, target, data in graph.edges(data=True):
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_line_x.extend([x0, x1, None])
        edge_line_y.extend([y0, y1, None])

        track_lines = []
        for track in data["tracks"]:
            year = _format_year(track["release_year"])
            album = track["album"] or "unknown album"
            track_lines.append(f"{track['track_title']} ({year}) — {album}")

        edge_mid_x.append((x0 + x1) / 2)
        edge_mid_y.append((y0 + y1) / 2)
        edge_hover.append("<br>".join(track_lines))

    node_x = [positions[node][0] for node in graph.nodes]
    node_y = [positions[node][1] for node in graph.nodes]
    node_text = list(graph.nodes)
    node_hover = [
        f"<b>{node}</b><br>Main genre: {graph.nodes[node].get('main_genre', 'unknown')}"
        for node in graph.nodes
    ]
    node_colors = [_node_color(node) for node in graph.nodes]
    node_sizes = [_node_size(node, graph.degree[node]) for node in graph.nodes]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=edge_line_x,
            y=edge_line_y,
            mode="lines",
            line=dict(width=0.6, color="#b0b0b0"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=edge_mid_x,
            y=edge_mid_y,
            mode="markers",
            marker=dict(size=8, color="rgba(0,0,0,0)"),
            hoverinfo="text",
            hovertext=edge_hover,
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(size=node_sizes, color=node_colors, line=dict(width=1, color="#ffffff")),
            hoverinfo="text",
            hovertext=node_hover,
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Bon Iver Collaboration Network (2-hop, featured credits)",
        showlegend=False,
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#fafafa",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)


def build_graph_outputs(
    collaborations_path,
    edges_path,
    matrix_path,
    graph_path,
    artists_path,
    hub_artist: str = HUB_ARTIST,
) -> tuple[pd.DataFrame, pd.DataFrame, nx.Graph, pd.DataFrame]:
    collab_df = load_collaborations(collaborations_path)
    artists_df = enrich_artists(graph_artists(collab_df), cache_path=artists_path)

    matrix = build_adjacency_matrix(collab_df)
    graph = build_network(collab_df, artists_df)

    edges_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)

    collab_df.to_csv(edges_path, index=False)
    matrix.to_csv(matrix_path)
    artists_df.to_csv(artists_path, index=False)

    draw_interactive_graph(graph, graph_path, hub_artist=hub_artist)

    return collab_df, matrix, graph, artists_df
