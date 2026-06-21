from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import requests

from boniver.config import (
    BON_IVER_SPOTIFY_ID,
    CACHE_DIR,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
)
from boniver.models import Collaboration, CollaborationRecord
from boniver.normalize import is_bon_iver, normalize_artist_name


class SpotifyClient:
    """Spotify Web API client focused on artist co-appearances."""

    BASE_URL = "https://api.spotify.com/v1"
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self.client_id = client_id or SPOTIFY_CLIENT_ID
        self.client_secret = client_secret or SPOTIFY_CLIENT_SECRET
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required. "
                "Register an app at https://developer.spotify.com/dashboard"
            )
        self._token: str | None = None
        self.session = requests.Session()

    def _authenticate(self) -> str:
        credentials = f"{self.client_id}:{self.client_secret}".encode()
        encoded = base64.b64encode(credentials).decode()
        response = self.session.post(
            self.TOKEN_URL,
            headers={"Authorization": f"Basic {encoded}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        response.raise_for_status()
        self._token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self._token}"})
        return self._token

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._token:
            self._authenticate()
        response = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
        if response.status_code == 401:
            self._authenticate()
            response = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _paginate(self, path: str, key: str, limit: int = 50) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = self._get(path, params={"limit": limit, "offset": offset})
            batch = payload.get(key, [])
            items.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
            time.sleep(0.1)
        return items

    def artist_albums(self, artist_id: str) -> list[dict[str, Any]]:
        return self._paginate(
            f"/artists/{artist_id}/albums",
            key="items",
        )

    def album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        return self._paginate(f"/albums/{album_id}/tracks", key="items")

    def track_details(self, track_ids: list[str]) -> list[dict[str, Any]]:
        tracks: list[dict[str, Any]] = []
        for start in range(0, len(track_ids), 50):
            chunk = track_ids[start : start + 50]
            payload = self._get("/tracks", params={"ids": ",".join(chunk)})
            tracks.extend(payload.get("tracks", []))
            time.sleep(0.1)
        return tracks

    def search_tracks(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        payload = self._get("/search", params={"q": query, "type": "track", "limit": limit})
        return payload.get("tracks", {}).get("items", [])

    def collaborations_from_track(self, track: dict[str, Any]) -> CollaborationRecord:
        title = track.get("name", "Unknown")
        track_id = track.get("id")
        collaborators = [
            Collaboration(
                song_title=title,
                artist_name=normalize_artist_name(artist["name"]),
                role="performer",
                song_id=track_id,
                source="spotify",
            )
            for artist in track.get("artists", [])
        ]
        return CollaborationRecord(
            song_title=title,
            song_id=track_id,
            collaborators=collaborators,
            source="spotify",
        )

    def fetch_bon_iver_collaborations(
        self,
        artist_id: str | None = None,
        include_appearances: bool = True,
        max_search_tracks: int = 50,
    ) -> list[CollaborationRecord]:
        """Collect tracks where Bon Iver appears alongside other artists."""
        artist_id = artist_id or BON_IVER_SPOTIFY_ID
        records: dict[str, CollaborationRecord] = {}

        albums = self.artist_albums(artist_id)
        track_ids: list[str] = []
        for album in albums:
            for track in self.album_tracks(album["id"]):
                if track.get("id"):
                    track_ids.append(track["id"])

        for track in self.track_details(track_ids):
            if not track:
                continue
            record = self.collaborations_from_track(track)
            if len(record.collaborators) >= 2:
                records[record.song_id or record.song_title] = record

        if include_appearances:
            for track in self.search_tracks("Bon Iver", limit=max_search_tracks):
                names = {normalize_artist_name(a["name"]).lower() for a in track.get("artists", [])}
                if not any(is_bon_iver(name) for name in names):
                    continue
                record = self.collaborations_from_track(track)
                if len(record.collaborators) >= 2:
                    records[record.song_id or record.song_title] = record

        return list(records.values())

    def save_collaborations(
        self,
        records: list[CollaborationRecord],
        path: Path | None = None,
    ) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        out = path or CACHE_DIR / "spotify_collaborations.json"
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
                    source=item.get("source", "spotify"),
                    collaborators=[
                        Collaboration(
                            song_title=c["song_title"],
                            artist_name=c["artist_name"],
                            role=c.get("role", "performer"),
                            song_id=c.get("song_id"),
                            source=c.get("source", "spotify"),
                        )
                        for c in item["collaborators"]
                    ],
                )
            )
        return records
