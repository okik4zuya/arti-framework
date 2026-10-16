# Classification schema for the included sources

Every included record gets four labels, written into the decisions CSV (`task, method, field, evidence`) while it is
screened, so each abstract is read once. The same four fields feed Figures 3 and 4 and both tables. Comparable runs need
comparable labels, so fix the vocabulary before the first batch, not after.

## How to build the vocabulary (do this once, before screening batch 1)

1. Read the first 20 abstracts of the first screening batch.
2. For each field write 4-6 short values plus `other`. Save them in `data/classification-vocabulary.md` (one line per
   field) and use only those values from then on. A value used by fewer than 2 sources at the end is merged into `other`
   before aggregation.
3. Use the lower-case, 1-4 word form shown below. Values are labels in a figure; they must stay readable at 7 pt.

| Field | Question it answers | Typical values (adapt to the topic; these are examples) |
|---|---|---|
| `task` | What does the study set out to do? | the main activities of the topic, for example: screening, extraction, appraisal, search, synthesis, writing support |
| `method` | Which family of approach does it use? | for example: large language model, classical machine learning, rule-based, statistical, hybrid, manual/qualitative |
| `field` | In which application domain? | the domains that recur in the abstracts, for example: medicine, software engineering, education, environment |
| `evidence` | What kind of study is it? | benchmark evaluation, case study, review, tool description, position paper, other |

## Rules

- One value per field per record; pick the dominant one. Do not invent a value for a record whose abstract does not say:
  use `other` for the first three fields; for `evidence` use `other` as well.
- Label from the abstract only. The full texts read afterwards may refine a label (re-run `screen.py apply` with the new
  value; the CSV is merged by key), but a label must never rest on knowledge of a paper that is not in its abstract.
- Excluded records get no labels.

## Why four fields

They answer the three review questions directly: RQ1 volume, venues and access (landscape figure), RQ2 which approaches
are used for which tasks (Figures 3 and 4), RQ3 what kind of evidence stands behind them and how much of it was read in full
(Table 2). Changing the fields changes the review questions; do not add a fifth field in an unattended run.
