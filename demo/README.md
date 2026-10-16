# ARTi client demo

One prompt, unattended, from idea to manuscript `.docx`. See [demo-prompt.md](demo-prompt.md).

| File | Purpose |
|---|---|
| [demo-prompt.md](demo-prompt.md) | The prompt to paste. Topic is the `{TOPIK}` variable |
| [demo-researcher-profile.md](demo-researcher-profile.md) | Fictional profile, copied into `memory/` only if no real profile exists |

## Before the demo (fresh machine)
- Run the installer, then confirm `~/.arti/python` and `~/.arti/bin` (poppler, tesseract) exist.
- In a Claude Code session, run `check_search_sources` and confirm at least OpenAlex is live; Semantic
  Scholar and Google Scholar keys are optional but add range.
- Open internet access is required (OpenAlex, Crossref, Scimago snapshot is local).
- Do a dry run once on the client machine; the prompt takes about 30 minutes.

## What it shows
Literature search across three sources, open-access full-text download with abstract-only fallback,
database of references, data classification and aggregation, PRISMA diagram, plots, tables, graphical
abstract, journal targeting, drafting from a Scratchbook, citation verification, `.docx` export, and a
capability scoreboard.

## After the demo
The demo profile is a placeholder. To replace it with the client's real one, delete
`~/.arti/memory/researcher-profile.md` and run ARTi-setup Workflow A.
