import json
import math
from html import escape

import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.artist_metadata import enrich_artists

HUB_ARTIST = "Bon Iver"
HOP1_EDGE_COLOR = "#e74c3c"
HOP2_EDGE_COLOR = "#95a5a6"
HUB_NODE_COLOR = "#c0392b"

DISPLAY_GENRE_COLORS = {
    "Hip-hop / Rap": "#E45756",
    "R&B / Soul": "#B279A2",
    "Pop": "#F2CF5B",
    "Rock / Alternative": "#4C78A8",
    "Folk / Country": "#59A14F",
    "Electronic / Dance": "#76B7B2",
    "Jazz / Classical": "#FF9DA7",
    "Global / Reggae": "#F28E2B",
    "Experimental / Soundtrack": "#9C755F",
    "Other / Unknown": "#79706E",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Bon Iver Collaboration Network</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #111; color: #eee; }}
    #layout {{ height: 100vh; }}
    #plot-wrap {{ width: calc(100vw - 320px); height: 100vh; overflow: hidden; }}
    #panel {{
      position: fixed; z-index: 1000; top: 0; right: 0; bottom: 0;
      width: 320px; padding: 20px; background: #1a1a1a; border-left: 1px solid #333;
      overflow-y: auto; box-sizing: border-box; contain: layout paint;
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
    #reset-view {{ background: #2b2b2b; color: #eee; border: 1px solid #555; border-radius: 5px; padding: 7px 10px; cursor: pointer; }}
    #reset-view:hover {{ background: #3a3a3a; }}
    .controls {{ display: flex; gap: 8px; margin-bottom: 10px; }}
    .genre-key {{ display: grid; grid-template-columns: 14px 1fr; gap: 6px 8px; align-items: center; }}
    .genre-key span {{ width: 12px; height: 12px; border-radius: 50%; }}
    .genre-legend {{
      position: sticky; z-index: 2; top: -20px; margin: 0 -20px 16px; padding: 12px 20px;
      background: #1a1a1a; border-bottom: 1px solid #333;
    }}
    .genre-legend h3 {{ margin: 0 0 8px; color: #eee; }}
    @media (max-width: 760px) {{
      #plot-wrap {{ width: 100vw; height: 70vh; }}
      #panel {{ position: absolute; top: 70vh; width: 100%; min-height: 30vh; border-left: 0; border-top: 1px solid #333; }}
      .genre-legend {{ position: relative; top: auto; }}
    }}
  </style>
</head>
<body>
  <div id="layout">
    <div id="plot-wrap">{plot}</div>
    <div id="panel">
      <h2 id="panel-title">Select a node</h2>
      <div class="subtitle" id="panel-subtitle">Click an artist to see their connection to Bon Iver.</div>
      <div class="controls">
        <button id="reset-view" type="button">Reset view</button>
      </div>
      <p class="subtitle">Drag to rotate. Use the wheel or trackpad to zoom quickly.</p>
      <div class="legend genre-legend">
        <h3>Node colors</h3>
        <div class="genre-key">{genre_legend}</div>
        <p>First-hop line width = number of shared recordings. Line length increases with the collaborator's downstream connections.</p>
        <p>Use the graph legend to independently show or hide connection lines and node layers.</p>
      </div>
      <div id="panel-body" class="empty">No artist selected.</div>
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
        subtitle.textContent = "Direct collaborator · " + (info.display_genre || "Other / Unknown");
      }} else if (info.path && info.path.length) {{
        subtitle.textContent = (info.path.length + 1) + " hops from Bon Iver · " + (info.display_genre || "Other / Unknown");
      }} else {{
        subtitle.textContent = info.display_genre ? "Genre: " + info.display_genre : "";
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
    const INITIAL_CAMERA = {{ eye: {{ x: 1.25, y: 1.25, z: 1.0 }} }};
    let currentCamera = INITIAL_CAMERA;

    plotDiv.on("plotly_relayout", function(update) {{
      if (update["scene.camera"]) currentCamera = update["scene.camera"];
    }});

    plotDiv.addEventListener("wheel", function(event) {{
      event.preventDefault();
      const eye = (currentCamera && currentCamera.eye) || INITIAL_CAMERA.eye;
      const distance = Math.hypot(eye.x, eye.y, eye.z);
      const amount = Math.min(Math.abs(event.deltaY), 40);
      const factor = Math.exp(Math.sign(event.deltaY) * amount * 0.012);
      const nextDistance = Math.max(0.35, Math.min(8, distance * factor));
      const scale = nextDistance / distance;
      const nextCamera = {{
        ...currentCamera,
        eye: {{ x: eye.x * scale, y: eye.y * scale, z: eye.z * scale }}
      }};
      currentCamera = nextCamera;
      Plotly.relayout(plotDiv, {{ "scene.camera": nextCamera }});
    }}, {{ passive: false }});

    document.getElementById("reset-view").addEventListener("click", function() {{
      currentCamera = INITIAL_CAMERA;
      Plotly.relayout(plotDiv, {{ "scene.camera": INITIAL_CAMERA }});
    }});

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
            "display_genre": collapse_genre(genre_map.get(artist, "unknown")),
            "direct": direct,
            "path": path_steps,
        }

    return click_data


def collapse_genre(genre: str) -> str:
    value = str(genre or "").strip().casefold()
    if not value or value in {"unknown", "none", "nan", "person", "group", "other"}:
        return "Other / Unknown"

    categories = (
        ("Hip-hop / Rap", ("hip hop", "hip-hop", "rap", "trap", "drill", "boom bap", "horrorcore")),
        ("R&B / Soul", ("r&b", "rnb", "soul", "funk")),
        ("Folk / Country", ("folk", "country", "americana", "bluegrass", "old-time", "celtic", "fiddling", "western")),
        ("Electronic / Dance", ("electronic", "electronica", "dance", "house", "edm", "trance", "ambient", "downtempo", "trip-hop", "synth", "electro", "chillwave")),
        ("Pop", ("pop", "bedroom")),
        ("Rock / Alternative", ("rock", "indie", "alternative", "metal", "psychedelia")),
        ("Jazz / Classical", ("jazz", "classical", "composer", "swing", "blues", "choir", "gospel")),
        ("Global / Reggae", ("reggae", "dancehall", "afrobeat", "latin", "mexicano", "k-pop", "v-pop")),
        ("Experimental / Soundtrack", ("experimental", "soundtrack", "production music", "new age")),
    )
    for category, terms in categories:
        if any(term in value for term in terms):
            return category
    return "Other / Unknown"


def build_network(collab_df: pd.DataFrame, artists_df: pd.DataFrame) -> nx.Graph:
    genre_map = artists_df.set_index("artist_name")["main_genre"].to_dict()
    graph = nx.Graph()

    for artist in graph_artists(collab_df):
        raw_genre = genre_map.get(artist, "unknown")
        graph.add_node(
            artist,
            main_genre=raw_genre,
            display_genre=collapse_genre(raw_genre),
        )

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
    return DISPLAY_GENRE_COLORS.copy()


def _layout_3d(graph: nx.Graph, hub_artist: str = HUB_ARTIST) -> dict:
    positions = nx.spring_layout(
        graph,
        dim=3,
        seed=42,
        k=3.0 / math.sqrt(max(len(graph.nodes), 1)),
        iterations=200,
        scale=2.5,
    )
    if hub_artist in positions:
        hub_position = positions[hub_artist].copy()
        positions = {name: position - hub_position for name, position in positions.items()}
        first_hop = set(graph.neighbors(hub_artist))
        positions[hub_artist] = np.array([0.0, 0.0, 0.0])

        for name in first_hop:
            position = positions[name]
            distance = np.linalg.norm(position)
            if distance == 0:
                continue
            downstream_connections = graph.degree[name] - 1
            branch_spacing = min(
                2.2,
                math.log1p(max(downstream_connections, 0)) * 0.45,
            )
            positions[name] = position / distance * (2.4 + branch_spacing)

        for name in set(graph) - first_hop - {hub_artist}:
            position = positions[name]
            distance = np.linalg.norm(position)
            if distance == 0:
                continue
            parent_radii = [
                np.linalg.norm(positions[neighbor])
                for neighbor in graph.neighbors(name)
                if neighbor in first_hop
            ]
            minimum_radius = max([3.2, *(radius + 0.8 for radius in parent_radii)])
            if distance < minimum_radius:
                positions[name] = position / distance * minimum_radius
    return positions


def _node_size(artist: str, degree: int) -> float:
    if artist == HUB_ARTIST:
        return 28
    return 6 + min(degree, 8)


def _first_hop_edge_width(weight: int) -> float:
    return min(11.0, 2.0 + 1.8 * math.sqrt(max(weight, 1)))


def _node_hover_text(
    artist: str,
    graph: nx.Graph,
    click_data: dict,
    hub_artist: str = HUB_ARTIST,
) -> str:
    display_genre = escape(graph.nodes[artist].get("display_genre", "Other / Unknown"))
    raw_genre = escape(str(graph.nodes[artist].get("main_genre", "unknown")))
    lines = [f"<b>{escape(artist)}</b>", f"Genre: {display_genre}"]
    if raw_genre.casefold() != display_genre.casefold():
        lines.append(f"Source label: {raw_genre}")

    if artist == hub_artist:
        lines.append("Center of the collaboration network")
        return "<br>".join(lines)

    info = click_data.get(artist, {})
    direct = info.get("direct", [])
    if direct:
        lines.append(f"<b>Directly connected to {escape(hub_artist)} by:</b>")
        for track in direct[:4]:
            lines.append(f"• {escape(str(track['track']))} ({escape(str(track['year']))})")
        if len(direct) > 4:
            lines.append(f"• +{len(direct) - 4} more")
    elif info.get("path"):
        lines.append(f"<b>Path to {escape(hub_artist)}:</b>")
        for step in info["path"]:
            track_names = ", ".join(
                escape(str(track["track"])) for track in step.get("tracks", [])[:2]
            ) or "unknown recording"
            lines.append(
                f"{escape(step['from'])} → {escape(step['to'])}: {track_names}"
            )
    else:
        lines.append(f"No verified path to {escape(hub_artist)}")

    return "<br>".join(lines)


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


def _add_edge_trace(
    fig,
    positions,
    edges,
    color,
    name,
    width=2,
    showlegend=True,
    legendgroup=None,
):
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
            showlegend=showlegend,
            legendgroup=legendgroup or name,
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
            legendgroup=legendgroup or name,
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
    _add_edge_trace(fig, positions, hop2_edges, HOP2_EDGE_COLOR, "Second-hop lines", width=1.5)
    for index, edge in enumerate(
        sorted(hop1_edges, key=lambda item: (item[0], item[1]))
    ):
        _add_edge_trace(
            fig,
            positions,
            [edge],
            HOP1_EDGE_COLOR,
            "First-hop lines",
            width=_first_hop_edge_width(int(edge[2].get("weight", 1))),
            showlegend=index == 0,
            legendgroup="First-hop lines",
        )

    first_hop_names = [
        name
        for name in graph.nodes
        if name != hub_artist and graph.has_edge(hub_artist, name)
    ]
    second_hop_names = [
        name
        for name in graph.nodes
        if name != hub_artist and name not in first_hop_names
    ]

    def add_node_trace(
        names: list[str],
        trace_name: str,
        show_labels: bool,
        outline_color: str,
        outline_width: float,
        show_in_legend: bool = True,
    ) -> None:
        fig.add_trace(
            go.Scatter3d(
                x=[positions[name][0] for name in names],
                y=[positions[name][1] for name in names],
                z=[positions[name][2] for name in names],
                mode="markers+text" if show_labels else "markers",
                text=names if show_labels else None,
                textposition="top center",
                textfont=dict(size=8, color="#dddddd"),
                marker=dict(
                    size=[_node_size(name, graph.degree[name]) for name in names],
                    color=[
                        HUB_NODE_COLOR
                        if name == hub_artist
                        else genre_colors.get(
                            graph.nodes[name].get("display_genre", "Other / Unknown"),
                            "#888888",
                        )
                        for name in names
                    ],
                    line=dict(width=outline_width, color=outline_color),
                ),
                hovertext=[
                    _node_hover_text(name, graph, click_data, hub_artist=hub_artist)
                    for name in names
                ],
                hoverinfo="text",
                customdata=names,
                name=trace_name,
                showlegend=show_in_legend,
                legendgroup=trace_name,
            )
        )

    add_node_trace(
        second_hop_names,
        "Second-hop nodes",
        show_labels=False,
        outline_color="#ffffff",
        outline_width=0.5,
    )
    add_node_trace(
        first_hop_names,
        "First-hop nodes",
        show_labels=True,
        outline_color=HOP1_EDGE_COLOR,
        outline_width=4,
    )
    add_node_trace(
        [hub_artist],
        hub_artist,
        show_labels=True,
        outline_color="#ffffff",
        outline_width=1,
        show_in_legend=False,
    )

    fig.update_layout(
        title="Bon Iver Collaboration Network (3D · 2-hop featured credits)",
        showlegend=True,
        legend=dict(
            title=dict(text="Click to show / hide"),
            x=0.01,
            y=0.99,
            bgcolor="rgba(0,0,0,0.65)",
            font=dict(color="white"),
            groupclick="togglegroup",
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#111111",
            camera=dict(eye=dict(x=1.25, y=1.25, z=1.0)),
            dragmode="orbit",
            aspectmode="cube",
        ),
        paper_bgcolor="#111111",
        font=dict(color="#eeeeee"),
        margin=dict(l=0, r=0, t=50, b=0),
    )

    plot_html = fig.to_html(
        include_plotlyjs="cdn",
        div_id="collab-graph",
        full_html=False,
        config={"scrollZoom": False, "displaylogo": False, "responsive": True},
    )
    html = HTML_TEMPLATE.format(
        plot=plot_html,
        genre_legend="".join(
            f'<span style="background:{color}"></span><div>{escape(genre)}</div>'
            for genre, color in genre_colors.items()
        ),
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
    artists_df["display_genre"] = artists_df["main_genre"].map(collapse_genre)
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
