#!/usr/bin/env python3
"""Generate all collaboration graph visualizations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boniver.config import OUTPUT_DIR
from boniver.data import load_graph, load_sample_collaborations, save_graph
from boniver.graph.builder import CollaborationGraphBuilder
from boniver.viz import render_2d, render_interactive_2d, render_interactive_3d


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--graph",
        type=Path,
        default=OUTPUT_DIR / "collaboration_graph.json",
        help="Input graph JSON (builds from sample data if missing)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render MVP 2D PNG, interactive 2D HTML, and interactive 3D HTML",
    )
    parser.add_argument(
        "--mvp",
        action="store_true",
        help="Render static 2D PNG only",
    )
    parser.add_argument(
        "--interactive-2d",
        action="store_true",
        help="Render interactive 2D HTML",
    )
    parser.add_argument(
        "--interactive-3d",
        action="store_true",
        help="Render interactive 3D HTML",
    )
    args = parser.parse_args()

    if args.graph.exists():
        graph = load_graph(args.graph)
    else:
        builder = CollaborationGraphBuilder()
        graph = builder.to_networkx(load_sample_collaborations())
        save_graph(graph, args.graph)

    render_all = args.all or not (args.mvp or args.interactive_2d or args.interactive_3d)

    outputs: list[Path] = []
    if render_all or args.mvp:
        outputs.append(render_2d(graph))
    if render_all or args.interactive_2d:
        outputs.append(render_interactive_2d(graph))
    if render_all or args.interactive_3d:
        outputs.append(render_interactive_3d(graph))

    for path in outputs:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
