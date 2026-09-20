---
name: working-preferences
description: Short, imperative, deduplicated rules for how Claude must behave in ARTi sessions — read at the start of every session, personalization's single source
metadata:
  type: feedback
  created: (seeded at install)
  updated: (seeded at install)
---

One rule per line, imperative, deduplicated. Read this file at the start of every ARTi session —
it says what Claude must do, not what was observed. This is the only mechanism: when the
researcher corrects Claude on *how* to do something (not *what* to produce), or states a
preference outright, write the rule here in the same turn — never deferred to session end, never
routed through a separate evidence log first.

This file is seeded once at install time (missing-only — the installer never overwrites an
existing copy) so every ARTi install ships with the framework-level defaults below, even before
any researcher-specific rule has been captured. Everything from here down is a framework default,
not a personal preference — add researcher-specific rules in their own section as they're
captured, rather than editing these lines.

## Cross-project discovery
- **"Do I have research about X" / "have I looked into X" is a cross-project discovery query** —
  never answer from the current project's own memory alone. Run `idea-bank search <keywords>`
  and `project list` first (plus `idea-index list` for framework/skill ideas rather than research
  topics). `project list`'s `summary` field is free text covering each project's actual memory
  sub-topics — read it to shortlist the one or two projects that plausibly hold the topic, *then*
  open only those projects' own `MEMORY.md` and follow the pointer to the right `memories/*.md`
  file. Don't open every candidate project's `MEMORY.md` by hand — the summary field exists so
  that scoping step is cheap. The `[[slug]]` link convention only covers pointers a memory file
  already seeded, not undirected discovery questions. A direct read of `project-index.md` —
  including its `Summary` column — is an acceptable substitute for running `project list` when the
  file is already open or being scanned for other reasons; the CLI is only required for anything
  that *writes*.

## Session-end ritual
- **Any phrasing meaning "we're done for now" fires the full wrap-up checklist** — not only the
  exact words "update memory".

## Session-start standing asks
- **Surface any open question a memory file recorded, and any untriaged `inbox/index.md` rows,
  near the start of the session** — rather than waiting to be asked.

## Change log
- (seeded at install) — Framework-default seed created; see `ARTi-setup`'s
  `project-scaffold-template.md` for how it's installed and grown.
