import os
import sys
from pathlib import Path

import lyricsgenius
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.genius_pull import (
    HUB_ARTIST,
    collaboration_pull_two_hop,
    pull_settings,
)
from src.paths import COLLABORATIONS_CSV, save_data


def genius_token(env_var_name):
    genius_access_token = os.getenv(env_var_name)
    if not genius_access_token:
        raise ValueError("missing GENIUS_ACCESS_TOKEN in .env file")
    return lyricsgenius.Genius(genius_access_token)


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    genius = genius_token("GENIUS_ACCESS_TOKEN")
    genius = pull_settings(genius)

    collab_df = collaboration_pull_two_hop(genius, hub_artist=HUB_ARTIST)

    save_data(collab_df, filename=COLLABORATIONS_CSV.name, directory=COLLABORATIONS_CSV.parent)
    print(f"Saved {len(collab_df)} collaboration edges to {COLLABORATIONS_CSV}")


if __name__ == "__main__":
    main()
