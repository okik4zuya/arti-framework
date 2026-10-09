"""arti-annotate core: parse / mutate inline CriticMarkup annotations in a md file.

Format (see README.md for the spec):
    comment    {==span==}{>>#a3 open | note<<}
    suggestion {~~old~>new~~}{>>#a4 open | note<<}
    revised    {==new span==}{>>#a3 revised | was "old span" | note<<}

Everything inside fenced code blocks and inline code is ignored. The dashboard keeps a JS
mirror of this parser (dashboard/arti-dashboard.html); fixtures.json is the shared contract.
"""
import json
import re

_META = (r"(?P<meta>\{>>#(?P<id>a\d+) (?P<status>open|revised)"
         r'(?: \| was (?P<was>"(?:[^"\\]|\\.)*"))?'
         r"(?: \| (?P<note>.*?))?<<\})")
COMMENT_RE = re.compile(r"\{==(?P<text>(?:(?!==\}).)*)==\}" + _META, re.S)
SUGGEST_RE = re.compile(r"\{~~(?P<old>(?:(?!~>|~~\}).)*)~>(?P<new>(?:(?!~~\}).)*)~~\}" + _META, re.S)
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,}).*?(?:^[ \t]{0,3}\1[`~]*[ \t]*$|\Z)", re.S | re.M)
_INLINE_CODE_RE = re.compile(r"(`+)(?!`).+?(?<!`)\1(?!`)", re.S)


def _protected_ranges(text):
    ranges = [m.span() for m in _FENCE_RE.finditer(text)]
    for m in _INLINE_CODE_RE.finditer(text):
        if not any(s <= m.start() < e for s, e in ranges):
            ranges.append(m.span())
    return ranges


def _unquote_was(raw):
    return json.loads(raw) if raw else None


def quote_was(s):
    # "<<}" would end the meta block early; < decodes back through json.loads.
    return json.dumps(s, ensure_ascii=False).replace("<<}", "\\u003c<}")


def clean_note(note):
    return (note or "").replace("<<}", "< <}").strip()


def parse(text):
    """Return annotations in file order: dicts with id, kind ('comment'|'suggestion'),
    status, start, end, and text (comment) or old/new (suggestion), was, note."""
    prot = _protected_ranges(text)
    out = []
    for kind, rx in (("comment", COMMENT_RE), ("suggestion", SUGGEST_RE)):
        for m in rx.finditer(text):
            if any(s <= m.start() < e for s, e in prot):
                continue
            a = {"id": m.group("id"), "kind": kind, "status": m.group("status"),
                 "start": m.start(), "end": m.end(), "metaStart": m.start("meta"),
                 "was": _unquote_was(m.group("was")), "note": m.group("note") or ""}
            if kind == "comment":
                a["text"] = m.group("text")
            else:
                a["old"], a["new"] = m.group("old"), m.group("new")
            out.append(a)
    out.sort(key=lambda a: a["start"])
    return out


def _find(text, ann_id):
    for a in parse(text):
        if a["id"] == ann_id:
            return a
    raise KeyError("annotation %s not found" % ann_id)


def _splice(text, a, replacement):
    return text[:a["start"]] + replacement + text[a["end"]:]


def current_text(a):
    return a["text"] if a["kind"] == "comment" else a["old"]


def strip(text):
    """Clean prose: comments keep their (possibly revised) span, suggestions keep the old text."""
    for a in reversed(parse(text)):
        text = _splice(text, a, current_text(a))
    return text


def accept(text, ann_id):
    a = _find(text, ann_id)
    return _splice(text, a, a["text"] if a["kind"] == "comment" else a["new"])


def revert(text, ann_id):
    a = _find(text, ann_id)
    if a["kind"] == "suggestion":
        return _splice(text, a, a["old"])
    return _splice(text, a, a["was"] if a["status"] == "revised" and a["was"] is not None else a["text"])


def revise(text, ann_id, new_text):
    """Claude-side: replace an open comment's span, keep the markup, mark it revised."""
    a = _find(text, ann_id)
    if a["kind"] != "comment":
        raise ValueError("%s is a suggestion; only comments are revised" % ann_id)
    if "==}" in new_text:
        raise ValueError("revised text must not contain '==}'")
    was = a["was"] if a["status"] == "revised" and a["was"] is not None else a["text"]
    note = clean_note(a["note"])
    meta = "{>>#%s revised | was %s%s<<}" % (ann_id, quote_was(was), (" | " + note) if note else "")
    return _splice(text, a, "{==" + new_text + "==}" + meta)


def next_id(text):
    nums = [int(a["id"][1:]) for a in parse(text)]
    return "a%d" % (max(nums) + 1 if nums else 1)


def _check_free(text, start, end):
    for a in parse(text):
        if start < a["end"] and end > a["start"]:
            raise ValueError("span overlaps annotation %s" % a["id"])
    for s, e in _protected_ranges(text):
        if start < e and end > s:
            raise ValueError("span touches code")


def add_comment(text, start, end, note):
    span = text[start:end]
    if "==}" in span or not span:
        raise ValueError("cannot annotate this span")
    _check_free(text, start, end)
    note = clean_note(note)
    meta = "{>>#%s open%s<<}" % (next_id(text), (" | " + note) if note else "")
    return text[:start] + "{==" + span + "==}" + meta + text[end:]


def add_suggestion(text, start, end, new_text, note=""):
    old = text[start:end]
    if not old or "~>" in old or "~~}" in old or "~>" in new_text or "~~}" in new_text:
        raise ValueError("cannot suggest an edit on this span")
    _check_free(text, start, end)
    note = clean_note(note)
    meta = "{>>#%s open%s<<}" % (next_id(text), (" | " + note) if note else "")
    return text[:start] + "{~~" + old + "~>" + new_text + "~~}" + meta + text[end:]
