import os
import time

import pandas as pd
import requests

USER_AGENT = "bon-iver-everywhere/0.1 (student project)"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"
MUSICBRAINZ_SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"


def _spotify_token(client_id: str, client_secret: str) -> str | None:
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=15,
    )
    if not response.ok:
        return None
    return response.json().get("access_token")


def _genre_from_spotify(artist_name: str, token: str) -> str | None:
    response = requests.get(
        SPOTIFY_SEARCH_URL,
        params={"q": artist_name, "type": "artist", "limit": 1},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if not response.ok:
        return None

    items = response.json().get("artists", {}).get("items", [])
    if not items:
        return None

    genres = items[0].get("genres") or []
    return genres[0] if genres else None


def _genre_from_musicbrainz(artist_name: str) -> str | None:
    response = requests.get(
        MUSICBRAINZ_SEARCH_URL,
        params={"query": f'artist:"{artist_name}"', "fmt": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    if not response.ok:
        return None

    artists = response.json().get("artists", [])
    if not artists:
        return None

    tags = artists[0].get("tags") or []
    if tags:
        return tags[0].get("name")

    return artists[0].get("type")


def fetch_main_genre(artist_name: str, spotify_token: str | None = None) -> tuple[str, str]:
    if spotify_token:
        genre = _genre_from_spotify(artist_name, spotify_token)
        if genre:
            return genre, "spotify"

    genre = _genre_from_musicbrainz(artist_name)
    time.sleep(1.1)
    if genre:
        return genre, "musicbrainz"

    return "unknown", "none"


def enrich_artists(artist_names: list[str], cache_path=None) -> pd.DataFrame:
    cached = {}
    if cache_path and cache_path.exists():
        cache_df = pd.read_csv(cache_path)
        cached = {
            row["artist_name"]: (row["main_genre"], row["genre_source"])
            for _, row in cache_df.iterrows()
        }

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    spotify_token = None
    if client_id and client_secret:
        spotify_token = _spotify_token(client_id, client_secret)

    rows = []
    for index, artist_name in enumerate(sorted(set(artist_names)), start=1):
        if artist_name in cached:
            genre, source = cached[artist_name]
        else:
            print(f"Fetching genre ({index}/{len(set(artist_names))}): {artist_name}")
            genre, source = fetch_main_genre(artist_name, spotify_token=spotify_token)

        rows.append(
            {
                "artist_name": artist_name,
                "main_genre": genre,
                "genre_source": source,
            }
        )

    return pd.DataFrame(rows)
