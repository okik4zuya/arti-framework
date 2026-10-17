"""Create the standard ARTi paper-project layout (ARTi-setup Workflow B) for the demo, in one call.

    python.exe scripts/scaffold_project.py --path <working folder> --name "<project name>" [--no-register]

Uses the dashboard scaffolder (`dashboard/server/server.py: _scaffold_paper_folders`), the same code behind the
dashboard's "new paper project", so the folders, the memory trio and the root CLAUDE.md (rendered from
`ARTi-setup/references/project-claude-template.md`) are exactly what Workflow B produces. Every write is
missing-only. The project is then registered in the cross-project index with `arti-db project upsert`
(stage "Not started"), unless --no-register. Prints one JSON object.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ARTI_HOME, run_json, tool_cmd  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--path", required=True)
ap.add_argument("--name", required=True)
ap.add_argument("--no-register", action="store_true")
a = ap.parse_args()

project = Path(a.path).expanduser().resolve()
if ARTI_HOME.resolve() in (project, *project.parents):
    print(json.dumps({"ok": False, "error": "the project folder is inside the ARTi home (%s); open Claude Code in a separate empty folder" % ARTI_HOME}))
    sys.exit(1)
project.mkdir(parents=True, exist_ok=True)

server_dir = str(ARTI_HOME / "dashboard" / "server")
sys.path.insert(0, server_dir)
sys.path.insert(0, str(ARTI_HOME))
os.chdir(server_dir)
try:
    import server  # noqa: E402  (dashboard/server/server.py; importing it starts nothing)
except Exception as e:  # pragma: no cover - environment problem, reported not hidden
    print(json.dumps({"ok": False, "error": "cannot import the dashboard scaffolder: %s: %s" % (type(e).__name__, e)}))
    sys.exit(1)

server._scaffold_paper_folders(project, a.name)
result = {"ok": True, "project": str(project), "folders": sorted(p.name for p in project.iterdir() if p.is_dir()),
          "files": sorted(p.name for p in project.iterdir() if p.is_file())}

if not a.no_register:
    code, data, raw, err = run_json(tool_cmd("arti-db", "project", "upsert", "--project-path", str(project), "--topic", a.name,
                                             "--stage", "Not started", "--status", "Scaffolded (ARTi-demo)"))
    result["registered"] = bool(data and data.get("ok"))
    if not result["registered"]:
        result["register_error"] = (raw or err)[:300]
print(json.dumps(result, ensure_ascii=False, indent=2))
