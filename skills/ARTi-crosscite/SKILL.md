---
name: ARTi-crosscite
description: >
  Cross-citation overlap check between two named sets of papers, via ~/.arti/tools/citation-chase
  (OpenAlex primary, Semantic Scholar fallback, never Scopus or Google Scholar). Answers a bounded
  question: does any paper in Set A already cite, or get cited by, any paper in Set B? Use when a
  researcher needs to check whether two literature clusters have ever cross-cited each other before
  writing a novelty claim that depends on them being unconnected — e.g. an ARTi-idea Gap Map
  claiming two gaps/clusters have "never been cross-read." Triggers include: "check if these two
  clusters cite each other", "run a citation-chase between X and Y", "has anyone already connected
  these two literatures", "does paper A cite paper B". Do NOT use for retrieving or summarizing a
  single paper's content, adding/updating a bibliography entry, or fulltext ingestion — that's
  ARTi-ref. Do NOT use for constructing the DOI clusters themselves or scoring novelty from the
  result — that's ARTi-idea's Gap Map work; this skill only reports the citation facts.
---

# ARTi-crosscite Skill

Thin wrapper around the `citation-chase` CLI for a bounded yes/no question: has Set A ever
cross-cited Set B? Not a bibliometrics tool, not a citation-network builder — one overlap check,
in and out.

## What this is

Backed by `~/.arti/tools/citation-chase/` (cli.py + README.md + HANDOFF.md). **Cross-project
singleton** — no `--project` flag, like `arti-jfinder`/`arti-db`. Source priority: OpenAlex first
(resolves each Set-B DOI to a work ID once, then checks Set-A `referenced_works` membership for
the backward direction, and `filter=cites:<id>` for the forward direction); Semantic Scholar as a
one-shot fallback when OpenAlex 404s on a Set-A DOI. **Never** Scopus or Google Scholar — Scopus
entitlement is unconfirmed (see `~/.arti/tools/scopus-ris-batch-export/HANDOFF.md`) and Google
Scholar has no official API (deliberately not built, see the tool's own HANDOFF.md). Runs are
resumable and auditable: every row is persisted to `--out` as it resolves, so a re-run only
retries `not_found`/`error` rows, never re-queries an `ok` one.

## Invocation

```
"~/.arti/python/python.exe" "~/.arti/tools/citation-chase/cli.py" run --set-a DOI1,DOI2,... --set-b DOI3,DOI4,... --out PATH.jsonl [--mailto you@example.com] [--no-report]
```

(Mac/Linux: `~/.arti/python/bin/python3`.) `--set-a-file`/`--set-b-file` (one DOI per line) can be
used instead of, or combined with, `--set-a`/`--set-b`. See
`~/.arti/tools/citation-chase/README.md` for the full flag surface rather than relying on this
summary. Output is one JSON row per Set-A DOI on stdout plus a final `{"summary": {...}}` object;
the same rows persist to `--out` (JSONL).

## Resolving DOIs from arti-lit keys

The calling context almost always hands this skill `author-year` keys (from a Gap Map or a
research-design cluster), not raw DOIs — `citation-chase` itself takes DOIs only (no key
resolution, per its own non-goals). Resolve each key's *current* DOI before building
`--set-a`/`--set-b`:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library get --key KEY --project PATH
```

Always resolve fresh via `library get` rather than reusing a DOI list quoted earlier in the
conversation — a source's DOI in `arti-lit` can drift between turns.

## Interpreting results

Each row's `status` is `ok` (resolved, trust the `cites_from_set_b`/`cited_by_from_set_b` lists —
possibly empty), `not_found` (no queried source had the DOI — retried automatically on a re-run,
never a hard failure), or `error` (network/HTTP failure, retried with backoff before giving up).
The summary's `overlaps_found` is the number that actually matters: 0 means the two clusters have
never cross-cited each other, confirming a novelty claim that depends on that; nonzero means read
`overlap-report.md` (written next to `--out` unless `--no-report`) for the specific
`cites_from_set_b`/`cited_by_from_set_b` pairs and surface those into the researcher's wording
instead of a flat "no existing work has done this."

## Not this skill

- Retrieving, summarizing, or fulltext-ingesting a single paper, or any bibliography CRUD —
  **ARTi-ref**.
- Scimago journal search/ranking/aims-and-scope lookups — **ARTi-jfinder**.
- Constructing the Set A/Set B clusters in the first place, scoring novelty from the overlap
  result, or deciding manuscript wording — **ARTi-idea** (Gap Map) / **ARTi-writing**. This skill
  reports citation facts only.
- Scopus or Google Scholar citation checks — not built; see
  `~/.arti/tools/citation-chase/HANDOFF.md` for why.

## Change log
- 2026-09-15: skill created, wrapping the already-built and validated `citation-chase` tool so it
  is discoverable from trigger phrases instead of requiring the CLI's full path spelled out.
