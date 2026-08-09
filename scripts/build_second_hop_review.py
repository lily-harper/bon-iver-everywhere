import csv
from pathlib import Path

from build_first_hop_review import HUB_ARTIST, PROJECT_ROOT, automated_flags, normalize_year


FIRST_HOP_REVIEW_PATH = (
    PROJECT_ROOT / "data" / "review" / "first_hop_candidates.csv"
)
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "collaborations.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "review" / "second_hop_candidates.csv"


def accepted_first_hop_artists() -> set[str]:
    with FIRST_HOP_REVIEW_PATH.open(newline="", encoding="utf-8-sig") as review_file:
        rows = csv.DictReader(review_file)
        return {
            row["collaborator"].strip()
            for row in rows
            if row["review_status"].strip().casefold() == "accepted"
        }


def build_review_rows() -> list[dict[str, str]]:
    bridge_artists = accepted_first_hop_artists()
    rows = []

    with SOURCE_PATH.open(newline="", encoding="utf-8") as source_file:
        for source in csv.DictReader(source_file):
            primary_artist = source["source_artist"].strip()
            credited_artist = source["target_artist"].strip()
            endpoints = {primary_artist, credited_artist}

            if HUB_ARTIST in endpoints:
                continue

            bridges = endpoints & bridge_artists
            if len(bridges) != 1:
                # Zero bridges is outside the accepted graph. Two bridges is an
                # edge within hop one, not a path to a second-hop artist.
                continue

            bridge_artist = bridges.pop()
            second_hop_artist = (
                credited_artist
                if primary_artist == bridge_artist
                else primary_artist
            )
            year = normalize_year(source["release_year"])

            rows.append(
                {
                    "song_id": source["song_id"].strip(),
                    "review_status": "pending",
                    "track_title": source["track_title"].strip(),
                    "release_year": year,
                    "bridge_artist": bridge_artist,
                    "second_hop_artist": second_hop_artist,
                    "primary_artist_from_source": primary_artist,
                    "credited_artist_from_source": credited_artist,
                    "credited_role_from_source": source["role"].strip(),
                    "genius_url": source["genius_url"].strip(),
                    "automated_flags": automated_flags(
                        source["track_title"], year, source["genius_url"]
                    ),
                    "review_notes": "",
                }
            )

    unique_rows = {
        (
            row["song_id"],
            row["bridge_artist"],
            row["second_hop_artist"],
            row["credited_role_from_source"],
        ): row
        for row in rows
    }
    return sorted(
        unique_rows.values(),
        key=lambda row: (
            row["bridge_artist"].casefold(),
            row["second_hop_artist"].casefold(),
            row["release_year"],
            row["track_title"].casefold(),
        ),
    )


def main() -> None:
    rows = build_review_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Saved {len(rows)} candidate credits across "
        f"{len({row['bridge_artist'] for row in rows})} bridge artists and "
        f"{len({row['second_hop_artist'] for row in rows})} second-hop artists "
        f"to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
