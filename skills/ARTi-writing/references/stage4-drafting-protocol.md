# Stage 4 — Manuscript Drafting: protocol

Full procedure for turning Scratchbook content into manuscript prose. Read this when Stage 4 fires
— see `SKILL.md`'s Stage 4 stub for the trigger condition and output file. See
`references/section-guide.md` for per-section writing guidance while drafting.

**Project index cadence:** the first time this stage produces "Draft 1" content (not on later
revisions of the same draft), run `project upsert --stage "Drafting" --status "writing started"`
for this project's row. This is the phase boundary ARTi-idea's handoff row left open; skipping it
is why the dashboard can show a project stuck at "Handed off" indefinitely. Consider whether
`--summary` needs updating too (e.g. a voice-implementation pass or new section added).

## Procedure

- Skim the `**Argumen saat ini:**` lines first for a quick orientation on each section's current
  argument, then go to the full dumps beneath them for the supporting material
- Transform Scratchbook content into formal academic prose, following the Manuscript Blueprint's
  paragraph-level shape for this journal
- Strictly follow Journal Profile Block A (structure and formatting)
- Mirror the project's Voice Profile, adjusted for any journal-specific delta noted in Journal
  Profile Block B
- Match technical depth consistent with Journal Profile Block C (Technical Depth Profile)
- Flag any content in the Scratchbook that is unclear or insufficient
- Label each output clearly as "Draft N"
- Before drafting, scan all `[⚠️ CONTRADICTION]` tags in the relevant section — note them for the Discussion
- Before drafting, check Block C — flag any characterization technique or analysis type that typical journal papers include but the Scratchbook does not yet address
- Update the drafting progress tracker (status, draft #, word count, open-flag count) in the same
  turn a section is drafted or revised, before moving to the next section — never deferred to
  session end

## Concision is the default register, not a special pass

Draft every section, and revise every existing one, as dense and literature/evidence-rich as it can
be while remaining correct: trim elaboration, meta-commentary, and content already restated by an
adjacent table or figure; never touch citations or evidence. Concretely, on both a first draft and
any later revision:
- Cut signposting sentences that only announce what a paragraph is about to do or just did
  ("Note that…", "It is worth noting…", "Firstly / secondly / thirdly" scaffolding, "This
  demonstrates that…" restated after the demonstration already reads that way).
- Cut parenthetical glosses and restrictive clauses that repeat a claim already made in the
  sentence, or that a cited source's name alone already implies.
- When a table or figure states something in full (a mapping, a list of properties, a set of
  values), do not also restate it prose-form nearby — point to the display item instead.
- **Don't elaborate without strong support (literature or evidence).** A claim, interpretation, or
  aside earns extra sentences only if it is carrying a citation, a statistic, or data from the
  Scratchbook — not because it sounds plausible or adds color. If a sentence would need to be
  written from general reasoning rather than a sourced claim, it is a candidate to cut, not expand;
  when the point genuinely needs saying and has no source, flag it (`[SOURCE NEEDED]` or
  `[CITATION NEEDED]`) rather than writing it up unsupported at length.
- Never cut a citation, a statistic, a `[DATA NEEDED]`/`[CITATION NEEDED]`/`[SOURCE NEEDED]` flag,
  or a substantive claim (a distinct piece of evidence, reasoning, or a stated limitation/trade-off)
  purely to shorten. If a sentence carries a citation or a number, treat everything in it as load-
  bearing by default and cut around it, not through it.
- After any concision pass, verify nothing evidentiary was lost: diff the citation set (author-year
  keys) between the before and after text and confirm it is unchanged, the way
  `references/review-checklist.md` Section J already requires for citation integrity generally.
- This is the default weighting for every draft and revision, independent of whether the user asks
  for a "compression pass" by name — write tight the first time rather than padding now and cutting
  later. **The one override:** if the user explicitly asks for elaboration, more detail, or a longer
  treatment of something, honor that request for the scope asked — it does not reopen the default
  elsewhere in the same draft.

## Plagiarism Prevention at this stage

- Write exclusively from the Scratchbook — never draft by rephrasing the original source text directly
- All literature from the Scratchbook must be fully paraphrased into original prose; do not reproduce sentence structures from the original paper even if the words differ
- Direct quotes are not acceptable in scientific manuscripts — if a Scratchbook entry contains a direct quote, rewrite it before including it in the draft
- Cite as you write — every claim derived from literature must carry its citation inline; never plan to add citations later
- Flag any Methods section content that appears reused from a prior paper — self-plagiarism is a violation
- Add a note at the end of each drafted section: *"Please review this section for unintended similarity to source texts before proceeding."*

## Hallucination Prevention at this stage

- Only cite references explicitly listed in the Scratchbook `## Reference List` — never generate or infer citations from memory
- If a claim requires a citation but no source is in the Scratchbook, insert `[CITATION NEEDED]` and notify the user
- Never invent numerical data, experimental results, or author names — flag missing values as `[DATA NEEDED — VERIFY FROM SOURCE]`
- Do not expand on a reference's content beyond what the user has provided in the Scratchbook
