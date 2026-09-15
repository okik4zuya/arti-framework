# citation-chase

Cross-project singleton (no `--project` flag, like `arti-jfinder`/`arti-db`). Answers a bounded
question for two named sets of DOIs: **does any paper in Set A already cite, or get cited by, any
paper in Set B?** Built for SLR novelty-claim checks — see `HANDOFF.md` for the full brief and
motivating case.

## Usage

```
"~/.arti/python/python.exe" "~/.arti/tools/citation-chase/cli.py" run \
    --set-a DOI1,DOI2,...      (or --set-a-file PATH, one DOI per line)
    --set-b DOI3,DOI4,...      (or --set-b-file PATH)
    --out PATH.jsonl           (required -- also the resume/state file)
    [--mailto you@example.com] (optional; OpenAlex polite-pool contact, speeds up responses)
    [--no-report]              (skip writing overlap-report.md next to --out)
```

`--set-a`/`--set-a-file` and `--set-b`/`--set-b-file` may be combined; both are merged.

## Output

One JSON object per Set-A DOI printed to stdout as it resolves, plus a final `{"summary": {...}}`
object. The same rows are persisted to `--out` (JSONL) so a re-run can resume.

```json
{"doi": "10.1021/acsestengg.3c00124", "cites_from_set_b": [], "cited_by_from_set_b": ["10.3390/nano15161270"], "source": "openalex", "status": "ok"}
{"summary": {"ok": 7, "partial": 0, "error": 0, "not_found": 1, "overlaps_found": 2}}
```

`status` is one of `ok` / `not_found` (no queried database has the DOI) / `error` (network/HTTP
failure, retried with backoff before giving up). A `not_found`/`error` row is retried on the next
run; an `ok` row is not re-queried.

`overlaps_found` in the summary is the number that matters for an SLR novelty claim: 0 means the
two clusters have never cross-cited each other; nonzero means the specific `cites_from_set_b` /
`cited_by_from_set_b` DOIs need surfacing into the manuscript's wording instead of a flat "no
existing work has done this."

If any overlap exists, a human-readable `overlap-report.md` is also written next to `--out`
(unless `--no-report`), listing only the rows with a hit.

## How it resolves each direction

1. **Backward (Set A cites Set B):** each Set-B DOI is resolved to its OpenAlex work ID once
   (cached across the whole run), then a Set-A paper's `referenced_works` ID list is checked for
   membership. This answers the same question as resolving every one of a Set-A paper's 30-60
   references individually, at a fraction of the API calls.
2. **Forward (Set A is cited by Set B):** `GET /works?filter=cites:<id>`, paginated; each result
   already carries its own DOI, so no extra resolution step is needed.
3. **Fallback:** if OpenAlex 404s on a Set-A DOI, Semantic Scholar's
   `paper/DOI:<doi>?fields=references.externalIds,citations.externalIds` is tried once. If that
   also misses, the row is `not_found` — never scraped from Google Scholar (no official API, see
   `HANDOFF.md` Path D — deliberately not built).

## Known limitation

A Set-B DOI that OpenAlex has not indexed at all can't be matched via the backward (ID-membership)
path; such a row prints as `unresolved_set_b` at the start of a run. It can still surface via the
forward direction if OpenAlex's citation graph independently links to it. This is inherent to
OpenAlex's own coverage, not a bug in this tool — cross-check with Semantic Scholar by hand for a
DOI that stays unresolved across a full run.

## Not built (see HANDOFF.md for why)

- Scopus (Path C) — institutional entitlement unconfirmed; check
  `~/.arti/tools/scopus-ris-batch-export/HANDOFF.md` before ever adding this.
- Google Scholar (Path D) — no official API; not implemented, ever.
- Citation-network visualization, full bibliometrics (h-index, co-citation clustering).
- Automatic manuscript-text generation from the overlap result.
