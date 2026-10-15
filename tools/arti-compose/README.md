# arti-compose

HTML/CSS/SVG figure source to a vector PDF and an exact-size PNG, with built-in checks. This is
the composite lane of `ARTi-figure` (lane H): graphical abstracts, fixed-pixel images, and
multi-panel figures that mix plots, images, and drawn diagrams. The `.html` file in
`figures/src/` is the reproducibility record, the way a JSON spec is for `arti-render`.

No install beyond what is already vendored: rendering is the system Edge/Chrome called by
`subprocess` (`tools/_shared/browser.py`), checks use `pdfminer.six` and Pillow, the PNG comes from
poppler (`~/.arti/bin`) when present and from a browser screenshot otherwise. No Node, no Playwright.

## Use

```
python.exe tools/arti-compose/compose.py --new multi-panel --src figures/src/Fig_2.html
python.exe tools/arti-compose/compose.py --src figures/src/Fig_2.html --out-dir figures
```

`--new` copies a template from `skills/ARTi-figure/templates/` with `base.css` inlined, so the
source stays self-contained. Templates: `multi-panel` (190 mm, 2 columns), `graphical-abstract`
(1328 x 531 px). Size and mode come from `<meta>` tags in the source; flags override.

| Meta / flag | Meaning | Default |
|---|---|---|
| `arti:width`, `arti:height` / `--width`, `--height` | page size, `mm`, `cm`, `in`, `pt` or `px` | required |
| `arti:mode` / `--mode` | `print` (vector PDF + PNG at dpi) or `pixel` (PNG at exact px) | `pixel` if the size is in px, else `print` |
| `arti:dpi` / `--dpi` | PNG resolution in print mode | 600 |
| `arti:min-pt` / `--min-pt` | smallest allowed final text size, print mode | 7 |
| `arti:min-px` / `--min-px` | smallest allowed text size in CSS px, pixel mode (24 px is about 6.8 pt at 13 cm wide) | 24 |

`--strict` exits 2 if any check warns or fails; `--no-png`, `--no-lint` skip those steps.
`--tiff` also writes `<name>.tif` (LZW, RGB) from the PNG. Pixel mode writes the exact-size PNG and
also a vector PDF of the same page; the PDF is what the text-size check reads, so text inside SVG
(scaled by its viewBox) is measured at its real size.
A source must start with `<!doctype html>`. Compose pins `@page` and the page size variables
`--page-w` / `--page-h`, so a template can size its root with `var(--page-w)`.

## What it checks

Layout lint (headless `--dump-dom`, one copy of the source with a measuring script; the printed
copy never contains it): content overflowing its box, SVG text clipped by its own `<svg>`, images
that failed to load, text outside the page, content past the page. Add `data-lint-ignore` to an
element that overflows on purpose (for example a cropped micrograph).

PDF check (`pdfminer.six`): page count, page size against the request, fonts embedded, text is
real vector text, smallest text size at print width (rotated text is handled for 0 and 90 degrees),
effective resolution of every raster image (warns below 300 dpi).

PNG check (Pillow): pixel size, dpi tag, alpha flattened onto white. A passing run is not
approval: look at the PNG.

## Limits, measured on 2026-10-14 (Edge, Windows)

- The browser page size rounds up by about 0.1 mm; the PNG is 4 px wider than the exact size at 600 dpi.
- Browsers do not write a `--print-to-pdf` file for a relative path and still exit 0; the code uses
  absolute paths and checks that the file exists.
- `--dump-dom` cannot open a window narrower than about 500 px; the lint copy pins the root width,
  but `vw`/`vh` units in a source still follow the real window.
- Fallback PNG (no poppler) took 17 s at 600 dpi, and 1000 dpi on 190 x 110 mm took 28 s.
- Subscripts and superscripts are not counted: a character is skipped when it is under 85% of a
  bigger character that touches it along the text direction and its baseline is shifted by 10-90%
  of that size (the count is reported). Neighbours are searched page-wide because pdfminer
  sometimes puts a subscript in its own text line. Small text on the baseline, or with no bigger
  neighbour, is still counted. Limit: a deliberately tiny label raised off the baseline right next
  to bigger text would be skipped too.
- Only Edge was tested. Chrome, macOS and Linux are not.

## Examples

`examples/` holds the two prototypes with synthetic data. Run `examples/make_panels.py` first
(writes `examples/panels/`), then render `multi-panel-example.html` and
`graphical-abstract-example.html`.
