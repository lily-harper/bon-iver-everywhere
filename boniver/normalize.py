from __future__ import annotations

import re

from boniver.config import BON_IVER_ALIASES


def normalize_artist_name(name: str) -> str:
    """Canonicalize artist names for graph node identity."""
    cleaned = re.sub(r"\s+", " ", name.strip())
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_bon_iver(name: str) -> bool:
    return normalize_artist_name(name).lower() in BON_IVER_ALIASES


def display_name(name: str) -> str:
    """Prefer title case for visualization labels."""
    normalized = normalize_artist_name(name)
    if normalized.lower() in BON_IVER_ALIASES:
        return "Bon Iver"
    return normalized
