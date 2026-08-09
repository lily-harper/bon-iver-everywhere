import csv
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "collaborations.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "review" / "first_hop_candidates.csv"
HUB_ARTIST = "Bon Iver"


def automated_flags(title: str, year: str, url: str) -> str:
    text = f"{title} {url}".lower()
    flags = []

    patterns = (
        (r"\blive\b|studio sessions|xcel energy center", "alternate_or_live_version"),
        (r"\boriginal\b|\[v\d+\]|\byedits?\b", "unreleased_or_fan_edit_risk"),
        (r"\bmixed\b", "mix_or_compilation_risk"),
        (r"annotated", "annotation_or_non_song_risk"),
    )
    for pattern, flag in patterns:
        if re.search(pattern, text):
            flags.append(flag)

    if not year.strip():
        flags.append("missing_release_year")

    return ";".join(flags)


def normalize_year(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return str(int(float(value)))


def build_review_rows() -> list[dict[str, str]]:
    rows = []
    with SOURCE_PATH.open(newline="", encoding="utf-8") as source_file:
        for source in csv.DictReader(source_file):
            primary_artist = source["source_artist"].strip()
            credited_artist = source["target_artist"].strip()
            if HUB_ARTIST not in (primary_artist, credited_artist):
                continue

            collaborator = (
                credited_artist if primary_artist == HUB_ARTIST else primary_artist
            )
            bon_iver_source_role = (
                "primary_artist" if primary_artist == HUB_ARTIST else source["role"]
            )
            collaborator_source_role = (
                source["role"] if primary_artist == HUB_ARTIST else "primary_artist"
            )
            year = normalize_year(source["release_year"])

            rows.append(
                {
                    "song_id": source["song_id"].strip(),
                    "track_title": source["track_title"].strip(),
                    "release_year": year,
                    "collaborator": collaborator,
                    "primary_artist_from_source": primary_artist,
                    "bon_iver_role_from_source": bon_iver_source_role,
                    "collaborator_role_from_source": collaborator_source_role,
                    "genius_url": source["genius_url"].strip(),
                    "automated_flags": automated_flags(
                        source["track_title"], year, source["genius_url"]
                    ),
                    "review_status": "pending",
                    "verified_credit_type": "",
                    "official_release": "",
                    "review_source_url": "",
                    "review_notes": "",
                }
            )

    return sorted(
        rows,
        key=lambda row: (
            row["collaborator"].casefold(),
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

    collaborators = {row["collaborator"] for row in rows}
    print(
        f"Saved {len(rows)} candidate credits across "
        f"{len(collaborators)} collaborators to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
