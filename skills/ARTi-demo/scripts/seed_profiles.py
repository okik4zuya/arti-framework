"""Install the demo researcher profile and the demo voice profile, only where nothing exists yet.

    python.exe scripts/seed_profiles.py

Never overwrites: a real researcher profile (or an existing voice profile of the same name) is left untouched.
Prints one JSON object describing what was done. The profile skills read these files as normal, so the unattended
demo needs no interview. Replace them later with the real ones (ARTi-setup Workflow A, ARTi-writing Stage 0).
"""
import json
import os
import re
import shutil
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ARTI_HOME, SKILL_DIR  # noqa: E402

CATALOG_HEADER = """# Voice Profile Catalog

One row per Voice Profile that exists under `~/.arti/voice-profiles/`. ARTi-writing's Stage 0
selection step reads this file: if more than one profile is listed, it asks the researcher which
to use for the current project before proceeding, and records the choice in that project's Journal
Profile Block B.

| Profile | Type (flat template / pointer / multi-file corpus) | Field | Source | Last confirmed |
|---|---|---|---|---|
"""
ROW = "| [demo-generic.md](demo-generic.md) | Flat template | Any field (neutral academic English) | Hand-written placeholder shipped with the ARTi-demo skill; not from any researcher's papers | %s |\n"

actions = []


def copy_if_missing(src, dst, label):
    if dst.exists():
        actions.append({"item": label, "action": "kept", "path": str(dst)})
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    actions.append({"item": label, "action": "installed", "path": str(dst)})


copy_if_missing(SKILL_DIR / "references" / "demo-researcher-profile.md",
                ARTI_HOME / "memory" / "researcher-profile.md", "researcher profile")
copy_if_missing(SKILL_DIR / "references" / "demo-voice-profile.md",
                ARTI_HOME / "voice-profiles" / "demo-generic.md", "voice profile demo-generic")

catalog = ARTI_HOME / "voice-profiles" / "00-INDEX.md"
today = date.today().isoformat()
if not catalog.exists():
    catalog.write_text(CATALOG_HEADER + ROW % today + "\n---\n\n## Change log\n- %s - created by ARTi-demo with one row.\n" % today,
                       encoding="utf-8")
    actions.append({"item": "voice catalog", "action": "created", "path": str(catalog)})
else:
    text = catalog.read_text(encoding="utf-8")
    if "demo-generic" in text:
        actions.append({"item": "voice catalog", "action": "kept", "path": str(catalog)})
    else:
        lines = text.split("\n")
        last_row = max((i for i, l in enumerate(lines) if re.match(r"^\|.*\|\s*$", l)), default=None)
        if last_row is None:
            text = text.rstrip("\n") + "\n\n" + CATALOG_HEADER + ROW % today
        else:
            lines.insert(last_row + 1, (ROW % today).rstrip("\n"))
            text = "\n".join(lines)
        catalog.write_text(text, encoding="utf-8")
        actions.append({"item": "voice catalog", "action": "row added", "path": str(catalog)})

print(json.dumps({"ok": True, "actions": actions}, ensure_ascii=False, indent=2))
