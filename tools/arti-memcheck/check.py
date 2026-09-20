#!/usr/bin/env python3
"""
arti-memcheck - composition checker for an ARTi project's T0 memory set

T0 is the four files auto-loaded into context every session: CLAUDE.md,
memory/MEMORY.md, memory/todo-list.md, memory/status.md. The defect this
catches is composition, not size: stacked "Current state" blocks, an
oversized Current-state block (it must be a short pointer to a memories/
topic file, not the report itself), a change log that has eaten its own
file, a "## Change log" section in status.md/todo-list.md at all (git
history plus the linked topic file's own change log cover it - these two
files don't get a second one), prose in a checklist-only file (including
prose smuggled in as indented continuation lines under a checkbox item,
not just bare stray lines), and references left dangling by a directory
move. Those are ERRORs at any size.

Size is a WARN only. A large T0 made entirely of live state is a pass - the
checker must never create pressure to delete load-bearing content.

Usage:
    python check.py [--project DIR] [--all] [--budget N] [--hook]

Exit 0 clean - 1 findings - 2 usage/IO error.
"""
import argparse
import os
import re
import sys

ARTI_HOME = os.path.join(os.path.expanduser("~"), ".arti")
PROJECT_INDEX_PATH = os.path.join(ARTI_HOME, "memory", "project-index.md")
TEMPLATE_PATH = os.path.join(
    ARTI_HOME, "skills", "ARTi-setup", "references", "project-claude-template.md"
)

T0 = ["CLAUDE.md", "memory/MEMORY.md", "memory/todo-list.md", "memory/status.md"]

DEFAULT_BUDGET = 20480
PER_FILE_WARN = 8192
CHANGELOG_RATIO = 0.35
CHANGELOG_WARN_ENTRIES = 12
CHANGELOG_ERR_ENTRIES = 20
FOLDED_ENTRY_CHARS = 120
INDEX_LINE_CHARS = 200
PROSE_WARN = 0
PROSE_ERR = 5
CURRENT_STATE_WARN_CHARS = 800
CURRENT_STATE_ERR_CHARS = 2000
TODO_CONTINUATION_WARN_CHARS = 200
TODO_CONTINUATION_ERR_CHARS = 400

FENCE = "<!-- arti: local additions below"
TEMPLATE_MARKER = "arti-claude-template:"

SKIP_DIRS = {".git", "python", "node_modules", "__pycache__", ".venv", "venv", "exports"}

# ERROR and non-size WARN drive the exit code; SIZE and INFO never do.
ERROR, WARN, SIZE, INFO = "ERROR", "WARN", "SIZE", "INFO"


class Finding(object):
    def __init__(self, level, path, message):
        self.level = level
        self.path = path
        self.message = message

    def __str__(self):
        return "  [%-5s] %s: %s" % (self.level, self.path, self.message)


def read_text(path):
    """Returns (text, None) or (None, reason). Google Drive holds real file
    locks here, so every read is guarded - a traceback in a SessionStart hook
    is unacceptable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), None
    except OSError as e:
        return None, "%s" % (e.strerror or e)


def file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return None


# --------------------------------------------------------------------------
# section helpers
# --------------------------------------------------------------------------

def sections(lines):
    """Yields (heading_text, start_index, end_index) for each `## ` section."""
    heads = [i for i, l in enumerate(lines) if l.startswith("## ")]
    for n, i in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        yield lines[i][3:].strip(), i, end


def changelog_span(lines):
    for name, start, end in sections(lines):
        if name.lower().startswith("change log"):
            return start, end
    return None, None


def fold_entries(lines):
    """Collapses `- ` entries plus their indented continuation lines into one
    string each, so the 120-char cap measures the whole entry."""
    out = []
    for line in lines:
        if line.startswith("- "):
            out.append(line[2:].strip())
        elif out and line.strip() and (line.startswith("  ") or line.startswith("\t")):
            out[-1] += " " + line.strip()
    return out


# --------------------------------------------------------------------------
# check A - size (WARN only, never ERROR)
# --------------------------------------------------------------------------

def check_size(project, budget, findings, sizes):
    total = 0
    for rel in T0:
        n = sizes.get(rel)
        if n is None:
            continue
        total += n
        if n > PER_FILE_WARN:
            findings.append(
                Finding(SIZE, rel, "%d B, over the %d B per-file smell threshold" % (n, PER_FILE_WARN))
            )
    if total > budget:
        pct = int(round(100.0 * total / budget))
        findings.append(
            Finding(SIZE, "T0", "total %d B / %d B (%d%%) - look at composition, not the number" % (total, budget, pct))
        )
    return total


# --------------------------------------------------------------------------
# check B - structure
# --------------------------------------------------------------------------

RE_CURRENT_STATE = re.compile(r"^##\s+Current state\b")
RE_SESSION_BLOCK = re.compile(r"^\*\*Session\s+\d+")


def check_status(rel, text, findings):
    lines = text.splitlines()
    hits = [i + 1 for i, l in enumerate(lines) if RE_CURRENT_STATE.match(l)]
    if len(hits) > 1:
        findings.append(
            Finding(ERROR, rel, "%d '## Current state' blocks at lines %s - the rule is one, overwritten in place"
                    % (len(hits), ", ".join(str(h) for h in hits)))
        )
    elif not hits:
        findings.append(Finding(ERROR, rel, "no '## Current state' block"))
    elif len(hits) == 1:
        # Current state must be a short pointer to a memories/ topic file, not
        # the report itself - this is the exact defect that let status.md grow
        # to 21.5K in the ARTi framework project before this check existed.
        start = hits[0]  # 1-indexed line of the heading; body starts right after
        next_head = next((i for i, l in enumerate(lines) if i > start - 1 and l.startswith("## ")), len(lines))
        body = "\n".join(lines[start:next_head])
        n = len(body.encode("utf-8"))
        # INFO, not WARN/ERROR (neither fails a check - see fails() below): this
        # check landed 2026-09-20 and most existing projects predate the
        # lean-pointer convention it enforces. Nudge them toward it without
        # failing every one of their sessions until they're migrated - a new
        # project scaffolded from the updated template starts clean and this
        # never fires for it.
        if n > CURRENT_STATE_ERR_CHARS:
            findings.append(
                Finding(INFO, rel, "'Current state' block is %d B (hard cap %d) - it must be a short pointer "
                                    "(what changed + a [[topic-file]] link), not the report itself"
                        % (n, CURRENT_STATE_ERR_CHARS))
            )
        elif n > CURRENT_STATE_WARN_CHARS:
            findings.append(
                Finding(INFO, rel, "'Current state' block is %d B (soft cap %d) - move detail into a "
                                    "memories/ topic file and link it" % (n, CURRENT_STATE_WARN_CHARS))
            )

    archive = next((i for i, l in enumerate(lines) if l.startswith("## Archive")), len(lines))
    for i, l in enumerate(lines[:archive]):
        if RE_SESSION_BLOCK.match(l):
            # A bold "**Session N ..." opening the Current state block is that
            # block's own lead sentence (house style), not a stacked block.
            prev = next((lines[j] for j in range(i - 1, -1, -1) if lines[j].strip()), "")
            if RE_CURRENT_STATE.match(prev):
                continue
            findings.append(
                Finding(WARN, rel, "line %d: bold '**Session N' pseudo-block in the live region - "
                                   "collapse to a one-line Archive entry" % (i + 1))
            )


RE_CHECKBOX = re.compile(r"^(\s*)-\s\[[ xX]\]")


def check_todo(rel, text, findings):
    lines = text.splitlines()
    bad = []
    long_items = []
    for name, start, end in sections(lines):
        low = name.lower()
        if low.startswith("change log") or low.startswith("archive"):
            continue
        item_start = None
        item_chars = 0
        for i in range(start + 1, end + 1):
            l = lines[i] if i < end else ""
            is_checkbox = i < end and bool(RE_CHECKBOX.match(l))
            is_continuation = (
                i < end and l.strip() and (l.startswith("  ") or l.startswith("\t"))
                and not is_checkbox
            )
            if is_continuation:
                # Indented text under a checkbox item is allowed (a short
                # blocking-condition note or a nested sub-item), but a
                # multi-paragraph narrative smuggled in this way is exactly
                # the defect that let todo-list.md balloon undetected - cap
                # its total length same as a folded change-log entry.
                item_chars += len(l.strip()) + 1
                continue
            # Reached a checkbox line, a blank line, a table row, or the
            # section end - close out whatever item was accumulating.
            if item_start is not None and item_chars > 0:
                if item_chars > TODO_CONTINUATION_ERR_CHARS:
                    long_items.append((item_start, item_chars, ERROR))
                elif item_chars > TODO_CONTINUATION_WARN_CHARS:
                    long_items.append((item_start, item_chars, WARN))
            item_chars = 0
            item_start = None
            if is_checkbox:
                item_start = i + 1
                continue
            if not l.strip():
                continue
            if l.lstrip().startswith("|"):
                continue
            bad.append(i + 1)
    if len(bad) > PROSE_ERR:
        findings.append(
            Finding(ERROR, rel, "%d non-checklist lines in task sections (lines %s...) - this file is checklist-only"
                    % (len(bad), ", ".join(str(b) for b in bad[:5])))
        )
    elif len(bad) > PROSE_WARN:
        findings.append(
            Finding(WARN, rel, "%d non-checklist line(s) in task sections (lines %s)"
                    % (len(bad), ", ".join(str(b) for b in bad)))
        )
    for item_start, item_chars, level in long_items:
        findings.append(
            Finding(level, rel, "line %d: checklist item's continuation is %d chars - narrative belongs in a "
                                 "memories/ topic file, link it with [[slug]] instead" % (item_start, item_chars))
        )


def check_no_changelog(rel, text, findings):
    """status.md and todo-list.md don't get their own '## Change log' section -
    git history covers edits to the tracker itself, and the substantive record
    already lives in the memories/ topic file each entry links to. A second
    change log here is exactly the kind of bookkeeping-about-bookkeeping that
    grew status.md/todo-list.md past budget in the first place.

    INFO, not WARN/ERROR (neither fails a check - see fails() below): this
    rule landed 2026-09-20 and most existing projects predate it. Nudge them
    toward dropping the section without failing every one of their sessions
    until they're migrated - a new project scaffolded from the updated
    template starts clean and this never fires for it."""
    lines = text.splitlines()
    start, _ = changelog_span(lines)
    if start is not None:
        findings.append(
            Finding(INFO, rel, "line %d: '## Change log' section not allowed here - git history plus the "
                                "linked topic file's own change log already cover it" % (start + 1))
        )


def check_changelog(rel, text, size, findings):
    lines = text.splitlines()
    start, end = changelog_span(lines)
    if start is None:
        return
    body = lines[start:end]
    entries = fold_entries(body)
    if len(entries) > CHANGELOG_ERR_ENTRIES:
        findings.append(
            Finding(ERROR, rel, "change log has %d entries (cap ~10) - fold the old ones into one line" % len(entries))
        )
    elif len(entries) > CHANGELOG_WARN_ENTRIES:
        findings.append(Finding(WARN, rel, "change log has %d entries (cap ~10)" % len(entries)))

    long_entries = [e for e in entries if len(e) > FOLDED_ENTRY_CHARS]
    if long_entries:
        findings.append(
            Finding(WARN, rel, "%d change-log entr%s over %d chars"
                    % (len(long_entries), "y" if len(long_entries) == 1 else "ies", FOLDED_ENTRY_CHARS))
        )

    cl_bytes = len("\n".join(body).encode("utf-8"))
    if size and float(cl_bytes) / size > CHANGELOG_RATIO:
        findings.append(
            Finding(WARN, rel, "change log dominates file: %d of %d B (%d%%)"
                    % (cl_bytes, size, int(round(100.0 * cl_bytes / size))))
        )


def check_memory_index(rel, text, findings):
    lines = text.splitlines()
    start, _ = changelog_span(lines)
    limit = start if start is not None else len(lines)
    for i in range(limit):
        l = lines[i]
        if not l.startswith("- "):
            continue
        entry = l[2:].strip()
        j = i + 1
        while j < limit and lines[j].strip() and (lines[j].startswith("  ") or lines[j].startswith("\t")):
            entry += " " + lines[j].strip()
            j += 1
        if len(entry) > INDEX_LINE_CHARS:
            findings.append(
                Finding(WARN, rel, "line %d: index line %d chars (cap %d) - it is restating the linked file"
                        % (i + 1, len(entry), INDEX_LINE_CHARS))
            )


# --------------------------------------------------------------------------
# check C - references
# --------------------------------------------------------------------------

RE_CODE = re.compile(r"`([^`\n]+)`")
RE_MDLINK = re.compile(r"\]\(([^)\s]+)\)")
RE_WIKI = re.compile(r"\[\[([^\]\n]+)\]\]")

BAD_CHARS = set("[]{}<>|*?\"")


def ref_candidates(text):
    """Paths in this corpus are always in backticks or markdown links, so
    scanning those two forms instead of free text keeps false positives near
    zero.

    A *bare* filename is deliberately not a reference. `gap-map.md` inside a
    sentence describing what `idea/` holds is prose naming a file, not a path
    to resolve; treating it as one turns this check into noise. Only
    home-anchored paths (`~/.arti/...`) and multi-segment relative paths are
    resolvable claims about where something lives. Placeholders
    (`manuscript_draft[N]_[date].md`) and elisions (`udugama-2022-...md`) are
    dropped.
    """
    out = []
    for m in RE_CODE.finditer(text):
        out.append(m.group(1).strip())
    for m in RE_MDLINK.finditer(text):
        out.append(m.group(1).strip())
    cands = []
    for raw in out:
        r = raw.strip().rstrip(",.;:")
        if not r or " " in r or "..." in r or any(c in BAD_CHARS for c in r):
            continue
        if r.startswith("~/"):
            cands.append(r)
            continue
        parts = [p for p in re.split(r"[\\/]", r) if p]
        if len(parts) < 2:
            continue
        last = parts[-1]
        if r.endswith("/") or r.endswith("\\") or "." in last:
            cands.append(r)
    return cands


def resolve_ref(ref, project, file_dir):
    """Returns an existing path, or None."""
    r = ref.replace("\\", "/")
    if r.startswith("~/"):
        p = os.path.join(os.path.expanduser("~"), r[2:])
        return p if os.path.exists(p) else None
    if os.path.isabs(r) or re.match(r"^[A-Za-z]:", r):
        return r if os.path.exists(r) else None
    for base in (file_dir, project, os.path.join(project, "memory")):
        p = os.path.join(base, r)
        if os.path.exists(p):
            return p
    return None


def build_basename_index(roots):
    idx = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                idx.setdefault(fn, set()).add(os.path.join(dirpath, fn))
    return idx


def check_refs(project, texts, findings):
    unresolved = []
    for rel, text in texts.items():
        if text is None:
            continue
        if rel == "CLAUDE.md" and TEMPLATE_MARKER in text:
            # The canonical region describes folder *conventions* ("data/instruments/ holds
            # ...", "figure-register.md, seeded on first ARTi-figure use"), not paths that
            # must exist today. It is identical in every project, so checking it per-project
            # yields the same false finding N times. Verify it once at the template, and
            # check only the project-owned additions below the fence.
            _, text = split_fence(text)
            if not text:
                continue
        file_dir = os.path.dirname(os.path.join(project, rel))
        for ref in ref_candidates(text):
            if resolve_ref(ref, project, file_dir) is None:
                unresolved.append((rel, ref))
        # Strip inline code first: `[[slug]]` in the frontmatter convention
        # prose is documentation of the link syntax, not a link.
        prose = RE_CODE.sub(" ", text)
        for m in RE_WIKI.finditer(prose):
            slug = m.group(1).strip()
            hit = False
            for cand in ("memory/memories/%s.md" % slug, "memory/%s.md" % slug, "%s.md" % slug):
                if os.path.exists(os.path.join(project, cand)):
                    hit = True
                    break
            if not hit:
                unresolved.append((rel, "[[%s]]" % slug))

    if not unresolved:
        return

    # Second pass: a ref that only moved is a patch line, not a nag. This
    # distinction is the whole point of the check.
    idx = build_basename_index([ARTI_HOME, project])
    seen = set()
    for rel, ref in unresolved:
        key = (rel, ref)
        if key in seen:
            continue
        seen.add(key)
        base = os.path.basename(ref.replace("\\", "/").rstrip("/"))
        if base.startswith("[["):
            base = base[2:-2] + ".md"
        hits = idx.get(base, set())
        if len(hits) == 1:
            found = list(hits)[0]
            findings.append(Finding(ERROR, rel, "MOVED  %s -> %s" % (ref, display_path(found))))
        else:
            findings.append(Finding(ERROR, rel, "MISSING  %s" % ref))


def display_path(p):
    home = os.path.expanduser("~")
    if p.startswith(home):
        return "~" + p[len(home):].replace("\\", "/")
    return p.replace("\\", "/")


# --------------------------------------------------------------------------
# check D - template conformance
# --------------------------------------------------------------------------

def split_fence(text):
    i = text.find(FENCE)
    if i < 0:
        return text, None
    j = text.find("\n", i)
    above = text[:i]
    below = text[j + 1:] if j >= 0 else ""
    return above, below


def norm(block):
    return [l.rstrip() for l in block.strip().splitlines()]


def check_template(rel, text, findings):
    if TEMPLATE_MARKER not in text:
        findings.append(Finding(INFO, rel, "no template marker - not generated from the canonical template"))
        return
    tmpl, err = read_text(TEMPLATE_PATH)
    if tmpl is None:
        findings.append(Finding(INFO, rel, "canonical template unreadable (%s) - conformance not checked" % err))
        return

    above, below = split_fence(text)
    if below is None:
        findings.append(Finding(ERROR, rel, "ownership fence missing - add '%s ... -->' before any local additions" % FENCE))
        below = ""
    t_above, _ = split_fence(tmpl)

    # Recover the substituted name by matching the file's H1 against the
    # template's, so an H1 with text around the placeholder still works.
    name = ""
    t_h1 = next((l for l in t_above.splitlines() if l.startswith("# ")), "")
    f_h1 = next((l for l in text.splitlines() if l.startswith("# ")), "")
    if "{{PROJECT_NAME}}" in t_h1:
        pat = "^" + "(.+)".join(re.escape(p) for p in t_h1.split("{{PROJECT_NAME}}")) + "$"
        m = re.match(pat, f_h1)
        if m:
            name = m.group(1)
    expected = t_above.replace("{{PROJECT_NAME}}", name)

    exp_heads = [l for l in norm(expected) if l.startswith("## ")]
    got_heads = [l for l in norm(above) if l.startswith("## ")]
    missing = [h for h in exp_heads if h not in got_heads]
    if missing:
        findings.append(
            Finding(ERROR, rel, "canonical heading(s) missing above the fence: %s" % ", ".join(missing))
        )

    if norm(above) != norm(expected):
        findings.append(
            Finding(ERROR, rel, "text above the fence differs from the canonical template - "
                                "move the change into the template or below the fence")
        )

    if below.strip():
        findings.append(
            Finding(INFO, rel, "%d B of local additions below the fence (preserved on regeneration)"
                    % len(below.strip().encode("utf-8")))
        )


# --------------------------------------------------------------------------
# per-project driver
# --------------------------------------------------------------------------

def is_project(project):
    return os.path.exists(os.path.join(project, "memory", "MEMORY.md"))


def check_project(project, budget):
    """Returns (findings, total_bytes, sizes)."""
    findings = []
    sizes = {}
    texts = {}
    for rel in T0:
        path = os.path.join(project, rel)
        n = file_size(path)
        if n is None:
            findings.append(Finding(ERROR, rel, "T0 file missing"))
            continue
        sizes[rel] = n
        text, err = read_text(path)
        if text is None:
            print("[skip] %s: %s" % (path, err))
            continue
        texts[rel] = text

    total = check_size(project, budget, findings, sizes)

    NO_CHANGELOG_FILES = ("memory/status.md", "memory/todo-list.md")
    for rel, text in texts.items():
        if rel in NO_CHANGELOG_FILES:
            check_no_changelog(rel, text, findings)
        else:
            check_changelog(rel, text, sizes.get(rel, 0), findings)
    if "memory/status.md" in texts:
        check_status("memory/status.md", texts["memory/status.md"], findings)
    if "memory/todo-list.md" in texts:
        check_todo("memory/todo-list.md", texts["memory/todo-list.md"], findings)
    if "memory/MEMORY.md" in texts:
        check_memory_index("memory/MEMORY.md", texts["memory/MEMORY.md"], findings)

    check_refs(project, texts, findings)

    if "CLAUDE.md" in texts:
        check_template("CLAUDE.md", texts["CLAUDE.md"], findings)

    return findings, total, sizes


def fails(findings):
    """Size never fails a check on its own; composition carries the verdict."""
    return any(f.level in (ERROR, WARN) for f in findings)


def imperative(project, findings):
    """One acted-on line beats a percentage that gets noted and forgotten."""
    parts = []
    stacked = [f for f in findings if "Current state' blocks" in f.message]
    if stacked:
        n = re.search(r"^(\d+)", stacked[0].message)
        parts.append("%s stacked \"Current state\" blocks" % (n.group(1) if n else "several"))
    bad_refs = len([f for f in findings if f.message.startswith(("MOVED", "MISSING"))])
    if bad_refs:
        parts.append("%d bad ref%s" % (bad_refs, "" if bad_refs == 1 else "s"))
    dom = [f for f in findings if "change log dominates" in f.message]
    if dom:
        parts.append("%d change log%s dominating %s"
                     % (len(dom), "" if len(dom) == 1 else "s", "its file" if len(dom) == 1 else "their files"))
    prose = [f for f in findings if "non-checklist" in f.message]
    if prose:
        parts.append("prose in todo-list.md")
    long_items = [f for f in findings if "checklist item's continuation" in f.message]
    if long_items:
        parts.append("%d over-long todo-list.md item(s)" % len(long_items))
    oversized_state = [f for f in findings if "'Current state' block is" in f.message]
    if oversized_state:
        parts.append("oversized Current-state block")
    stray_changelog = [f for f in findings if "'## Change log' section not allowed" in f.message]
    if stray_changelog:
        parts.append("stray Change log in status.md/todo-list.md")
    drift = [f for f in findings if "differs from the canonical template" in f.message]
    if drift:
        parts.append("CLAUDE.md drifted from the template")
    if not parts:
        parts.append("%d composition finding(s)" % len([f for f in findings if f.level in (ERROR, WARN)]))
    return "Compact %s memory before other work - %s." % (os.path.basename(project.rstrip("\\/")), ", ".join(parts))


def projects_from_project_index():
    out = []
    text, err = read_text(PROJECT_INDEX_PATH)
    if text is None:
        return out
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        p = cols[1]
        if os.path.isdir(p):
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description="Composition checker for an ARTi project's T0 memory set.")
    ap.add_argument("--project", default=None, help="project directory (default: cwd)")
    ap.add_argument("--all", action="store_true", help="every path in project-index.md, plus ~/.arti")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="T0 byte budget (default 20480)")
    ap.add_argument("--hook", action="store_true", help="summary mode: silent when clean, always exit 0")
    args = ap.parse_args()

    if args.all:
        targets = projects_from_project_index()
        if ARTI_HOME not in targets and os.path.isdir(ARTI_HOME):
            targets.append(ARTI_HOME)
    else:
        targets = [os.path.abspath(args.project or os.getcwd())]

    targets = [t for t in targets if is_project(t)]
    if not targets:
        if args.hook:
            return 0
        sys.stderr.write("arti-memcheck: not an ARTi project (no memory/MEMORY.md)\n")
        return 2

    any_fail = False
    for project in targets:
        try:
            findings, total, sizes = check_project(project, args.budget)
        except OSError as e:
            if args.hook:
                continue
            sys.stderr.write("arti-memcheck: %s: %s\n" % (project, e))
            return 2

        failed = fails(findings)
        any_fail = any_fail or failed

        if args.hook:
            if failed:
                print(imperative(project, findings))
            continue

        print("%s" % display_path(project))
        pct = int(round(100.0 * total / args.budget)) if args.budget else 0
        largest = max(sizes, key=lambda k: sizes[k]) if sizes else None
        for rel in T0:
            if rel in sizes:
                mark = "  <- largest" if rel == largest else ""
                print("  %-22s %7d B%s" % (rel, sizes[rel], mark))
        print("  %-22s %7d B  / %d B (%d%%)" % ("T0 total", total, args.budget, pct))
        if findings:
            print("")
            for level in (ERROR, WARN, SIZE, INFO):
                for f in findings:
                    if f.level == level:
                        print(str(f))
        print("")
        print("  %s" % ("FINDINGS" if failed else "clean"))
        print("")

    if args.hook:
        return 0
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
