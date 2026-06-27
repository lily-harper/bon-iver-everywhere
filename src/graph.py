import json
import math

import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.artist_metadata import enrich_artists

HUB_ARTIST = "Bon Iver"
HOP1_EDGE_COLOR = "#e74c3c"
HOP2_EDGE_COLOR = "#95a5a6"
HUB_NODE_COLOR = "#c0392b"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Bon Iver Collaboration Network</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #111; color: #eee; }}
    #layout {{ display: flex; height: 100vh; }}
    #plot-wrap {{ flex: 1; min-width: 0; }}
    #panel {{
      width: 360px; padding: 20px; background: #1a1a1a; border-left: 1px solid #333;
      overflow-y: auto; box-sizing: border-box;
    }}
    #panel h2 {{ margin: 0 0 8px; font-size: 1.1rem; }}
    #panel .subtitle {{ color: #aaa; font-size: 0.85rem; margin-bottom: 16px; }}
    #panel .empty {{ color: #888; font-style: italic; }}
    .track {{ margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #333; }}
    .track-title {{ font-weight: 600; }}
    .track-meta {{ color: #aaa; font-size: 0.85rem; margin-top: 4px; }}
    .path-step {{ margin-bottom: 10px; padding: 8px; background: #222; border-radius: 6px; }}
    .path-step strong {{ color: #e74c3c; }}
    .legend {{ margin-top: 20px; font-size: 0.8rem; color: #aaa; }}
    .legend span {{ display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: middle; }}
  </style>
</head>
<body>
  <div id="layout">
    <div id="plot-wrap">{plot}</div>
    <div id="panel">
      <h2 id="panel-title">Select a node</h2>
      <div class="subtitle" id="panel-subtitle">Click an artist to see their connection to Bon Iver.</div>
      <div id="panel-body" class="empty">No artist selected.</div>
      <div class="legend">
        <p><span style="background:{hop1}"></span> 1 hop from Bon Iver</p>
        <p><span style="background:{hop2}"></span> 2 hops from Bon Iver</p>
        <p>Node color = main genre</p>
      </div>
    </div>
  </div>
  <script>
    const HUB = {hub_json};
    const CLICK_DATA = {data_json};

    function escapeHtml(text) {{
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }}

    function renderTrack(track) {{
      const year = track.year || "unknown year";
      const album = track.album || "unknown album";
      const role = track.role || "collaborator";
      const relation = track.relation || "";
      return `
        <div class="track">
          <div class="track-title">${{escapeHtml(track.track)}}</div>
          <div class="track-meta">${{escapeHtml(relation)}}</div>
          <div class="track-meta">Role: ${{escapeHtml(role)}} · ${{escapeHtml(year)}} · ${{escapeHtml(album)}}</div>
        </div>`;
    }}

    function renderPath(steps) {{
      return steps.map(step => {{
        const tracks = step.tracks.map(t =>
          `<div class="track-meta">· ${{escapeHtml(t.track)}} (${{escapeHtml(t.role)}})</div>`
        ).join("");
        return `<div class="path-step"><strong>${{escapeHtml(step.from)}}</strong> → <strong>${{escapeHtml(step.to)}}</strong>${{tracks}}</div>`;
      }}).join("");
    }}

    function showArtist(name) {{
      const info = CLICK_DATA[name];
      const title = document.getElementById("panel-title");
      const subtitle = document.getElementById("panel-subtitle");
      const body = document.getElementById("panel-body");

      if (!info) {{
        title.textContent = name;
        subtitle.textContent = "No data available.";
        body.innerHTML = '<div class="empty">No collaboration data found.</div>';
        return;
      }}

      title.textContent = name;
      if (info.direct && info.direct.length) {{
        subtitle.textContent = "Direct collaborator · " + (info.genre || "unknown genre");
      }} else if (info.path && info.path.length) {{
        subtitle.textContent = (info.path.length + 1) + " hops from Bon Iver · " + (info.genre || "unknown genre");
      }} else {{
        subtitle.textContent = info.genre ? "Main genre: " + info.genre : "";
      }}

      let html = "";
      if (info.direct && info.direct.length) {{
        html += "<h3>Collaborations with Bon Iver</h3>";
        html += info.direct.map(renderTrack).join("");
      }} else {{
        html += "<p class='empty'>No direct Bon Iver collaborations in this dataset.</p>";
      }}

      if (info.path && info.path.length) {{
        html += "<h3>How they're connected</h3>";
        html += renderPath(info.path);
      }}

      body.innerHTML = html || '<div class="empty">No connection found.</div>';
    }}

    const plotDiv = document.getElementById("collab-graph");
    plotDiv.on("plotly_click", function(event) {{
      if (!event.points || !event.points.length) return;
      const point = event.points[0];
      if (point.customdata) showArtist(point.customdata);
    }});
  </script>
</body>
</html>
"""


def load_collaborations(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "role" not in df.columns:
        df["role"] = "featured"
    return df


def graph_artists(collab_df: pd.DataFrame) -> list[str]:
    artists = set(collab_df["source_artist"]).union(set(collab_df["target_artist"]))
    return sorted(artists)


def dedupe_collaborations(collab_df: pd.DataFrame) -> pd.DataFrame:
    if collab_df.empty:
        return collab_df

    return (
        collab_df.sort_values(["track_title", "release_year"], na_position="last")
        .drop_duplicates(
            subset=["track_title", "source_artist", "target_artist", "role"],
            keep="first",
        )
        .reset_index(drop=True)
    )


def build_adjacency_matrix(collab_df: pd.DataFrame) -> pd.DataFrame:
    pair_df = aggregate_artist_pairs(collab_df)
    artists = graph_artists(collab_df)
    matrix = pd.DataFrame(0, index=artists, columns=artists, dtype=int)

    for _, row in pair_df.iterrows():
        source = row["source_artist"]
        target = row["target_artist"]
        weight = int(row["weight"])
        matrix.loc[source, target] = weight
        matrix.loc[target, source] = weight

    return matrix


def aggregate_artist_pairs(collab_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        collab_df.groupby(["source_artist", "target_artist"])
        .agg(
            weight=("track_title", "nunique"),
            tracks=("track_title", lambda titles: "; ".join(sorted(set(titles)))),
        )
        .reset_index()
    )
    return grouped


def _format_year(year) -> str:
    if pd.isna(year) or year == "":
        return "unknown"
    return str(int(float(year)))


def _track_record(row) -> dict:
    source = row["source_artist"]
    target = row["target_artist"]
    role = row.get("role", "featured")

    if source == HUB_ARTIST:
        relation = f"Bon Iver (primary) · {target} ({role})"
    elif target == HUB_ARTIST:
        relation = f"{source} (primary) · Bon Iver ({role})"
    else:
        relation = f"{source} (primary) · {target} ({role})"

    return {
        "track": row["track_title"],
        "album": row["album"] if pd.notna(row.get("album")) else "",
        "year": _format_year(row.get("release_year")),
        "role": role,
        "relation": relation,
    }


def _edge_tracks(collab_df: pd.DataFrame, source: str, target: str) -> list[dict]:
    mask = (
        (collab_df["source_artist"] == source) & (collab_df["target_artist"] == target)
    ) | (
        (collab_df["source_artist"] == target) & (collab_df["target_artist"] == source)
    )
    return [_track_record(row) for _, row in collab_df[mask].iterrows()]


def build_click_data(
    collab_df: pd.DataFrame,
    graph: nx.Graph,
    genre_map: dict[str, str],
    hub_artist: str = HUB_ARTIST,
) -> dict:
    click_data = {}

    for artist in graph.nodes:
        direct_rows = collab_df[
            (
                (collab_df["source_artist"] == hub_artist)
                & (collab_df["target_artist"] == artist)
            )
            | (
                (collab_df["source_artist"] == artist)
                & (collab_df["target_artist"] == hub_artist)
            )
        ]

        direct = [_track_record(row) for _, row in direct_rows.iterrows()]

        path_steps = []
        if artist != hub_artist and nx.has_path(graph, hub_artist, artist):
            path = nx.shortest_path(graph, hub_artist, artist)
            if len(path) > 2:
                for index in range(len(path) - 1):
                    source = path[index]
                    target = path[index + 1]
                    path_steps.append(
                        {
                            "from": source,
                            "to": target,
                            "tracks": _edge_tracks(collab_df, source, target)[:5],
                        }
                    )

        click_data[artist] = {
            "genre": genre_map.get(artist, "unknown"),
            "direct": direct,
            "path": path_steps,
        }

    return click_data


def build_network(collab_df: pd.DataFrame, artists_df: pd.DataFrame) -> nx.Graph:
    genre_map = artists_df.set_index("artist_name")["main_genre"].to_dict()
    graph = nx.Graph()

    for artist in graph_artists(collab_df):
        graph.add_node(artist, main_genre=genre_map.get(artist, "unknown"))

    pair_df = aggregate_artist_pairs(collab_df)
    for _, row in pair_df.iterrows():
        tracks = _edge_tracks(collab_df, row["source_artist"], row["target_artist"])
        graph.add_edge(
            row["source_artist"],
            row["target_artist"],
            weight=int(row["weight"]),
            tracks=tracks,
        )

    return graph


def _genre_color_map(artists_df: pd.DataFrame) -> dict[str, str]:
    genres = sorted(artists_df["main_genre"].fillna("unknown").unique())
    palette = px.colors.qualitative.Alphabet + px.colors.qualitative.Dark24
    return {genre: palette[index % len(palette)] for index, genre in enumerate(genres)}


def _layout_3d(graph: nx.Graph, hub_artist: str = HUB_ARTIST) -> dict:
    positions = nx.spring_layout(graph, dim=3, seed=42, k=1.2 / math.sqrt(max(len(graph.nodes), 1)))
    if hub_artist in positions:
        positions[hub_artist] = np.array([0.0, 0.0, 0.0])
    return positions


def _node_size(artist: str, degree: int) -> float:
    if artist == HUB_ARTIST:
        return 14
    return 6 + min(degree, 8)


def _edge_hover_text(tracks: list[dict]) -> str:
    lines = []
    for track in tracks[:8]:
        album = track["album"] or "unknown album"
        lines.append(
            f"{track['track']} ({track['year']}) — {album}<br>Role: {track['role']}"
        )
    if len(tracks) > 8:
        lines.append(f"... +{len(tracks) - 8} more")
    return "<br>".join(lines)


def _add_edge_trace(fig, positions, edges, color, name, width=2):
    x_lines, y_lines, z_lines = [], [], []
    hover_x, hover_y, hover_z, hover_text = [], [], [], []

    for source, target, data in edges:
        x0, y0, z0 = positions[source]
        x1, y1, z1 = positions[target]
        x_lines.extend([x0, x1, None])
        y_lines.extend([y0, y1, None])
        z_lines.extend([z0, z1, None])

        hover_x.append((x0 + x1) / 2)
        hover_y.append((y0 + y1) / 2)
        hover_z.append((z0 + z1) / 2)
        hover_text.append(_edge_hover_text(data.get("tracks", [])))

    fig.add_trace(
        go.Scatter3d(
            x=x_lines,
            y=y_lines,
            z=z_lines,
            mode="lines",
            line=dict(color=color, width=width),
            hoverinfo="skip",
            name=name,
            showlegend=True,
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=hover_x,
            y=hover_y,
            z=hover_z,
            mode="markers",
            marker=dict(size=2, color="rgba(0,0,0,0)"),
            hoverinfo="text",
            hovertext=hover_text,
            name=f"{name} (tracks)",
            showlegend=False,
        )
    )


def draw_interactive_graph(
    graph: nx.Graph,
    output_path,
    click_data: dict,
    genre_colors: dict[str, str],
    hub_artist: str = HUB_ARTIST,
) -> None:
    positions = _layout_3d(graph, hub_artist=hub_artist)

    hop1_edges = []
    hop2_edges = []
    for source, target, data in graph.edges(data=True):
        if hub_artist in (source, target):
            hop1_edges.append((source, target, data))
        else:
            hop2_edges.append((source, target, data))

    fig = go.Figure()
    _add_edge_trace(fig, positions, hop2_edges, HOP2_EDGE_COLOR, "2 hops from Bon Iver", width=1.5)
    _add_edge_trace(fig, positions, hop1_edges, HOP1_EDGE_COLOR, "1 hop from Bon Iver", width=3)

    node_names = list(graph.nodes)
    node_x = [positions[name][0] for name in node_names]
    node_y = [positions[name][1] for name in node_names]
    node_z = [positions[name][2] for name in node_names]
    node_colors = [
        HUB_NODE_COLOR
        if name == hub_artist
        else genre_colors.get(graph.nodes[name].get("main_genre", "unknown"), "#888888")
        for name in node_names
    ]
    node_sizes = [_node_size(name, graph.degree[name]) for name in node_names]
    node_hover = [
        f"<b>{name}</b><br>Genre: {graph.nodes[name].get('main_genre', 'unknown')}<br>Click for Bon Iver details"
        for name in node_names
    ]

    fig.add_trace(
        go.Scatter3d(
            x=node_x,
            y=node_y,
            z=node_z,
            mode="markers+text",
            text=node_names,
            textposition="top center",
            textfont=dict(size=8, color="#dddddd"),
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=0.5, color="#ffffff"),
            ),
            hovertext=node_hover,
            hoverinfo="text",
            customdata=node_names,
            name="Artists",
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Bon Iver Collaboration Network (3D · 2-hop featured credits)",
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.5)", font=dict(color="white")),
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#111111",
        ),
        paper_bgcolor="#111111",
        font=dict(color="#eeeeee"),
        margin=dict(l=0, r=0, t=50, b=0),
    )

    plot_html = fig.to_html(include_plotlyjs="cdn", div_id="collab-graph", full_html=False)
    html = HTML_TEMPLATE.format(
        plot=plot_html,
        hop1=HOP1_EDGE_COLOR,
        hop2=HOP2_EDGE_COLOR,
        hub_json=json.dumps(hub_artist),
        data_json=json.dumps(click_data),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def build_graph_outputs(
    collaborations_path,
    edges_path,
    matrix_path,
    graph_path,
    artists_path,
    hub_artist: str = HUB_ARTIST,
) -> tuple[pd.DataFrame, pd.DataFrame, nx.Graph, pd.DataFrame]:
    collab_df = dedupe_collaborations(load_collaborations(collaborations_path))
    artists_df = enrich_artists(graph_artists(collab_df), cache_path=artists_path)
    genre_map = artists_df.set_index("artist_name")["main_genre"].to_dict()
    genre_colors = _genre_color_map(artists_df)

    matrix = build_adjacency_matrix(collab_df)
    graph = build_network(collab_df, artists_df)
    click_data = build_click_data(collab_df, graph, genre_map, hub_artist=hub_artist)

    edges_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)

    collab_df.to_csv(edges_path, index=False)
    matrix.to_csv(matrix_path)
    artists_df.to_csv(artists_path, index=False)

    draw_interactive_graph(
        graph,
        graph_path,
        click_data=click_data,
        genre_colors=genre_colors,
        hub_artist=hub_artist,
    )

    return collab_df, matrix, graph, artists_df
