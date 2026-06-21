#!/usr/bin/env python3
"""Build a collaboration graph from cached or sample data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boniver.config import CACHE_DIR, OUTPUT_DIR
from boniver.data import load_collaborations, load_sample_collaborations, save_graph
from boniver.graph.builder import CollaborationGraphBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Collaboration JSON input (defaults to bundled sample data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "collaboration_graph.json",
        help="Output graph JSON path",
    )
    parser.add_argument(
        "--full-network",
        action="store_true",
        help="Include collaborator-to-collaborator edges, not just Bon Iver links",
    )
    args = parser.parse_args()

    if args.input:
        records = load_collaborations(args.input)
    else:
        cached_genius = CACHE_DIR / "genius_collaborations.json"
        cached_spotify = CACHE_DIR / "spotify_collaborations.json"
        if cached_genius.exists():
            records = load_collaborations(cached_genius)
        elif cached_spotify.exists():
            records = load_collaborations(cached_spotify)
        else:
            records = load_sample_collaborations()
            print("Using bundled sample data. Run scripts/fetch_data.py for live API data.")

    builder = CollaborationGraphBuilder()
    graph = builder.to_networkx(records, bon_iver_centric=not args.full_network)
    save_graph(graph, args.output)

    summary = builder.graph_summary(graph)
    print(
        f"Graph saved to {args.output} "
        f"({summary['nodes']} nodes, {summary['edges']} edges, density={summary['density']:.3f})"
    )


if __name__ == "__main__":
    main()
