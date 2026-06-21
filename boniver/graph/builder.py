from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import networkx as nx

from boniver.models import ArtistNode, CollaborationEdge, CollaborationRecord
from boniver.normalize import display_name, is_bon_iver, normalize_artist_name


class CollaborationGraphBuilder:
    """
    Build an artist collaboration graph from song credit records.

    Nodes are artists. An undirected edge connects two artists when they share
    at least one song credit. Edge weight is the number of shared songs.
    """

    def __init__(
        self,
        focal_artist: str = "Bon Iver",
        include_roles: frozenset[str] | None = None,
        min_edge_weight: int = 1,
    ) -> None:
        self.focal_artist = display_name(focal_artist)
        self.include_roles = include_roles or frozenset(
            {"performer", "writer", "producer"}
        )
        self.min_edge_weight = min_edge_weight

    def _filtered_artists(self, record: CollaborationRecord) -> list[str]:
        artists = {
            display_name(c.artist_name)
            for c in record.collaborators
            if c.role in self.include_roles and c.artist_name.strip()
        }
        return sorted(artists)

    def build_edges(self, records: list[CollaborationRecord]) -> list[CollaborationEdge]:
        pair_songs: dict[tuple[str, str], set[str]] = defaultdict(set)

        for record in records:
            artists = self._filtered_artists(record)
            if len(artists) < 2:
                continue
            for left, right in combinations(artists, 2):
                key = tuple(sorted((left, right)))
                pair_songs[key].add(record.song_title)

        edges: list[CollaborationEdge] = []
        for (left, right), songs in pair_songs.items():
            weight = len(songs)
            if weight >= self.min_edge_weight:
                edges.append(
                    CollaborationEdge(
                        source=left,
                        target=right,
                        weight=weight,
                        songs=sorted(songs),
                    )
                )
        return edges

    def build_nodes(
        self,
        records: list[CollaborationRecord],
        edges: list[CollaborationEdge],
    ) -> list[ArtistNode]:
        song_counts: dict[str, set[str]] = defaultdict(set)
        role_map: dict[str, set[str]] = defaultdict(set)
        edge_counts: dict[str, int] = defaultdict(int)

        for record in records:
            artists = self._filtered_artists(record)
            for artist in artists:
                song_counts[artist].add(record.song_title)
                for collab in record.collaborators:
                    if display_name(collab.artist_name) == artist:
                        role_map[artist].add(collab.role)

        for edge in edges:
            edge_counts[edge.source] += edge.weight
            edge_counts[edge.target] += edge.weight

        all_artists = set(song_counts) | {self.focal_artist}
        nodes: list[ArtistNode] = []
        for name in sorted(all_artists):
            nodes.append(
                ArtistNode(
                    name=name,
                    collaboration_count=edge_counts.get(name, 0),
                    song_count=len(song_counts.get(name, set())),
                    roles=role_map.get(name, set()),
                    is_bon_iver=is_bon_iver(name),
                )
            )
        return nodes

    def to_networkx(
        self,
        records: list[CollaborationRecord],
        bon_iver_centric: bool = True,
    ) -> nx.Graph:
        """
        Build a NetworkX graph.

        When bon_iver_centric is True, only include edges that touch Bon Iver
        (direct collaborators). Set False to include collaborator-to-collaborator
        edges from shared songs.
        """
        edges = self.build_edges(records)
        if bon_iver_centric:
            edges = [
                edge
                for edge in edges
                if is_bon_iver(edge.source) or is_bon_iver(edge.target)
            ]

        nodes = self.build_nodes(records, edges)
        graph = nx.Graph()

        for node in nodes:
            if bon_iver_centric and not node.is_bon_iver:
                connected = any(
                    edge.source == node.name or edge.target == node.name for edge in edges
                )
                if not connected:
                    continue
            graph.add_node(
                node.name,
                song_count=node.song_count,
                collaboration_count=node.collaboration_count,
                roles=sorted(node.roles),
                is_bon_iver=node.is_bon_iver,
            )

        for edge in edges:
            if edge.source in graph and edge.target in graph:
                graph.add_edge(
                    edge.source,
                    edge.target,
                    weight=edge.weight,
                    songs=edge.songs,
                )

        return graph

    @staticmethod
    def graph_summary(graph: nx.Graph) -> dict[str, int | float]:
        if graph.number_of_nodes() == 0:
            return {"nodes": 0, "edges": 0, "density": 0.0}
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": float(nx.density(graph)),
        }
