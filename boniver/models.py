from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CollaborationRole = Literal["performer", "writer", "producer", "other"]


@dataclass(frozen=True)
class Collaboration:
    """A single artist appearing on or credited for a song."""

    song_title: str
    artist_name: str
    role: CollaborationRole = "performer"
    song_id: str | None = None
    source: str = "unknown"


@dataclass
class CollaborationRecord:
    """All collaborators on one song."""

    song_title: str
    song_id: str | None = None
    collaborators: list[Collaboration] = field(default_factory=list)
    source: str = "unknown"

    def artist_names(self) -> set[str]:
        return {c.artist_name for c in self.collaborators}


@dataclass
class ArtistNode:
    name: str
    collaboration_count: int = 0
    song_count: int = 0
    roles: set[str] = field(default_factory=set)
    is_bon_iver: bool = False


@dataclass
class CollaborationEdge:
    source: str
    target: str
    weight: int
    songs: list[str] = field(default_factory=list)
