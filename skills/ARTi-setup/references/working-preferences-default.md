---
name: working-preferences
description: Short, imperative, deduplicated rules for how Claude must behave in ARTi sessions — read at the start of every session, distinct from the descriptive workflow-profile log
metadata:
  type: feedback
  created: (seeded at install)
  updated: (seeded at install)
---

One rule per line, imperative, deduplicated. Read this file at the start of every ARTi session —
it says what Claude must do, not what was observed. Evidence for these rules lives in
`arti-workflow-profile.md` (created once the researcher's own sessions produce evidence worth
logging); this file keeps only the instruction.

**Two mechanisms keep this file alive after install:**
- **Capture.** When the researcher corrects Claude on *how* to do something (not *what* to
  produce), write the rule here in the same turn — never deferred to session end.
- **Promotion.** An observation in `arti-workflow-profile.md` that recurs across ≥2 sessions, or
  that the researcher states outright, gets promoted to a rule line here.

This file is seeded once at install time (missing-only — the installer never overwrites an
existing copy) so every ARTi install ships with the framework-level defaults below, even before
any researcher-specific rule has been captured. Everything from here down is a framework default,
not a personal preference — add researcher-specific rules in their own section as they're
captured, rather than editing these lines.

## Cross-project discovery
- **"Do I have research about X" / "have I looked into X" is a cross-project discovery query** —
  check `~/.arti/memory/research-idea-bank.md` and `~/.arti/memory/progress-index.md` (and
  `~/.arti/wdyt/idea-index.md` for framework/skill ideas) before answering from the current
  project's own memory alone. The `[[slug]]` link convention only covers pointers a memory file
  already seeded, not undirected discovery questions.

## Session-end ritual
- **Any phrasing meaning "we're done for now" fires the full wrap-up checklist** — not only the
  exact words "update memory".

## Session-start standing asks
- **Surface any open question a memory file recorded, and any untriaged `wdyt/index.md` rows,
  near the start of the session** — rather than waiting to be asked.

## Change log
- (seeded at install) — Framework-default seed created; see `ARTi-setup`'s
  `project-scaffold-template.md` for how it's installed and grown.
