# Bon Iver (everywhere)

<p>
  <q>I'm up in the woods, I'm down on my mind </q><br>
  <em>Lost in the World</em> — Kanye West (feat. Bon Iver)
</p>

### Where is Bon Iver?

a project by Lily Holmes

* Does Bon Iver serve as a link between distinct genres?
* Which artists has Bon Iver collaborated with?
* What genres are represented in Bon Iver's discography?

Can artist connectivity be modeled through graph based methods?

An exploration of music, genre, and networks.

**Stack:** `python`, `pandas`, `numpy`, `networkx`, `plotly`

---

## Collaboration network graphs

This repo maps **Bon Iver's collaboration network** as a graph:

| Element | Definition |
|---------|------------|
| **Nodes** | Artists |
| **Edges** | Shared song credits (co-performers, co-writers, producers on the same track) |
| **Weight** | Number of songs connecting two artists |

### Visualization roadmap

1. **MVP — static 2D** (`data/output/collaboration_graph_2d.png`) — quick sanity check
2. **Interactive 2D** (`data/output/collaboration_graph_2d.html`) — hover song lists, pan/zoom
3. **Interactive 3D** (`data/output/collaboration_graph_3d.html`) — end-product view, rotate and explore

All three can be generated from the same graph JSON.

### Quick start (no API keys)

```bash
pip install -r requirements.txt

# Build graph from bundled sample collaborations
python scripts/build_graph.py

# Render all visualizations
python scripts/visualize.py
```

Open `data/output/collaboration_graph_3d.html` in a browser for the interactive 3D graph.

### Live data (Genius or Spotify)

1. Copy `.env.example` → `.env` and add credentials:
   - **Genius** — richer credits (writers, producers, featured artists). [Create a token](https://genius.com/api-clients).
   - **Spotify** — co-performers on tracks and search-based appearances. [Register an app](https://developer.spotify.com/dashboard).

2. Fetch and cache collaboration records:

```bash
python scripts/fetch_data.py --source genius
# or
python scripts/fetch_data.py --source spotify
```

3. Build and visualize:

```bash
python scripts/build_graph.py
python scripts/visualize.py
```

### Project layout

```
boniver/
  clients/          # Genius & Spotify API wrappers
  graph/            # NetworkX graph builder
  viz/              # 2D MVP + interactive 2D/3D renderers
  sample_collaborations.json   # offline demo dataset
scripts/
  fetch_data.py     # pull credits from an API
  build_graph.py    # records → graph JSON
  visualize.py      # graph JSON → PNG / HTML
data/
  cache/            # API responses (gitignored contents optional)
  output/           # generated graphs and figures
```

### Graph options

```bash
# Include edges between collaborators who share a song but neither is Bon Iver
python scripts/build_graph.py --full-network
```

### Notebook

See `start.ipynb` for an interactive walkthrough of the pipeline.
