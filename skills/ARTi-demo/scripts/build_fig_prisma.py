"""Figure 1: the PRISMA-ScR flow diagram, filled from data/prisma-counts.json and rendered with arti-compose.

    python.exe scripts/build_fig_prisma.py --project P

Reads data/prisma-counts.json (screen.py counts). Writes figures/src/Fig_1.html (the reproducibility record), then
figures/Fig_1.pdf (vector) and figures/Fig_1.png (600 dpi) through `arti-compose`; its WARN/FAIL lines are printed as they
are. Why compose and not arti-render: the diagram lane only writes an editable .drawio, and a .drawio cannot be embedded in the
.docx without draw.io desktop; compose renders with Edge/Chrome, which every machine that runs the demo has.
"""
import argparse
import html
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ARTI_HOME, PY, SKILL_DIR, TOOLS, read_json  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
a = ap.parse_args()
project = Path(a.project)
c = read_json(project / "data" / "prisma-counts.json")
if not c:
    print("FAIL: data/prisma-counts.json is missing: run screen.py counts first")
    sys.exit(1)


def n(v):
    return "{:,}".format(int(v))


src_names = {"openalex": "OpenAlex", "s2": "Semantic Scholar", "semanticscholar": "Semantic Scholar", "scholar": "Google Scholar"}
by_source = c.get("identified_by_source") or {}
id_sources = "; ".join("%s n = %s" % (src_names.get(k, k), n(v)) for k, v in by_source.items()) or " "
def reason_items(pairs):
    return "".join("<li>%s (n = %s)</li>" % (html.escape(str(r)), n(v)) for r, v in (pairs or [])[:3]) or "<li>none recorded</li>"


values = {
    "identified": n(c["identified_total"]), "id_sources": html.escape(id_sources), "dups": n(c["duplicates_removed"]),
    "screened": n(c["screened"]), "excl_ta": n(c["excluded_title_abstract"]), "eligible": n(c["assessed_for_eligibility"]),
    "excl_elig": n(c["excluded_eligibility"]), "reasons": reason_items(c.get("top_exclusion_reasons_eligibility")),
    "reasons_ta": reason_items(c.get("top_exclusion_reasons_title_abstract")), "included": n(c["included"]),
    "inc_full": n(c["included_fulltext"]), "inc_abs": n(c["included_abstract_only"]),
}
text = (SKILL_DIR / "templates" / "prisma-flow.html").read_text(encoding="utf-8")
base_css = (ARTI_HOME / "skills" / "ARTi-figure" / "templates" / "base.css").read_text(encoding="utf-8")
text = text.replace("/*ARTI_BASE_CSS*/", base_css)
for k, v in values.items():
    text = text.replace("{{%s}}" % k, v)
if "{{" in text.split("</style>")[1]:
    print("FAIL: unfilled placeholder left in the page")
    sys.exit(1)
src = project / "figures" / "src" / "Fig_1.html"
src.parent.mkdir(parents=True, exist_ok=True)
src.write_text(text, encoding="utf-8")
r = subprocess.run([PY, str(TOOLS / "arti-compose" / "compose.py"), "--src", str(src), "--out-dir", str(project / "figures")],
                   capture_output=True, text=True)
print((r.stdout + r.stderr).strip())
sys.exit(0 if r.returncode == 0 else 1)
