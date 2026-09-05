# Predatory Journal Screen

Applied in Stage 5 to the **top two** candidate journals — the only ones that get analyzed at
all — before either goes on the Journal Comparison Table. Run once per journal; the verdict is
cached in that journal's `~/.arti/journal-library/<journal-slug>.md` entry rather than re-run every
time it's targeted again, unless `last verified` is stale.

---

## When to run the full screen — and when not to

**Auto-pass (no investigation, verdict still recorded):**
A journal indexed in **Scopus at Q1–Q2** that the **researcher or their group has already
published in**. Its legitimacy is already established by direct experience; re-verifying an
editorial board the researcher has personally corresponded with is friction without judgment.
Record the verdict with a one-line reason and move on:

```
**Predatory Journal Screen:** ✅ Pass (auto)
**Reason:** Scopus Q1, the group published here in 2024 — legitimacy established by direct
experience, full screen not run.
**Date screened:** [YYYY-MM-DD]
```

**Run the full checklist below** for any journal the researcher is unfamiliar with — a new
suggestion, a journal found through a search, an invitation received by email, or anything
outside Scopus Q1–Q2.

If in doubt, run the full screen. The auto-pass is for journals whose standing the researcher
can personally vouch for, not for journals that merely look respectable.

---

## Checklist

### 1. Review-speed claims vs. plausibility
- What review-to-decision time does the journal advertise?
- Is it plausible for the field and article type (e.g. a full experimental materials-chemistry
  paper reviewed in under 2 weeks is a red flag)?
- ⚠️ Flag: guaranteed turnaround times, "fast-track" fees tied to speed

### 2. Editorial board verifiability
- Are named editorial board members real, findable researchers in the field?
- Do their listed affiliations check out (institution, department)?
- Have any board members publicly disavowed affiliation with this journal?
- ⚠️ Flag: board members who cannot be independently verified, or who appear on multiple
  unrelated journals' boards simultaneously

### 3. Scopus / Web of Science indexing cross-check
- Is the journal actually listed in Scopus and/or WoS (not just claimed on its own website)?
- Cross-check directly against Scopus Sources / WoS Master Journal List, not the journal's
  self-reported indexing page
- ⚠️ Flag: indexing claims that can't be independently confirmed, or indexing in
  low-credibility/non-selective indices only

### 4. Additional red flags (secondary checks)
- Aggressive solicitation emails referencing unrelated prior work
- Article Processing Charges disproportionate to services offered, or hidden until acceptance
- Scope so broad it spans unrelated disciplines
- Journal not listed on Beall's-list-successor watchlists is reassuring but not sufficient alone

---

## Verdict

```
**Predatory Journal Screen:** ✅ Pass / ✅ Pass (auto) / ❌ Fail
**Reason:** [One or two sentences citing which checklist item(s) drove the verdict, or the
auto-pass basis]
**Date screened:** [YYYY-MM-DD]
```

A ❌ Fail verdict means the journal is excluded from the Journal Comparison Table entirely —
it is not merely down-ranked. Promote the next-ranked candidate and read its papers instead.
If the researcher believes the fail is a false positive, they must provide independent verifying
evidence before Claude re-screens.
