from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from boniver.models import Collaboration, CollaborationRecord


def load_sample_collaborations() -> list[CollaborationRecord]:
    sample_path = Path(__file__).resolve().parent / "sample_collaborations.json"
    payload = json.loads(sample_path.read_text())
    records: list[CollaborationRecord] = []
    for item in payload:
        records.append(
            CollaborationRecord(
                song_title=item["song_title"],
                song_id=item.get("song_id"),
                source=item.get("source", "sample"),
                collaborators=[
                    Collaboration(
                        song_title=c["song_title"],
                        artist_name=c["artist_name"],
                        role=c.get("role", "performer"),
                        song_id=c.get("song_id"),
                        source=c.get("source", "sample"),
                    )
                    for c in item["collaborators"]
                ],
            )
        )
    return records


def load_collaborations(path: Path) -> list[CollaborationRecord]:
    payload = json.loads(path.read_text())
    records: list[CollaborationRecord] = []
    for item in payload:
        records.append(
            CollaborationRecord(
                song_title=item["song_title"],
                song_id=item.get("song_id"),
                source=item.get("source", "unknown"),
                collaborators=[
                    Collaboration(
                        song_title=c["song_title"],
                        artist_name=c["artist_name"],
                        role=c.get("role", "performer"),
                        song_id=c.get("song_id"),
                        source=c.get("source", "unknown"),
                    )
                    for c in item["collaborators"]
                ],
            )
        )
    return records


def save_graph(graph: nx.Graph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = nx.node_link_data(graph)
    path.write_text(json.dumps(payload, indent=2))


def load_graph(path: Path) -> nx.Graph:
    payload = json.loads(path.read_text())
    return nx.node_link_graph(payload)
