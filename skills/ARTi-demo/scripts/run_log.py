"""The demo's run log: one JSON state file plus a readable Markdown copy, in the project root.

    python.exe scripts/run_log.py init    --project P --topic "..."
    python.exe scripts/run_log.py phase   --project P --n 3 --name "Screening" --status done|partial|skipped --note "..."
    python.exe scripts/run_log.py decision --project P --text "chose journal X because ..."
    python.exe scripts/run_log.py problem --project P --text "Scholar cooled down; route skipped"
    python.exe scripts/run_log.py status  --project P

`phase` closes a phase: it starts when the previous one ended (or when the run started) and ends now, so the minutes are
real. `status` prints the last finished phase, which is where an interrupted run resumes. Files: `demo-run-log.json`
(state, read by scoreboard.py) and `demo-run-log.md` (for people).
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

FMT = "%Y-%m-%d %H:%M:%S"


def paths(project):
    p = Path(project)
    return p / "demo-run-log.json", p / "demo-run-log.md"


def load(project):
    j, _ = paths(project)
    try:
        return json.loads(j.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(project, state):
    j, m = paths(project)
    j.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# ARTi demo run log", "", "Topic: %s" % state["topic"], "Started: %s" % state["started"], "",
             "| Phase | Name | Start | End | Minutes | Status | Note |", "|---|---|---|---|---|---|---|"]
    for p in state["phases"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (p["n"], p["name"], p["start"][11:16], p["end"][11:16], p["minutes"], p["status"], p["note"].replace("|", "/")))
    lines += ["", "## Decisions made without the researcher", ""] + ["- %s %s" % (d["at"][11:16], d["text"]) for d in state["decisions"]]
    lines += ["", "## Problems and fallbacks", ""] + ["- %s %s" % (d["at"][11:16], d["text"]) for d in state["problems"]]
    m.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stamp():
    return datetime.now().strftime(FMT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "phase", "decision", "problem", "status"])
    ap.add_argument("--project", required=True)
    ap.add_argument("--topic")
    ap.add_argument("--n", type=int)
    ap.add_argument("--name")
    ap.add_argument("--status", default="done")
    ap.add_argument("--note", default="")
    ap.add_argument("--text")
    a = ap.parse_args()
    state = load(a.project)
    if a.cmd == "init":
        if state and not a.topic:
            print(json.dumps({"ok": True, "resumed": True, "last_phase": state["phases"][-1]["n"] if state["phases"] else -1}))
            return 0
        state = {"topic": a.topic or "(not set)", "started": stamp(), "phases": [], "decisions": [], "problems": []}
        save(a.project, state)
        print(json.dumps({"ok": True, "resumed": False, "started": state["started"]}))
        return 0
    if state is None:
        print(json.dumps({"ok": False, "error": "no run log here: run `init` first"}))
        return 1
    if a.cmd == "phase":
        if a.n is None or not a.name:
            print(json.dumps({"ok": False, "error": "--n and --name are required"}))
            return 1
        start = state["phases"][-1]["end"] if state["phases"] else state["started"]
        end = stamp()
        minutes = round((datetime.strptime(end, FMT) - datetime.strptime(start, FMT)).total_seconds() / 60.0, 1)
        state["phases"] = [p for p in state["phases"] if p["n"] != a.n]
        state["phases"].append({"n": a.n, "name": a.name, "start": start, "end": end, "minutes": minutes, "status": a.status, "note": a.note})
        state["phases"].sort(key=lambda p: p["n"])
    elif a.cmd in ("decision", "problem"):
        state["decisions" if a.cmd == "decision" else "problems"].append({"at": stamp(), "text": a.text or ""})
    save(a.project, state)
    last = state["phases"][-1]["n"] if state["phases"] else -1
    print(json.dumps({"ok": True, "last_phase": last, "phases": len(state["phases"]), "problems": len(state["problems"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
