import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.genius_pull import clean_collaborations
from src.graph import build_graph_outputs
from src.paths import (
    ADJACENCY_MATRIX_CSV,
    ARTISTS_CSV,
    COLLABORATIONS_CSV,
    EDGES_CSV,
    GRAPH_HTML,
    save_data,
)


def main():
    raw_df = pd.read_csv(COLLABORATIONS_CSV)
    collab_df = clean_collaborations(raw_df)
    save_data(collab_df, filename=COLLABORATIONS_CSV.name, directory=COLLABORATIONS_CSV.parent)

    collab_df, matrix, graph, artists_df = build_graph_outputs(
        collaborations_path=COLLABORATIONS_CSV,
        edges_path=EDGES_CSV,
        matrix_path=ADJACENCY_MATRIX_CSV,
        graph_path=GRAPH_HTML,
        artists_path=ARTISTS_CSV,
    )

    print(f"Saved {len(collab_df)} edges to {EDGES_CSV}")
    print(f"Saved {len(artists_df)} artist genre rows to {ARTISTS_CSV}")
    print(f"Saved {matrix.shape[0]}x{matrix.shape[1]} adjacency matrix to {ADJACENCY_MATRIX_CSV}")
    print(f"Saved interactive graph to {GRAPH_HTML}")
    print(f"Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")


if __name__ == "__main__":
    main()
