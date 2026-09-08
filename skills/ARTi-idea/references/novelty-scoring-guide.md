# Novelty Scoring Guide

A detailed rubric for scoring research ideas on three dimensions.
Used during Stage 3 (Idea Canvas) and Stage 5 (Journal Target Sheet) of the
ARTi-idea workflow.

---

## Overview

Every research idea is scored on three independent dimensions:
- **C** — Conceptual Novelty (the research question)
- **M** — Methodological Novelty (the approach)
- **E** — Empirical Novelty (the findings produced)

Scores run from 1 (fully incremental) to 5 (paradigm-shifting).
A composite label is assigned based on the combination.

Scores are always written as: **C[n] / M[n] / E[n]**
Example: C3 / M2 / E3 = Meaningful novelty

---

## Dimension C — Conceptual Novelty

How new is the research *question* or *hypothesis* itself?

| Score | Label | Criteria | Example |
|---|---|---|---|
| 1 | Replication | Repeating an existing study with no meaningful variation. Same question, same system, same context. | Re-measuring a known material's properties using the same method in the same conditions. |
| 2 | Extension | Same conceptual framework, minor variation. New sample, new temperature, new concentration — but the question is essentially the same. | Testing a well-known photocatalyst at a new pH range. |
| 3 | Gap-filling | Asks a question that the literature has not addressed, but that follows logically from existing work. A real gap is filled. | Investigating the effect of surface defects on catalytic performance — studied in Theory but not experimentally confirmed. |
| 4 | Reframing | Proposes a new mechanism, new theoretical lens, or new conceptual relationship between variables. Challenges assumptions without overturning established consensus. | Proposing that the active site is not the surface area but the grain boundary — with experimental evidence. |
| 5 | Paradigm-shifting | Fundamentally challenges or overturns a widely accepted framework or mechanism. Extremely rare. | Demonstrating that a mechanism assumed for 30 years is incorrect, with compelling evidence. |

**Scoring rules for C:**
- Score based on the *question*, not the execution. Even a poorly designed experiment
  can ask a novel question (score the question, flag the design separately).
- If the gap is identified in the Gap Map, C ≥ 3 is defensible.
- C = 4 requires that the researcher has sufficient literature depth to recognize the
  reframing as genuinely new — check the Researcher Profile.
- C = 5 is almost never appropriate unless the researcher has deep domain mastery and
  the Gap Map contains direct contradictory evidence of an established theory.

---

## Dimension M — Methodological Novelty

How new is the *approach*, *technique*, or *study design*?

| Score | Label | Criteria | Example |
|---|---|---|---|
| 1 | Standard | Fully established methods, published protocols, no adaptation. | XRD + SEM + FTIR characterization of a material — standard in every paper in the field. |
| 2 | Adaptation | Minor modification of an established method. Slightly different parameters, sample preparation, or sequence. | Modified synthesis temperature in a standard hydrothermal method. |
| 3 | Cross-field application | Applies an established method from another field or in a meaningfully new context within the same field. | Applying electrochemical impedance spectroscopy to a photocatalysis system where it has rarely been used. |
| 4 | Method development | Significant modification or combination of methods producing a new analytical or synthesis capability. | Developing a new in-situ characterization setup by combining two existing instruments. |
| 5 | New technique | Inventing a genuinely new measurement approach, instrument, or analytical method. | Designing a new sensor mechanism not previously described. |

**Scoring rules for M:**
- Score based on what the researcher will actually *do*, not what they could theoretically do.
  Cross-check against the Researcher Profile — if the technique requires equipment not available,
  M cannot be claimed until access is confirmed.
- M = 1 does not make an idea bad — a strong C or E score compensates.
- M = 4 or 5 requires explicit confirmation in the Researcher Profile that the researcher
  has access to the necessary equipment and expertise.

---

## Dimension E — Empirical Novelty

How new are the *data*, *findings*, or *observations* produced?

| Score | Label | Criteria | Example |
|---|---|---|---|
| 1 | Confirmatory | Produces data that confirms known results in a new but unremarkable sample. | Showing that a well-known synthesis method works for yet another material variant. |
| 2 | Incremental data | Adds to an existing dataset in a meaningful but expected way. | Adding one more temperature point to an existing thermal stability study. |
| 3 | First-reported | Generates the first reported measurement or observation for a meaningful condition, system, or parameter combination. | First-reported photocatalytic efficiency of a specific ternary composite under visible light. |
| 4 | Quantitative revision | Produces findings that substantially revise or refine existing quantitative understanding — new numbers that matter. | Demonstrating that the efficiency is 3× higher than previously reported due to a previously ignored variable. |
| 5 | Contradictory finding | Produces findings that directly contradict established empirical results — with solid evidence. | Showing that a material previously reported as inactive is in fact highly active under specific conditions, explaining prior failures. |

**Scoring rules for E:**
- E = 3 is achievable for most well-designed studies addressing a real gap.
- E = 4 requires a study design capable of producing quantitatively precise, reproducible
  data — check the Researcher Profile for data reporting capacity.
- E = 5 requires a strong contradictory finding grounded in the Gap Map's
  `[⚠️ CONTRADICTION]` entries.
- E = 1 is a warning sign — if the study only confirms known results, ask whether
  the idea is worth pursuing.

---

## Composite Label Assignment

After scoring all three dimensions:

| Rule | Composite Label | Recommendation |
|---|---|---|
| All three dimensions ≤ 2 | **Incremental** | ❌ Reject or major redesign. Unlikely to be accepted by meaningful journals. |
| At least one ≥ 3, all others ≥ 2 | **Meaningful** | ✅ Minimum viable novelty. Suitable for solid field journals (Q2–Q3). |
| At least one ≥ 4, all others ≥ 2 | **Significant** | ✅ Strong candidate. Suitable for high-impact field journals (Q1–Q2). |
| Any dimension = 5 | **Paradigm-shifting** | ⚠️ High risk. Check ceiling carefully. Suitable for top-tier journals only if supported by the Researcher Profile. |

---

## Novelty Ceiling Check

Before finalising a score, check the researcher's Novelty Ceiling — read it from Section H of `~/.arti/memory/researcher-profile.md`, where ARTi-setup derived it once. Do not re-derive it here.

**Ceiling check procedure:**
1. Read the C, M, E ceilings from Section H of the Researcher Profile.
2. Compare each dimension score against its ceiling.
3. If any dimension score > ceiling: flag as ⚠️ Exceeds ceiling.
4. Propose a redesign that reduces the dimension score to within ceiling
   while preserving as much novelty as possible.

**Ceiling flag format:**
```
⚠️ Ceiling exceeded on M: Scored M4 but researcher ceiling is M2.
Reason: Technique X required but not available.
Redesign option: Replace technique X with technique Y (available, M3 result)
or seek collaboration with [type of lab] to restore M4.
```

---

## Novelty Profile vs. Journal Fit

Different novelty profiles suit different journal types.
Use this table when building the Journal Target Sheet.

| Novelty Profile | Best journal fit |
|---|---|
| C3 / M1 / E3 — novel question, standard methods, new data | Solid disciplinary journal (Q1–Q2 field journal). High empirical value. |
| C2 / M4 / E2 — standard question, novel method, incremental data | Methods-focused journal or technical communication. |
| C4 / M2 / E3 — reframing question, standard methods, first-reported data | High-impact field journal. Strong if evidence supports the reframing. |
| C3 / M3 / E4 — gap-filling, cross-field method, quantitative revision | Strong Q1 field journal candidate. Well-rounded profile. |
| C4 / M3 / E4 — reframing, applied method, quantitative revision | Top-tier field journal or broad-scope journal candidate. |
| C5 / M* / E5 — paradigm-shifting | Nature family, Science, PNAS, JACS, Angewandte — only with ceiling support. |

---

## Journal Novelty Threshold Extraction (Stage 5)

When analyzing 2–3 example papers from a candidate journal:

For each paper, estimate:
- C score: How novel is the question? (1–5)
- M score: How novel is the method? (1–5)
- E score: How novel are the findings? (1–5)

Then derive the journal's **typical novelty threshold**:
- Take the average or range across the 2–3 papers per dimension
- Record as: "This journal typically publishes C[n]–[n] / M[n]–[n] / E[n]–[n]"
- Compare your idea's score against this threshold
- This is a **light** threshold. ARTi-writing extends it with the remaining papers of its 5–8
  set — it does not re-derive it from zero, and these papers count toward that set.

**Threshold comparison output:**
```
Your idea: C3 / M2 / E3 → Meaningful
Journal typical range: C3–4 / M2–3 / E3–4 → Significant minimum
Fit: ⚠️ Borderline — your E score meets threshold but C score is at the low end.
Recommendation: Strengthen the conceptual framing before targeting this journal,
or consider [lower-tier journal] where C3 / E3 is sufficient.
```
