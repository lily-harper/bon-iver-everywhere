from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from boniver.config import CACHE_DIR, GENIUS_ACCESS_TOKEN
from boniver.models import Collaboration, CollaborationRecord, CollaborationRole
from boniver.normalize import is_bon_iver, normalize_artist_name


class GeniusClient:
    """Thin wrapper around the Genius API for Bon Iver collaboration credits."""

    BASE_URL = "https://api.genius.com"

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or GENIUS_ACCESS_TOKEN
        if not self.access_token:
            raise ValueError(
                "GENIUS_ACCESS_TOKEN is required. "
                "Create a token at https://genius.com/api-clients"
            )
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def search_artist(self, query: str) -> dict[str, Any]:
        payload = self._get("/search", params={"q": query})
        hits = payload.get("response", {}).get("hits", [])
        for hit in hits:
            result = hit.get("result", {})
            if result.get("primary_artist", {}).get("name", "").lower() == query.lower():
                return result
        if hits:
            return hits[0]["result"]
        raise LookupError(f"No Genius artist found for query: {query}")

    def artist_songs(self, artist_id: int, max_pages: int = 10) -> list[dict[str, Any]]:
        songs: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            payload = self._get(
                f"/artists/{artist_id}/songs",
                params={"sort": "popularity", "per_page": 50, "page": page},
            )
            batch = payload.get("response", {}).get("songs", [])
            if not batch:
                break
            songs.extend(batch)
            page += 1
            time.sleep(0.2)
        return songs

    def song_details(self, song_id: int) -> dict[str, Any]:
        payload = self._get(f"/songs/{song_id}")
        return payload.get("response", {}).get("song", {})

    @staticmethod
    def _role_from_credit_type(credit_type: str) -> CollaborationRole:
        lowered = credit_type.lower()
        if "writer" in lowered or "lyricist" in lowered:
            return "writer"
        if "producer" in lowered:
            return "producer"
        if "performer" in lowered or "primary" in lowered or "featured" in lowered:
            return "performer"
        return "other"

    def collaborations_from_song(self, song: dict[str, Any]) -> CollaborationRecord:
        song_id = str(song.get("id", ""))
        title = song.get("title", "Unknown")
        collaborators: list[Collaboration] = []

        primary = song.get("primary_artist", {})
        if primary.get("name"):
            collaborators.append(
                Collaboration(
                    song_title=title,
                    artist_name=normalize_artist_name(primary["name"]),
                    role="performer",
                    song_id=song_id,
                    source="genius",
                )
            )

        for featured in song.get("featured_artists", []):
            name = featured.get("name")
            if name:
                collaborators.append(
                    Collaboration(
                        song_title=title,
                        artist_name=normalize_artist_name(name),
                        role="performer",
                        song_id=song_id,
                        source="genius",
                    )
                )

        producer_artists = song.get("producer_artists") or []
        for producer in producer_artists:
            name = producer.get("name")
            if name:
                collaborators.append(
                    Collaboration(
                        song_title=title,
                        artist_name=normalize_artist_name(name),
                        role="producer",
                        song_id=song_id,
                        source="genius",
                    )
                )

        writer_artists = song.get("writer_artists") or []
        for writer in writer_artists:
            name = writer.get("name")
            if name:
                collaborators.append(
                    Collaboration(
                        song_title=title,
                        artist_name=normalize_artist_name(name),
                        role="writer",
                        song_id=song_id,
                        source="genius",
                    )
                )

        return CollaborationRecord(
            song_title=title,
            song_id=song_id,
            collaborators=collaborators,
            source="genius",
        )

    def fetch_bon_iver_collaborations(
        self,
        max_songs: int = 100,
        include_non_bon_iver_songs: bool = True,
    ) -> list[CollaborationRecord]:
        """Fetch songs where Bon Iver is credited and extract collaborators."""
        artist = self.search_artist("Bon Iver")
        songs = self.artist_songs(artist["id"])
        records: list[CollaborationRecord] = []

        for index, song_meta in enumerate(songs[:max_songs]):
            song = self.song_details(song_meta["id"])
            record = self.collaborations_from_song(song)
            names = record.artist_names()
            has_bon_iver = any(is_bon_iver(name) for name in names)
            if has_bon_iver or include_non_bon_iver_songs:
                records.append(record)
            if index % 10 == 0:
                time.sleep(0.3)

        return records

    def save_collaborations(
        self,
        records: list[CollaborationRecord],
        path: Path | None = None,
    ) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        out = path or CACHE_DIR / "genius_collaborations.json"
        payload = [
            {
                "song_title": record.song_title,
                "song_id": record.song_id,
                "source": record.source,
                "collaborators": [
                    {
                        "artist_name": c.artist_name,
                        "role": c.role,
                        "song_title": c.song_title,
                        "song_id": c.song_id,
                        "source": c.source,
                    }
                    for c in record.collaborators
                ],
            }
            for record in records
        ]
        out.write_text(json.dumps(payload, indent=2))
        return out

    @staticmethod
    def load_collaborations(path: Path) -> list[CollaborationRecord]:
        payload = json.loads(path.read_text())
        records: list[CollaborationRecord] = []
        for item in payload:
            records.append(
                CollaborationRecord(
                    song_title=item["song_title"],
                    song_id=item.get("song_id"),
                    source=item.get("source", "genius"),
                    collaborators=[
                        Collaboration(
                            song_title=c["song_title"],
                            artist_name=c["artist_name"],
                            role=c.get("role", "performer"),
                            song_id=c.get("song_id"),
                            source=c.get("source", "genius"),
                        )
                        for c in item["collaborators"]
                    ],
                )
            )
        return records
