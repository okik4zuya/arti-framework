# Stage 0 — Voice Profile: extraction protocol

Full procedure for building or selecting a Voice Profile (Core Document #2). Read this when
Stage 0 fires — see `SKILL.md`'s Stage 0 stub for the trigger condition and output file. See
`references/voice-profile-template.md` for the blank Path A/B template.

Run this stage only if the researcher has no Voice Profile yet in `~/.arti/voice-profiles/`, or if
they explicitly say their writing style has shifted. Otherwise skip straight to Stage 1 — read the
existing Voice Profile file, don't re-derive it.

## Selection step — run before choosing a path or reusing a profile

Read (or create, if missing) `~/.arti/voice-profiles/00-INDEX.md`, the flat catalog of every
existing profile. If it lists more than one profile, ask the researcher which one is in effect for
this project before proceeding — do not guess or default to the most recent. Record the choice in
this project's Journal Profile Block B pointer line, alongside the existing "which Voice Profile
file is in effect" note (this is the write-half of the Stage 0 ↔ Stage 1 Journal Profile Block B
coupling — Stage 1 reads and extends the same pointer line, see
`references/stage1-journal-profile-protocol.md`). If the catalog lists none yet, proceed to build
one (Path A, B, or C below) and add its row to the catalog once written.

## Path A — extracted from the researcher's own papers

Ask for 3–5 of the researcher's own first-author papers (any journal — this is about how *they*
write, not what one journal expects). For each paper, extract, in one reading pass:

*Title analysis:*
- Word count and structural pattern (record the formula, e.g., "[Material]-enabled [Property] for [Application]")
- Whether the key finding or novelty is stated explicitly in the title or implied
- Use of punctuation, colons, or subtitles

*Abstract analysis:*
- Sentence count per component (background, objective, methods, results, conclusion)
- Dominant tense per component
- Active vs. passive voice preference
- How key results are quantified (specific numbers vs. qualitative statements)
- Total word count

*Voice and tone:*
- Overall register (formal vs. semi-formal)
- Passive vs. active voice ratio across sections
- Hedging language patterns — list the specific phrases used (e.g., "suggests," "indicates," "demonstrates," "was found to," "it is proposed that")
- How claims are qualified or strengthened

*Section-level patterns:*
- Introduction: paragraph count, how the research gap is stated, how the objective is introduced
- Methods: level of procedural detail, how instruments are cited, tense consistency
- Results/Discussion: how figures are introduced, how literature comparisons are framed, how contradictory results are handled
- Conclusion: paragraph count, whether future work is included, how contribution is stated

*Vocabulary and terminology:*
- Field-specific preferred terms
- How chemical names, formulas, and units are written
- When abbreviations are introduced and how frequently used

*In-text citation style:*
- Narrative vs. parenthetical citation preference
- Typical number of references per claim
- Whether recent or seminal papers are favored

Then run one synthesis pass across all papers into a single consensus Voice Profile: note
dimensions where the researcher is consistent vs. variable, flag any pattern that appears in only
one paper as a possible one-off rather than a true habit, and write the result to
`~/.arti/voice-profiles/<voice-slug>.md`.

## Path B — supplied ready-made (e.g. `gtmk-voice`)

Record a thin pointer file at the same location instead of re-extracting: which existing style
skill or profile this points to, and the date the researcher last confirmed it still matches their
writing. Do not run Path A's extraction over papers that skill was already built from.

## Path C — generalized multi-file corpus, built from a single example article

Use this path when the researcher wants a rich, `gtmk-voice`-style reference corpus — not a single
flat template file, and not a pointer to somebody else's style skill — built from their own writing
in whatever field they're in, from just one example article (rather than Path A's 3–5). Modeled
directly on the `gtmk-voice` skill's own decomposition, generalized so it transfers to any field:

1. Ask the researcher for one example article (their own, or one they want to emulate) and a
   **descriptive slug** for the resulting profile — prompt for this explicitly; never default to a
   placeholder like "writing-style-1". The slug becomes the folder name.
2. From that single article, extract the same registers `gtmk-voice` documents, generalized rather
   than left field-specific: verb/noun/adjective/adverb registers with a preferred-vs-avoided list
   (no domain-noun lexicon section, since one article can't establish a stable domain vocabulary —
   flag this gap explicitly rather than inventing one); verbatim phrase banks by rhetorical
   function; the commitment/hedging ladder; paragraph-flow move-sequences per section; title/
   abstract formulas; the non-native-English or other signature fingerprint, if present; and a
   condensed copy-paste prompt block distilling all of the above.
3. Write the result to `~/.arti/voice-profiles/<slug>/`, as a folder (not a flat file — the folder
   structure is the point of "same structure but generalized"), containing:
   `00-INDEX.md`, `01-lexicon.md`, `02-phrases.md`, `03-hedging.md`, `04-paragraph-flow.md`,
   `05-abstract-title.md`, `06-signature-notes.md`, `07-PROMPT-BLOCK.md`.
4. Because this is built from one source article rather than 3–5, `00-INDEX.md` must state the
   single-source provenance explicitly and flag the whole extraction as **provisional** until
   reconfirmed against a second sample — do not present it with the same confidence as a Path A or
   an established Path C profile built from more than one source.
5. Add a row for the new profile to `~/.arti/voice-profiles/00-INDEX.md` (the catalog read by the
   selection step above).

**File:** `~/.arti/voice-profiles/<voice-slug>.md` (Path A/B) or `~/.arti/voice-profiles/<slug>/` (Path C)
