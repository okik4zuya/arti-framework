#!/usr/bin/env python3
"""
arti-compose - HTML/CSS/SVG figure source -> vector PDF + exact-size PNG, with checks

The HTML file is the reproducibility record (like a JSON spec for arti-render). Rendering is a
headless Edge/Chrome called by subprocess (tools/_shared/browser.py); nothing is installed for
that. Verification is built in: a PDF check (pdfminer: pages, size, embedded fonts, real text
size, raster-image resolution) and an in-page layout lint (overflow, clipped SVG text, broken
images, content outside the page).

Size comes from <meta> tags in the source, CLI flags override:
    <meta name="arti:width"  content="190mm">   (mm, cm, in, pt or px)
    <meta name="arti:height" content="120mm">
    <meta name="arti:dpi"    content="600">     (print mode PNG resolution)
    <meta name="arti:mode"   content="print">   (print = vector PDF + PNG at dpi; pixel = PNG at exact px)
    <meta name="arti:min-pt" content="7">       (smallest allowed final text size, print mode)
    <meta name="arti:min-px" content="24">      (smallest allowed text size in px, pixel mode)
mode defaults to pixel when the size is in px, else print.

Usage:
    python compose.py --src figures/src/Fig_2.html --out-dir figures
    python compose.py --new multi-panel --src figures/src/Fig_2.html     # scaffold from a template
"""
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys

# Reports quote figure text (minus signs, Greek letters); never let a console codepage crash a run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
# pdfminer logs one warning per gradient pattern colour ("Cannot set gray stroke color"); harmless here.
logging.getLogger("pdfminer").setLevel(logging.ERROR)

ARTI_HOME = os.environ.get("ARTI_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ARTI_HOME not in sys.path:
    sys.path.insert(0, ARTI_HOME)
from tools._shared.browser import dump_dom, find_browser, print_pdf, screenshot  # noqa: E402
from tools._shared.paths import poppler_bin_dir  # noqa: E402

TEMPLATE_DIR = os.path.join(ARTI_HOME, "skills", "ARTi-figure", "templates")
UNITS_PX = {"px": 1.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0, "pt": 96 / 72}
MIN_RASTER_DPI = 300  # lowest rung of references/artwork-default.md (halftone)


# --- source parsing ------------------------------------------------------------------------

def parse_meta(html_text):
    meta = {}
    for m in re.finditer(r'<meta\s+name="arti:([a-z-]+)"\s+content="([^"]*)"', html_text):
        meta[m.group(1)] = m.group(2).strip()
    return meta


def parse_len(s):
    """'190mm' -> (css_px, mm, unit). A bare number is px."""
    m = re.fullmatch(r"\s*([0-9.]+)\s*(mm|cm|in|pt|px)?\s*", s or "")
    if not m:
        raise ValueError(f"cannot read length {s!r} (use e.g. 190mm, 8in, 1328px)")
    value, unit = float(m.group(1)), m.group(2) or "px"
    px = value * UNITS_PX[unit]
    return px, px * 25.4 / 96, unit


def resolve_spec(html_text, args):
    meta = parse_meta(html_text)
    width = args.width or meta.get("width")
    height = args.height or meta.get("height")
    if not width or not height:
        raise SystemExit('size missing: add <meta name="arti:width" content="190mm"> and arti:height, or pass --width/--height')
    wpx, wmm, wunit = parse_len(width)
    hpx, hmm, _ = parse_len(height)
    mode = args.mode or meta.get("mode") or ("pixel" if wunit == "px" else "print")
    if mode not in ("print", "pixel"):
        raise SystemExit(f"mode must be print or pixel, got {mode!r}")
    return {
        "mode": mode,
        "w_css": width, "h_css": height,
        "w_px": wpx, "h_px": hpx, "w_mm": wmm, "h_mm": hmm,
        "dpi": float(args.dpi or meta.get("dpi") or 600),
        "min_pt": float(args.min_pt or meta.get("min-pt") or 7),
        "min_px": float(args.min_px or meta.get("min-px") or 24),
    }


# --- in-page lint --------------------------------------------------------------------------

LINT_JS = """
<script id="arti-compose-lint">
addEventListener('load', function () { (document.fonts ? document.fonts.ready : Promise.resolve()).then(function () {
  var r = {overflow: [], svgText: [], img: [], outside: [], page: null, error: null};
  try {
    var W = %(w)s, H = %(h)s;
    function sel(e) {
      if (e.id) return '#' + e.id;
      var s = e.tagName.toLowerCase();
      if (typeof e.className === 'string' && e.className.trim()) s += '.' + e.className.trim().split(/\\s+/).join('.');
      return s;
    }
    function ignored(e) { return e.closest && e.closest('[data-lint-ignore]'); }
    var de = document.documentElement;
    r.page = {scrollW: document.body.scrollWidth, scrollH: document.body.scrollHeight, W: W, H: H};
    document.querySelectorAll('body *').forEach(function (e) {
      if (ignored(e) || e.closest('svg') && e.tagName.toLowerCase() !== 'svg') return;
      var cs = getComputedStyle(e);
      if (cs.display === 'none') return;
      if (e.tagName === 'IMG') {
        if (!(e.complete && e.naturalWidth > 0)) r.img.push(sel(e) + ' src=' + (e.getAttribute('src') || ''));
        return;
      }
      if (cs.display !== 'inline' && e.clientWidth > 0 && e.clientHeight > 0 &&
          (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1)) {
        r.overflow.push(sel(e) + ' content ' + e.scrollWidth + 'x' + e.scrollHeight + ' > box ' + e.clientWidth + 'x' + e.clientHeight);
      }
      var hasText = Array.prototype.some.call(e.childNodes, function (n) { return n.nodeType === 3 && n.textContent.trim(); });
      if (hasText) {
        var b = e.getBoundingClientRect();
        if (b.left < -1 || b.top < -1 || b.right > W + 1 || b.bottom > H + 1) r.outside.push(sel(e) + ' text outside page');
      }
    });
    document.querySelectorAll('svg text').forEach(function (t) {
      if (ignored(t)) return;
      var s = t.ownerSVGElement; if (!s) return;
      var a = t.getBoundingClientRect(), b = s.getBoundingClientRect();
      if (a.width && (a.left < b.left - 1 || a.right > b.right + 1 || a.top < b.top - 1 || a.bottom > b.bottom + 1)) {
        r.svgText.push('"' + t.textContent.trim().slice(0, 40) + '" extends beyond its <svg> (clipped)');
      }
    });
  } catch (err) { r.error = String(err); }
  var pre = document.createElement('pre'); pre.id = 'arti-lint'; pre.textContent = JSON.stringify(r);
  document.body.appendChild(pre);
}); });
</script>
"""


def inject(html_text, spec, with_lint):
    """Copy of the source with page size/margins forced to the spec (and the lint script appended)."""
    css = [f":root{{--page-w:{spec['w_css']};--page-h:{spec['h_css']};}}", "html,body{margin:0;}",
           f"@page{{size:{spec['w_css']} {spec['h_css']};margin:0;}}"]  # pixel mode also prints a PDF
    if with_lint:
        # dump-dom cannot open a window narrower than ~500 px, so pin the root to the page width
        # to lay fluid content out as the printed page will (vw/vh units still follow the window).
        css.append(f"html{{width:{spec['w_css']};}}")
    style = '<style id="arti-compose-page">' + "".join(css) + "</style>\n"
    if "</head>" in html_text:
        html_text = html_text.replace("</head>", style + "</head>", 1)
    else:
        html_text = style + html_text
    if with_lint:
        js = LINT_JS % {"w": round(spec["w_px"], 2), "h": round(spec["h_px"], 2)}
        html_text = html_text.replace("</body>", js + "</body>", 1) if "</body>" in html_text else html_text + js
    return html_text


def run_lint(tmp_html, spec):
    dom = dump_dom(tmp_html, width_px=round(spec["w_px"]), height_px=round(spec["h_px"]))
    m = re.search(r'<pre id="arti-lint">(.*?)</pre>', dom or "", re.S)
    if not m:
        return None
    import html as htmllib
    return json.loads(htmllib.unescape(m.group(1)))


# --- PDF checks (pdfminer) -----------------------------------------------------------------

def check_pdf(pdf_path, spec, report):
    try:
        from pdfminer.layout import LTChar, LTImage
        from pdfminer.high_level import extract_pages
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdftypes import resolve1
    except ImportError:
        report("warn", "pdfminer.six not available - PDF checks skipped")
        return

    with open(pdf_path, "rb") as fh:
        doc = PDFDocument(PDFParser(fh))
        pages = list(PDFPage.create_pages(doc))
        if len(pages) == 1:
            report("ok", "1 page")
        else:
            report("fail", f"{len(pages)} pages - content overflows the page; shrink it or raise arti:height")
        if pages:
            x0, y0, x1, y1 = pages[0].mediabox
            w_mm, h_mm = (x1 - x0) * 25.4 / 72, (y1 - y0) * 25.4 / 72
            d = max(abs(w_mm - spec["w_mm"]), abs(h_mm - spec["h_mm"]))
            msg = f"page {w_mm:.1f} x {h_mm:.1f} mm (requested {spec['w_mm']:.1f} x {spec['h_mm']:.1f})"
            report("ok" if d <= 0.5 else "warn", msg + ("" if d <= 0.5 else " - differs by more than rounding"))

        fonts = {}
        for pg in pages:
            res = resolve1(pg.resources) or {}
            for _, ref in (resolve1(res.get("Font")) or {}).items():
                f = resolve1(ref)
                name = getattr(resolve1(f.get("BaseFont")), "name", str(resolve1(f.get("BaseFont"))))
                sub = getattr(resolve1(f.get("Subtype")), "name", "")
                if sub == "Type0":
                    f = resolve1(resolve1(f.get("DescendantFonts"))[0])
                desc = resolve1(f.get("FontDescriptor")) or {}
                fonts[name] = (sub, any(k in desc for k in ("FontFile", "FontFile2", "FontFile3")))
        bad = [n for n, (sub, emb) in fonts.items() if not emb and sub != "Type3"]
        t3 = [n for n, (sub, _) in fonts.items() if sub == "Type3"]
        if not fonts:
            report("warn", "no fonts in the PDF - text may have been rasterised")
        elif bad:
            report("fail", "fonts NOT embedded: " + ", ".join(bad))
        else:
            report("ok", f"fonts embedded: {', '.join(sorted(fonts))}")
        if t3:
            report("warn", "Type 3 (bitmap-like) fonts: " + ", ".join(t3))

    sizes, images, script = {}, [], [0]

    def char_size(c):
        # LTChar.size is the glyph advance for rotated text, so measure the extent
        # perpendicular to the text direction (exact for 0 and 90 degrees only).
        rotated = abs(c.matrix[1]) > abs(c.matrix[0])
        return round(c.width if rotated else c.height, 1), (c.matrix[4] if rotated else c.matrix[5])

    def add_chars(chars):
        """chars: LTChar list of one page. A character is a sub/superscript, and not counted, when a
        clearly bigger character (it is under 85% of its size) touches it along the text direction
        and its baseline is shifted by 10-90% of the bigger size. Small text on the same baseline,
        or with no bigger neighbour, is still counted. (pdfminer sometimes puts a subscript in a
        line of its own, so lines cannot be used for this.)"""
        info = []
        for c in chars:
            if not c.get_text().strip():
                continue
            size, base = char_size(c)
            rot = abs(c.matrix[1]) > abs(c.matrix[0])
            a0, a1 = (c.y0, c.y1) if rot else (c.x0, c.x1)
            info.append((rot, size, base, min(a0, a1), max(a0, a1), c.get_text(), len(info)))
        import bisect
        info.sort(key=lambda t: (t[0], t[3]))
        keys = [(t[0], t[3]) for t in info]
        maxs = max((t[1] for t in info), default=0)
        flagged = {}
        for i, (rot, size, base, a0, a1, text, idx) in enumerate(info):
            is_script = False
            for j in range(bisect.bisect_left(keys, (rot, a0 - 2 * maxs)), bisect.bisect_right(keys, (rot, a1 + 0.6 * maxs))):
                r2, s2, b2, c0, c1, _, _ = info[j]
                if j == i or r2 != rot or size >= 0.85 * s2:
                    continue
                if c0 - a1 <= 0.6 * s2 and a0 - c1 <= 0.6 * s2 and 0.1 * s2 <= abs(base - b2) <= 0.9 * s2:
                    is_script = True
                    break
            flagged[idx] = is_script
        for rot, size, base, a0, a1, text, idx in sorted(info, key=lambda t: t[6]):  # reading order, for the samples
            if flagged[idx]:
                script[0] += 1
                continue
            n, sample = sizes.get(size, (0, ""))
            sizes[size] = (n + 1, (sample + text)[:28] if len(sample) < 28 else sample)

    def walk(obj, out):
        for e in obj:
            if isinstance(e, LTChar):
                out.append(e)
            elif isinstance(e, LTImage):
                images.append(e)
            elif hasattr(e, "__iter__"):
                walk(e, out)

    for pg in extract_pages(pdf_path):
        page_chars = []
        walk(pg, page_chars)
        add_chars(page_chars)
    nchars = sum(n for n, _ in sizes.values()) + script[0]
    if nchars:
        # Pixel mode states the floor in CSS px (1 px = 0.75 pt in the PDF); print mode in pt.
        k, unit, floor = (96 / 72, "px", spec["min_px"]) if spec["mode"] == "pixel" else (1.0, "pt", spec["min_pt"])
        lo, hi = min(sizes, default=0) * k, max(sizes, default=0) * k
        report("ok", f"text is vector: {nchars} characters, sizes {lo:.0f}-{hi:.0f} {unit}"
                     if unit == "px" else f"text is vector: {nchars} characters, sizes {lo:g}-{hi:g} pt")
        small = {s: v for s, v in sizes.items() if s * k < floor - 0.05 * k}
        if small:
            detail = "; ".join(f"{s * k:.1f} {unit} x{n} (\"{smp.strip()}\")" for s, (n, smp) in sorted(small.items()))
            report("warn", f"text below {floor:g} {unit} at final size: {detail}")
        else:
            report("ok", f"all text >= {floor:g} {unit} at final size")
        if script[0]:
            report("ok", f"{script[0]} sub/superscript character(s) not counted (under 85% of a touching bigger character and off its baseline)")
    else:
        report("warn", "no extractable text in the PDF")

    # pdfminer's layout pass misses soft-mask images (what a browser makes of a blurred shadow or an SVG
    # filter), so count image XObjects straight from the page resources, including inside forms.
    n_xobj = 0
    seen = set()

    def count_xobjects(obj):
        """Walk the resource tree (XObjects, forms, patterns, ExtGState soft masks) and count Image objects."""
        nonlocal n_xobj
        oid = getattr(obj, "objid", None)
        if oid is not None:
            if oid in seen:
                return
            seen.add(oid)
        obj = resolve1(obj)
        if hasattr(obj, "attrs"):  # PDFStream: look at its dictionary
            obj = obj.attrs
        if isinstance(obj, dict):
            if getattr(resolve1(obj.get("Subtype")), "name", "") == "Image":
                n_xobj += 1
                return
            for k, v in obj.items():
                if k not in ("Parent", "Contents", "Font"):
                    count_xobjects(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                count_xobjects(v)

    with open(pdf_path, "rb") as fh:
        for pg in PDFPage.create_pages(PDFDocument(PDFParser(fh))):
            count_xobjects(resolve1(pg.resources))
    if n_xobj > len(images):
        extra = n_xobj - len(images)
        report("warn", f"{extra} raster image object(s) beyond the visible pictures (soft masks from shadows, blur or SVG filters): "
                       "those effects are rasterised, so the PDF is not pure vector")

    if images:
        dpis = []
        for im in images:
            wi = (im.bbox[2] - im.bbox[0]) / 72
            if wi > 0 and im.srcsize[0]:
                dpis.append(im.srcsize[0] / wi)
        if dpis:
            report("ok" if min(dpis) >= MIN_RASTER_DPI else "warn",
                   f"{len(images)} raster image(s), effective resolution {min(dpis):.0f}-{max(dpis):.0f} dpi"
                   + ("" if min(dpis) >= MIN_RASTER_DPI else f" (< {MIN_RASTER_DPI}: supply a larger source image)"))
    elif not n_xobj:
        report("ok", "no raster images (pure vector)")


# --- PNG output ----------------------------------------------------------------------------

def poppler_pdftoppm():
    exe = os.path.join(poppler_bin_dir(), "pdftoppm.exe" if os.name == "nt" else "pdftoppm")
    if os.path.exists(exe):
        return exe
    return shutil.which("pdftoppm")


def finish_png(path, dpi, report, expect_px=None):
    from PIL import Image
    with Image.open(path) as im:
        had_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        rgb = im.convert("RGBA")
        bg = Image.new("RGB", rgb.size, (255, 255, 255))
        bg.paste(rgb, mask=rgb.getchannel("A"))
        size = bg.size
    bg.save(path, dpi=(dpi, dpi) if dpi else None)
    msg = f"PNG {size[0]} x {size[1]} px"
    if dpi:
        msg += f" at {dpi:g} dpi = {size[0] / dpi * 25.4:.1f} x {size[1] / dpi * 25.4:.1f} mm"
    msg += ", RGB no alpha" + (" (alpha flattened onto white)" if had_alpha else "")
    if expect_px and tuple(size) != tuple(expect_px):
        report("fail", msg + f" - expected {expect_px[0]} x {expect_px[1]}")
    else:
        report("ok", msg)


# --- main flow -----------------------------------------------------------------------------

def compose(src, out_dir, args):
    src = os.path.abspath(src)
    name = os.path.splitext(os.path.basename(src))[0]
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    spec = resolve_spec(text, args)

    results = {"ok": 0, "warn": 0, "fail": 0}

    def report(level, msg):
        results[level] += 1
        print(f"  [{ {'ok': 'ok', 'warn': 'WARN', 'fail': 'FAIL'}[level] }] {msg}")

    print(f"arti-compose: {name}  ({spec['w_css']} x {spec['h_css']}, {spec['mode']} mode)")
    if not re.match(r"\s*<!doctype html", text, re.I):
        report("warn", "no <!doctype html> - the browser falls back to quirks mode, so layout and the page-overflow check can be wrong")
    if not find_browser():
        raise SystemExit("no Edge/Chrome found - install one or print the HTML to PDF by hand")

    # Temp copies sit next to the source so relative <img src> paths resolve. The lint copy is
    # separate: its result element must never reach the printed PDF or the screenshot.
    tmp = os.path.join(os.path.dirname(src), f".~compose_{os.path.basename(src)}")
    tmp_lint = os.path.join(os.path.dirname(src), f".~lint_{os.path.basename(src)}")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(inject(text, spec, with_lint=False))

        if not args.no_lint:
            with open(tmp_lint, "w", encoding="utf-8", newline="") as f:
                f.write(inject(text, spec, with_lint=True))
            lint = run_lint(tmp_lint, spec)
            if lint is None:
                report("warn", "layout lint produced no result (page script did not finish)")
            else:
                if lint.get("error"):
                    report("warn", "layout lint error: " + lint["error"])
                findings = [("overflow", "content overflows its box"), ("svgText", "SVG text clipped"),
                            ("img", "image failed to load"), ("outside", "outside the page")]
                p = lint.get("page") or {}
                if p and (p["scrollW"] > p["W"] + 1 or p["scrollH"] > p["H"] + 1):
                    report("fail", f"page content {p['scrollW']} x {p['scrollH']} px exceeds page {p['W']:.0f} x {p['H']:.0f} px")
                bad = 0
                for key, label in findings:
                    for item in lint.get(key, []):
                        bad += 1
                        report("fail" if key == "img" else "warn", f"{label}: {item}")
                if not bad and not lint.get("error"):
                    report("ok", "layout lint clean (no overflow, clipped SVG text, broken images, or off-page text)")

        if spec["mode"] == "print":
            pdf = os.path.join(out_dir, f"{name}.pdf")
            if not print_pdf(tmp, pdf):
                report("fail", "browser did not produce the PDF")
            else:
                print(f"  [ok] {pdf}")
                check_pdf(pdf, spec, report)
                if not args.no_png:
                    png = os.path.join(out_dir, f"{name}.png")
                    ppm = poppler_pdftoppm()
                    done = False
                    if ppm:
                        base = png[:-4]
                        subprocess.run([ppm, "-r", f"{spec['dpi']:g}", "-png", "-singlefile", pdf, base], capture_output=True)
                        done = os.path.exists(png)
                        how = "rasterised from the PDF with poppler"
                    if not done:
                        scale = spec["dpi"] / 96
                        done = screenshot(tmp, png, round(spec["w_px"]), round(spec["h_px"]), scale)
                        how = "browser screenshot fallback (no poppler)"
                    if done:
                        print(f"  [ok] {png}  ({how})")
                        finish_png(png, spec["dpi"], report)
                    else:
                        report("fail", "PNG was not produced (poppler and browser screenshot both failed)")
        else:
            # Pixel mode: the PNG is the exact-size deliverable; the PDF is printed from the same
            # source for the text-size check (it applies SVG scaling) and as a vector export.
            pdf = os.path.join(out_dir, f"{name}.pdf")
            if not print_pdf(tmp, pdf):
                report("fail", "browser did not produce the PDF")
            else:
                print(f"  [ok] {pdf}")
                check_pdf(pdf, spec, report)
            png = os.path.join(out_dir, f"{name}.png")
            w, h = round(spec["w_px"]), round(spec["h_px"])
            if screenshot(tmp, png, w, h, 1.0):
                print(f"  [ok] {png}")
                finish_png(png, None, report, expect_px=(w, h))
            else:
                report("fail", "browser did not produce the PNG")
        png = os.path.join(out_dir, f"{name}.png")
        if args.tiff and os.path.exists(png):
            from PIL import Image
            tif = os.path.join(out_dir, f"{name}.tif")
            with Image.open(png) as im:
                im.convert("RGB").save(tif, compression="tiff_lzw", dpi=(spec["dpi"], spec["dpi"]) if spec["mode"] == "print" else None)
            print(f"  [ok] {tif}  (TIFF, LZW, RGB, from the PNG)")
    finally:
        for t in (tmp, tmp_lint):
            if os.path.exists(t):
                os.remove(t)

    print(f"  checks: {results['ok']} ok, {results['warn']} warn, {results['fail']} fail  (the .png/.pdf still need to be looked at)")
    return results


def scaffold(template, dest):
    tpl = os.path.join(TEMPLATE_DIR, f"{template}.html")
    css = os.path.join(TEMPLATE_DIR, "base.css")
    if not os.path.exists(tpl):
        names = sorted(os.path.splitext(f)[0] for f in os.listdir(TEMPLATE_DIR) if f.endswith(".html"))
        raise SystemExit(f"no template {template!r}; available: {', '.join(names)}")
    dest = os.path.abspath(dest)
    if os.path.exists(dest):
        raise SystemExit(f"{dest} already exists - not overwriting")
    with open(tpl, "r", encoding="utf-8") as f:
        text = f.read()
    with open(css, "r", encoding="utf-8") as f:
        base = f.read()
    text = text.replace("/*ARTI_BASE_CSS*/", base)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"arti-compose: scaffolded {dest} from template {template} (base.css inlined, so the file is self-contained)")


def main():
    ap = argparse.ArgumentParser(description="HTML figure source -> vector PDF + PNG, with checks")
    ap.add_argument("--src", required=True, help="path to the figure HTML source")
    ap.add_argument("--out-dir", default=".", help="output directory for .pdf/.png")
    ap.add_argument("--new", metavar="TEMPLATE", help="scaffold --src from a template instead of rendering")
    ap.add_argument("--width"), ap.add_argument("--height")
    ap.add_argument("--dpi", type=float), ap.add_argument("--min-pt", type=float)
    ap.add_argument("--min-px", type=float, help="pixel mode: smallest allowed text size in px (default 24)")
    ap.add_argument("--tiff", action="store_true", help="also write <name>.tif (LZW) from the PNG")
    ap.add_argument("--mode", choices=["print", "pixel"])
    ap.add_argument("--no-png", action="store_true"), ap.add_argument("--no-lint", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 2 if any check warns or fails")
    args = ap.parse_args()
    if args.new:
        scaffold(args.new, args.src)
        return
    res = compose(args.src, args.out_dir, args)
    if res["fail"] or (args.strict and res["warn"]):
        sys.exit(2)


if __name__ == "__main__":
    main()
