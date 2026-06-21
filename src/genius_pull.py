import pandas as pd
import networkx as nx

HUB_ARTIST = "Bon Iver"
KNOWN_JUNK_ARTISTS = {
    "Rock Genius",
    "Rap Genius",
    "Country Genius",
    "Fashion Genius",
    "Sneaker Genius",
    "Tattoo Genius",
    "Concert Genius",
    "Genius",
    "Genius traductions françaises",
    "Spinelli",
}
JUNK_ARTIST_MARKERS = ("Contributor", "Traduction")


def get_release_year(song):
    if isinstance(song, dict):
        body = song
    else:
        body = getattr(song, "_body", {})

    components = body.get("release_date_components")
    if components and components.get("year"):
        return components["year"]

    release_date = body.get("release_date")
    if not release_date:
        album = body.get("album") or {}
        release_date = album.get("release_date")

    if release_date:
        parsed_date = pd.to_datetime(release_date, errors="coerce")
        if not pd.isna(parsed_date):
            return int(parsed_date.year)

    return None


def should_skip_song(title, exclude_terms):
    return any(term.lower() in title.lower() for term in exclude_terms)


def is_junk_artist(name: str) -> bool:
    if not name:
        return True
    if name in KNOWN_JUNK_ARTISTS:
        return True
    if any(marker in name for marker in JUNK_ARTIST_MARKERS):
        return True
    if name.endswith(" Genius") and name != "Perfume Genius":
        return True
    return False


def is_valid_song(song_info, exclude_terms):
    title = song_info.get("title") or ""
    if not title or should_skip_song(title, exclude_terms):
        return False
    if title.startswith("#"):
        return False

    primary_name = (song_info.get("primary_artist") or {}).get("name", "")
    if is_junk_artist(primary_name):
        return False

    featured_artists = song_info.get("featured_artists") or []
    if not featured_artists:
        return False

    return True


def pull_settings(genius):
    genius.skip_non_songs = True
    genius.exclude_terms = [
        "(Live)",
        "(Remix)",
        "Remix",
        "Live",
        "(Demo)",
        "(Band Demo)",
        "Demo",
        "Acoustic",
        "(Acoustic)",
    ]
    genius.timeout = 15
    genius.verbose = False
    return genius


def resolve_artist_id(genius, artist_name):
    response = genius.search_all(artist_name, per_page=5)

    for section in response.get("sections", []):
        if section.get("type") != "artist":
            continue
        for hit in section.get("hits", []):
            result = hit.get("result", {})
            if result.get("name") == artist_name:
                return result["id"]

    return None


def iter_artist_songs(genius, artist_id, sort="title"):
    page = 1
    while page:
        songs_page = genius.artist_songs(
            artist_id=artist_id,
            per_page=50,
            page=page,
            sort=sort,
        )

        for song_info in songs_page.get("songs", []):
            yield song_info

        page = songs_page.get("next_page")


def song_metadata_score(song_info):
    album = song_info.get("album") or {}
    score = 0
    if album.get("name"):
        score += 2
    if get_release_year(song_info):
        score += 1
    if song_info.get("featured_artists"):
        score += 1
    return score


def register_song(songs_by_title, song_info):
    title = song_info.get("title")
    if not title:
        return

    existing = songs_by_title.get(title)
    if existing is None or song_metadata_score(song_info) > song_metadata_score(existing):
        songs_by_title[title] = song_info


def pull_songs_for_artist(genius, artist_name, songs_by_title, exclude_terms):
    print(f"Pulling songs for {artist_name}")

    artist_id = resolve_artist_id(genius, artist_name)
    if artist_id is None:
        print(f"  Could not resolve artist: {artist_name}")
        return set()

    artists_on_songs = set()

    for song_info in iter_artist_songs(genius, artist_id):
        title = song_info.get("title")
        primary_name = (song_info.get("primary_artist") or {}).get("name", "Unknown")
        print(f"  - {title} ({primary_name})")

        if not title or not is_valid_song(song_info, exclude_terms):
            continue

        register_song(songs_by_title, song_info)

        if primary_name:
            artists_on_songs.add(primary_name)
        for featured in song_info.get("featured_artists") or []:
            if featured.get("name"):
                artists_on_songs.add(featured["name"])

    return artists_on_songs


def extract_edges_from_song(song_info):
    primary_name = (song_info.get("primary_artist") or {}).get("name")
    if not primary_name:
        return []

    album = (song_info.get("album") or {}).get("name")
    base = {
        "track_title": song_info.get("title"),
        "album": album,
        "release_year": get_release_year(song_info),
        "song_id": song_info.get("id"),
        "genius_url": song_info.get("url"),
    }

    rows = []
    for featured in song_info.get("featured_artists") or []:
        featured_name = featured.get("name")
        if not featured_name or featured_name == primary_name:
            continue
        rows.append(
            {
                **base,
                "source_artist": primary_name,
                "target_artist": featured_name,
            }
        )

    return rows


def songs_to_edges(songs_by_title):
    rows = []
    for song_info in songs_by_title.values():
        rows.extend(extract_edges_from_song(song_info))
    return pd.DataFrame(rows)


def hop1_neighbors(songs_by_title, hub_artist=HUB_ARTIST):
    neighbors = set()
    for song_info in songs_by_title.values():
        for edge in extract_edges_from_song(song_info):
            for artist in (edge["source_artist"], edge["target_artist"]):
                if artist != hub_artist:
                    neighbors.add(artist)
    return neighbors


def collaboration_pull_two_hop(genius, hub_artist=HUB_ARTIST):
    exclude_terms = genius.exclude_terms
    songs_by_title = {}

    pull_songs_for_artist(genius, hub_artist, songs_by_title, exclude_terms)
    neighbors = hop1_neighbors(songs_by_title, hub_artist=hub_artist)

    for neighbor in sorted(neighbors):
        pull_songs_for_artist(genius, neighbor, songs_by_title, exclude_terms)

    return songs_to_edges(songs_by_title)


def clean_collaborations(collab_df, hub_artist=HUB_ARTIST, hops=2):
    if collab_df.empty:
        return collab_df

    cleaned = collab_df.copy()
    cleaned = cleaned[
        ~cleaned["source_artist"].map(is_junk_artist)
        & ~cleaned["target_artist"].map(is_junk_artist)
    ]

    cleaned = (
        cleaned.sort_values(["track_title", "release_year"], na_position="last")
        .drop_duplicates(subset=["track_title", "source_artist", "target_artist"], keep="first")
        .reset_index(drop=True)
    )

    return filter_two_hop_edges(cleaned, hub_artist=hub_artist, hops=hops)


def filter_two_hop_edges(edges_df, hub_artist=HUB_ARTIST, hops=2):
    if edges_df.empty:
        return edges_df

    graph = nx.Graph()
    for _, row in edges_df.iterrows():
        graph.add_edge(row["source_artist"], row["target_artist"])

    allowed = {hub_artist}
    frontier = {hub_artist}
    for _ in range(hops):
        next_frontier = set()
        for node in frontier:
            for neighbor in graph.neighbors(node):
                if neighbor in allowed or is_junk_artist(neighbor):
                    continue
                allowed.add(neighbor)
                next_frontier.add(neighbor)
        frontier = next_frontier

    mask = edges_df["source_artist"].isin(allowed) & edges_df["target_artist"].isin(allowed)
    return edges_df[mask].reset_index(drop=True)
