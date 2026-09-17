# Stage 2 — Gap Map construction: protocol

Full procedure for building the Gap Map (Core Document #2). Read this when Stage 2 fires — see
`SKILL.md`'s Stage 2 stub for the trigger condition and output file.

## Procedure

- Before generating anything new, Claude runs `idea-bank search <keywords>` (see Reference Files
  for the `arti-db` invocation) for parked ideas relevant to this topic and surfaces them to the
  researcher first
- The researcher feeds literature: papers, summaries, or notes — for a single paper, "summarize
  paper [title]" (see Paper Extraction, in Core Documents) produces the `REFERENCE ENTRY` and
  evidence lines ready to fold in directly
- Claude identifies which gaps are Conceptual, Methodological, or Empirical
- Claude flags contradictions between sources with `[⚠️ CONTRADICTION]` tags
- Claude must NOT suggest gaps beyond what the literature supports — flag as
  `[SUGGESTED — USER MUST VERIFY]` if speculating
- After each addition, Claude reports: gaps updated, contradictions found, areas still thin

## Minimum viable Gap Map

**One** gap carrying at least three supporting references and an explicit statement of why it
matters. Depth beats count — a single well-evidenced gap is a better foundation than three thin
ones. More gaps are welcome, but not required to proceed.
