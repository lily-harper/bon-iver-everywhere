#!/usr/bin/env python3
"""Fetch Bon Iver collaboration data from Genius or Spotify."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boniver.clients.genius import GeniusClient
from boniver.clients.spotify import SpotifyClient
from boniver.config import CACHE_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["genius", "spotify"],
        default="genius",
        help="API source for collaboration credits",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (defaults to data/cache/<source>_collaborations.json)",
    )
    parser.add_argument(
        "--max-songs",
        type=int,
        default=100,
        help="Maximum songs to fetch (Genius only)",
    )
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output = args.output or CACHE_DIR / f"{args.source}_collaborations.json"

    if args.source == "genius":
        client = GeniusClient()
        records = client.fetch_bon_iver_collaborations(max_songs=args.max_songs)
        client.save_collaborations(records, output)
    else:
        client = SpotifyClient()
        records = client.fetch_bon_iver_collaborations()
        client.save_collaborations(records, output)

    print(f"Saved {len(records)} songs to {output}")


if __name__ == "__main__":
    main()
