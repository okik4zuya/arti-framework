# arti-pdf-ingest

Converts a batch of PDFs to Markdown fulltext for one project's `literature\fulltext\` folder and
registers each conversion in that project's `arti-lit` library (`literature\arti-lit.db` /
`literature\library.md`). Closes the manual copy/rename/registration loop that otherwise follows
converting a PDF by hand.

## Invocation

Same convention as every other `~/.arti/tools/*` tool -- the vendored interpreter's absolute path:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-pdf-ingest/cli.py" ingest \
    --project PATH --manifest PATH [--source-dir PATH] [--keep-source-pdf]
```

`--source-dir` defaults to the manifest's own folder.

Every row emits one JSON object to stdout (`{"key", "pdf", "status": "ok"|"error", "detail"}`),
plus a final summary object -- never a single all-or-nothing exit code, so a partial batch is still
fully inspectable: `{"summary": {"ok": N, "skipped": N, "error": N}}`.

## Manifest format (`manifest.csv`)

```
pdf_filename,key
Bandura_1977_selfefficacy.pdf,bandura-1977
smith-2026-preprint.pdf,smith-2026
```

Written by hand (or by Claude) before running -- no auto-detection. `key` must already exist as a
row in the target project's `literature\library.md` (added earlier via `arti-lit library add`
during screening); a row whose key isn't found is reported as `error` and does **not** create a
new library entry. Building the manifest means cross-referencing `library.md` rows with
`local file: —` against the PDFs actually on disk (by author/year/DOI) -- a Claude/researcher task,
not something this tool guesses at.

## Pipeline per row

1. Resolve `pdf_filename` inside `--source-dir`.
2. Confirm `key` exists via `arti-lit library get --key KEY --project PROJECT`.
3. Extract text (pdfminer text layer; OCR fallback via pdf2image + pytesseract if the text layer is
   empty) and write `literature\fulltext\<key>.md`.
4. If `--keep-source-pdf`, also copy the source PDF alongside it as
   `literature\fulltext\<key>.pdf`.
5. Register the result: `arti-lit library update --key KEY --local-file
   literature/fulltext/<key>.md --status fulltext --project PROJECT`.
6. One row's failure (missing PDF, key not found, extraction error, registration error) is logged
   as `error` and never aborts the rest of the batch.

## Design note: depends on `~/.arti` alone, not on `artipdf`

The plan this tool was built from originally called `C:\python_tools\artipdf\pdf2md.py` as a
subprocess, reusing its extraction logic unmodified but depending on that separate repo's own venv
for `pdfminer.six`/`pdf2image`/`pytesseract` and its own bundled poppler/tesseract binaries.

That subprocess dependency turned out to be unnecessary: `pdfminer.six`, `pdf2image`, and
`pytesseract` are now installed directly into the vendored `~/.arti/python` interpreter (see
`~/.arti/tools/requirements.txt`), and poppler/tesseract are vendored into `~/.arti/bin/` by the
NSIS installer (`~/.arti/installer/`, resolved via `~/.arti/tools/_shared/paths.py`) -- built for
exactly this purpose, per that folder's README: "so a future ARTi PDF-ingest tool can depend on
`~/.arti` alone, with zero reference to `artipdf`."

So `extract_text_to_markdown()` in this tool's `cli.py` re-implements the same short algorithm
in-process (same pdfminer call, same OCR fallback shape) instead of shelling out to
`pdf2md.py`. `C:\python_tools\artipdf` is not touched, imported, or depended on anywhere in this
tool. If `~/.arti/bin/tesseract` is missing (a machine that only ran `install.ps1`/`install.sh`,
not the NSIS installer), OCR-fallback rows fail with a clear "run the installer" error instead of
crashing; text-layer PDFs are unaffected.

## Not in this tool

- Extraction quality/fidelity (no table/equation reconstruction) -- same raw-text limitation as
  `pdf2md.py` itself, since the algorithm is the same.
- Creating new `arti-lit` library rows -- fulltext ingestion is a status *update* on an
  already-tracked source, never a way to add one.
- Manifest auto-generation / fuzzy PDF-to-key matching.
