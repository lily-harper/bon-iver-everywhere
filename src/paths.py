from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"

COLLABORATIONS_CSV = RAW_DATA_DIR / "collaborations.csv"
ARTISTS_CSV = PROCESSED_DATA_DIR / "artists.csv"

EDGES_CSV = PROCESSED_DATA_DIR / "edges.csv"
ADJACENCY_MATRIX_CSV = PROCESSED_DATA_DIR / "adjacency_matrix.csv"
GRAPH_HTML = OUTPUT_DIR / "collaboration_graph.html"
GRAPH_PNG = OUTPUT_DIR / "collaboration_graph.png"

# Backward-compatible alias used by existing scripts
RAW_DATA_PATH = RAW_DATA_DIR

DATA_DIRS = (
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    OUTPUT_DIR,
)


def ensure_dirs() -> None:
    for directory in DATA_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def save_data(
    df: pd.DataFrame,
    directory: Path | None = None,
    output: str = "csv",
    filename: str = "data.csv",
) -> Path:
    directory = Path(directory or RAW_DATA_DIR)
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / filename
    if output == "csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported output format: {output}")

    return path
