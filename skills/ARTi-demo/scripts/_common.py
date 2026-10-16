"""Shared helpers for the ARTi-demo scripts. Standard library only (plus what the vendored Python has)."""
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
ARTI_HOME = Path(os.environ.get("ARTI_HOME") or Path(__file__).resolve().parents[3])
TOOLS = ARTI_HOME / "tools"
PY = sys.executable  # the scripts are always started with the vendored interpreter


def tool_cmd(tool, *args):
    return [PY, str(TOOLS / tool / "cli.py"), *[str(a) for a in args]]


def run_json(cmd, cwd=None, timeout=300):
    """Run a tool that prints one JSON object; return (exit_code, parsed_or_None, raw_stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=cwd, timeout=timeout)
    out = p.stdout.strip()
    try:
        data = json.loads(out) if out else None
    except ValueError:
        data = None
    return p.returncode, data, p.stdout, p.stderr


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def lit():
    """The arti-lit db module (in-process, same code the CLI runs)."""
    os.environ.setdefault("ARTI_HOME", str(ARTI_HOME))
    lit_dir = str(TOOLS / "arti-lit")
    if lit_dir not in sys.path:
        sys.path.insert(0, lit_dir)
    import db  # noqa: E402  (tools/arti-lit/db.py)
    return db


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def year_of(key):
    """author-year[a|b] key -> year string ('' when the key has none)."""
    parts = str(key).split("-")
    for p in reversed(parts):
        digits = "".join(ch for ch in p if ch.isdigit())
        if len(digits) == 4:
            return digits
    return ""
