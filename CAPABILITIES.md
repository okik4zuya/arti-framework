# ARTi capabilities map

One line per skill, tool and MCP server, plus who calls whom. Pointers only: details live in the
linked `SKILL.md` or `tools/<name>/README.md`, never here. **Maintenance: add one line here whenever a
skill, tool or MCP server is added, renamed or removed.**

## Skills (10, in `~/.arti/skills/`, linked into `~/.claude/skills/`)

| Skill | Owns | Calls |
|---|---|---|
| [ARTi-setup](skills/ARTi-setup/SKILL.md) | One-time onboarding; scaffolds each paper project's memory and `CLAUDE.md` | `arti-db`, `arti-memcheck` |
| [ARTi-idea](skills/ARTi-idea/SKILL.md) | Gap map, idea canvas, novelty scoring, research design, journal target | ARTi-ref, ARTi-jfinder, ARTi-crosscite, `arti-db`, search MCP |
| [ARTi-writing](skills/ARTi-writing/SKILL.md) | Journal profile, blueprint, drafting, review, cover letter, rebuttal | ARTi-ref, ARTi-scratchbook, ARTi-figure, `arti-docx`, `arti-convert` |
| [ARTi-scratchbook](skills/ARTi-scratchbook/SKILL.md) | Creating and populating the section-organized Scratchbook, tagging rules | ARTi-ref, search MCP |
| [ARTi-ref](skills/ARTi-ref/SKILL.md) | `arti-lit.db` CRUD, fulltext ingestion, paper extraction, search-route choice | `arti-lit`, `arti-convert`, search MCP |
| [ARTi-SLR](skills/ARTi-SLR/SKILL.md) | PRISMA systematic review from RQ to synthesis | ARTi-ref, `arti-lit`, search MCP, `arti-render` |
| [ARTi-figure](skills/ARTi-figure/SKILL.md) | Diagrams (`.drawio`), tables, data plots, composite figures (graphical abstract, multi-panel) | `arti-render`, `arti-table`, `arti-compose` |
| [ARTi-jfinder](skills/ARTi-jfinder/SKILL.md) | Ad-hoc Scimago journal lookup and ranking | `arti-jfinder` |
| [ARTi-crosscite](skills/ARTi-crosscite/SKILL.md) | Cross-citation overlap between two paper sets | `citation-chase` |
| [ARTi-annotate](skills/ARTi-annotate/SKILL.md) | Resolve the researcher's inline md comments and suggested edits (dashboard annotations) | `arti-annotate` |

## Tools (15 folders in `~/.arti/tools/`)

| Tool | What | Called by |
|---|---|---|
| [arti-lit](tools/arti-lit/README.md) | Per-project bibliography database and `library.md`/`references.md` exports | ARTi-ref, ARTi-SLR |
| [arti-convert](tools/arti-convert/README.md) | Document conversion: `pdf` (Markdown to A4 PDF via Edge or Chrome) and `ingest` ([PDFs to fulltext Markdown](tools/arti-convert/INGEST.md), registered into `arti-lit`) | ARTi-writing, ARTi-idea, ARTi-ref, ARTi-SLR, dashboard |
| [arti-db](tools/arti-db/README.md) | Cross-project project index, idea bank, idea index | ARTi-setup, ARTi-idea, dashboard |
| [arti-render](tools/arti-render/render.py) | JSON spec to editable `.drawio` diagram | ARTi-figure |
| [arti-table](tools/arti-table/README.md) | JSON spec to editable Markdown table (ARTi-figure table lane) | ARTi-figure |
| [arti-compose](tools/arti-compose/README.md) | HTML/SVG figure source to vector PDF + exact-size PNG with layout, font, text-size and image-resolution checks | ARTi-figure |
| [arti-docx](tools/arti-docx/README.md) | Markdown to styled `.docx` manuscript | ARTi-writing |
| [arti-annotate](tools/arti-annotate/README.md) | Inline CriticMarkup comments/suggestions in any md file: parse, revise, accept, revert, strip | ARTi-annotate, dashboard |
| [arti-jfinder](tools/arti-jfinder/README.md) | Scimago SJR snapshot database | ARTi-jfinder, ARTi-idea |
| [citation-chase](tools/citation-chase/README.md) | Does set A cite or get cited by set B (OpenAlex, S2 fallback) | ARTi-crosscite |
| [arti-license](tools/arti-license/README.md) | Client for paid licensing: activate, status, offline verify (Ed25519). Worker and `arti-admin` live outside `~/.arti` | dashboard (license gate, Settings > License), installers; ARTi-setup (notice only, never blocks) |
| [arti-update](tools/arti-update/README.md) | Updates: signed release manifest, notes, read-receipt, resumable bundle download, safe apply in a separate `updater.py` process (backup, health check, automatic rollback), manual rollback | dashboard (sidebar card, Settings > About: Update now, Roll back) |
| [arti-memcheck](tools/arti-memcheck/README.md) | T0 memory composition checker, `SessionStart` hook | hook, ARTi-setup |
| [_shared](tools/_shared/README.md) | Narrow shared helpers (paths, DB migration) | other tools |

## MCP servers

| Server | What | Notes |
|---|---|---|
| `arti-ref-search-mcp` | In-house live literature discovery: OpenAlex, Semantic Scholar, Google Scholar; citation tracing, candidate resolution, full-text download | [README](tools/arti-ref-search-mcp/README.md). Keys live in the git-ignored `mcp-keys.json` (not `.mcp.json`, which is tracked and shipped), never printed. Check live routes with `check_search_sources`. Never writes `arti-lit.db` |
| `openalex` (claude.ai connector) | Official OpenAlex: `find_keywords`, `keyword_search`, `search_works` (OQL), `analyze_works`, `resolve_references` | OAuth sign-in; about 1 USD of usage per day free |
| `scite` (claude.ai connector) | Smart citations (supporting or contrasting) | Needs URL authorization; not used yet |

## Finding literature

Which route for which task: [skills/ARTi-ref/references/search-routing.md](skills/ARTi-ref/references/search-routing.md).

## Considered, not used

- **OneCite** (github.com/HzaCode/OneCite): free DOI, PMID, arXiv and plain-text reference resolver to BibTeX; flags ambiguous matches. Covered by `resolve_external_candidates` plus openalex `resolve_references`.
- **CiteTrue** (citetrue.com): reference verification against bibliographic databases, with web, API and MCP. Pricing unconfirmed.
- **Aggregator MCPs** (`xingyulu23/Academix`, `pipeworx-io/mcp-openalex`): no source or feature beyond what `arti-ref-search-mcp` and the openalex connector give. `openags/paper-search-mcp` was replaced by the in-house server.
