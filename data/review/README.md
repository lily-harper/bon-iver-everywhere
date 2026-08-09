# First-hop collaboration review

`first_hop_candidates.csv` contains every row in the current raw dataset where
Bon Iver is either the primary artist or a credited featured artist. No candidate
has been removed automatically.

Review each row by setting `review_status` to `accepted`, `rejected`, or
`needs_research`. The working review sheet may be extended with notes, corrected
credit types, or additional evidence columns when useful.

Only accept a row when it represents an officially released recording and Bon
Iver and the named collaborator both have performing credits. The
`*_role_from_source` columns preserve what the Genius-derived input reported;
they are not independently verified.

`automated_flags` highlights candidates that deserve extra attention. Flags do
not automatically reject a row.

Regenerate the review sheet from the raw data with:

```bash
python3 scripts/build_first_hop_review.py
```

Regeneration replaces the review sheet, so do not run it after beginning manual
review unless the completed review columns have been saved elsewhere.

## Second-hop review

`second_hop_candidates.csv` contains candidate credits connecting an accepted
first-hop collaborator (`bridge_artist`) to a possible `second_hop_artist`.
Direct Bon Iver credits and edges between two accepted first-hop artists are
excluded. Rejected and unresolved first-hop rows do not qualify an artist as a
bridge, although an artist with another accepted first-hop row still qualifies.

Set `review_status` to `accepted`, `rejected`, or `needs_research`, and use
`review_notes` for corrections or evidence. Regenerate the sheet with:

```bash
python3 scripts/build_second_hop_review.py
```

As with the first-hop sheet, regeneration replaces existing manual decisions.
