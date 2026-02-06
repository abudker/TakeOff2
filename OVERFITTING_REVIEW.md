# Overfitting Review: Agent Instructions vs. Test Data

**Date:** 2026-02-06
**Scope:** All files in `.claude/instructions/` compared against 5 ground truth CSVs in `evals/`

## Summary

Several agent instruction files contain patterns calibrated to the specific 5 evaluation
projects rather than teaching general extraction principles. The most severe case is the
orientation extractor, whose "worked examples" produce the exact ground truth answers for
4 of 5 test cases.

---

## Findings

### CRITICAL: Orientation examples encode test answers

**File:** `.claude/instructions/orientation-extractor/instructions.md` (lines 185-207)

The four "worked examples" produce results matching the actual ground truth orientations:

| Example | Computed Result | Matching Eval      | Ground Truth |
|---------|----------------|---------------------|--------------|
| 1       | 73 deg         | chamberlin-circle   | **73 deg** (exact match)  |
| 2       | 110 deg        | poonian-adu         | **112 deg** (2 deg off)   |
| 3       | 284 deg        | martinez-adu        | **284 deg** (exact match) |
| 4       | 20 deg         | lamb-adu            | **22 deg** (2 deg off)    |

Canterbury Rd (90 deg) is the only eval not directly represented. An agent reading these
examples gets de facto answer keys for the test set.

Additionally, `pass1-north-arrow.md` line 25 directly references `"Front faces Canterbury Rd
on the east side"`, naming a test case location.

**Recommendation:** Replace with synthetic examples using round-number angles that don't
match any eval. Remove the Canterbury Rd reference.

---

### HIGH: Zone naming rule overfit to test distribution

**File:** `.claude/instructions/zones-extractor/instructions.md` (line 8)

> For ADU projects, the zone name MUST be "ADU" -- never "Zone 1", "Living Zone"

Ground truth: 4/5 evals use zone name "ADU", 1/5 uses "Single-Family Dwelling". The "MUST" /
"never" language is calibrated to the test set. CBECC zone names are user-configurable.

**Recommendation:** Change to "typically 'ADU' in CBECC; use the name from the plans when
available."

---

### HIGH: Construction type format rigidity

**File:** `.claude/instructions/zones-extractor/instructions.md` (lines 9, 824-855)

> MUST use CBECC short form: "R-21 Wall", "R-13 Wall". Never include framing details.

All 5 test cases use "R-21 Wall". The mandated string format pattern was derived entirely
from the ground truth CSVs. CBECC supports various construction labels.

**Recommendation:** Teach how to read and normalize construction types rather than
prescribing a rigid format derived from the test set.

---

### HIGH: Ceiling height 8.5 ft emphasis

**File:** `.claude/instructions/zones-extractor/instructions.md` (lines 10, 109-115)
**File:** `.claude/instructions/zones-extractor/field-guide.md` (lines 738-780)

> ADU/small buildings commonly have 8'-6" (= 8.5 ft), NOT 8'-0".

Added after the Chamberlin Circle case (ground truth: 8.5 ft). The other 4 evals have
ceiling heights of 9.0, 8.0, 10.0, and 9.0 ft -- there is no consistent "ADU = 8.5"
pattern even within the test data. The disproportionate emphasis on 8.5 ft steers the
agent toward one test case's answer.

**Recommendation:** Instruct to always read the actual dimension from section drawings.
Remove the specific bias toward 8.5 ft for ADUs.

---

### MEDIUM: SHGC values derived from test failures

**File:** `.claude/instructions/windows-extractor/instructions.md` (lines 9, 126-128)

> Do NOT default to 0.23 SHGC if the schedule shows a different value (e.g., 0.29, 0.25).

0.29 is from Lamb ADU (the only eval with SHGC 0.29). The principle is sound but the
specific counterexample values were chosen from the test set.

**Recommendation:** Keep the principle; replace specific values with a general statement
like "values commonly range from 0.18 to 0.40."

---

### MEDIUM: Window designation code examples from test data

**File:** `.claude/instructions/windows-extractor/instructions.md` (line 8)

> "3040" = 3'0" x 4'0" = 12 sf, "6068" = 6'0" x 6'8" = 40 sf

These exact codes appear in the Martinez and Chamberlin ground truth. The decoding principle
is general, but the specific examples are drawn from test data.

**Recommendation:** Use a broader set of examples not tied to the test data, or at minimum
add additional examples that don't appear in the evals.

---

### MEDIUM: "Insect Screen (default)" exterior shade

**File:** `.claude/instructions/windows-extractor/instructions.md` (lines 4, 11, 224)

> Default to "Insect Screen (default)" when no exterior shading device is specified.

Every window in all 5 ground truth CSVs uses this exact string. While it is the CBECC
default, the emphasis and exact string formatting were learned from the test data.

**Recommendation:** Keep as a CBECC default note but don't elevate it to a "CRITICAL
OUTPUT RULE."

---

### MEDIUM: Climate zone city-to-zone mapping

**File:** `.claude/instructions/project-extractor/field-guide.md` (lines 98-103)

> Common zones by region: Sacramento: 12, San Jose: 4

Sacramento maps to 3 test evals; San Jose maps to Poonian. The table covers exactly the
cities in the test set while omitting Napa (CZ 2, Lamb ADU).

**Recommendation:** Either make the table comprehensive (many more cities) or remove it
entirely and instruct the agent to read climate zone from the documents.

---

### STRUCTURAL: Narrow test distribution creates implicit overfitting

The 5 evals share extreme homogeneity:
- 4/5 are ADUs
- 3/5 are Climate Zone 12
- 5/5 are single-family, 1-story, new construction
- 5/5 use R-21 walls
- 4/5 are All Electric

Instructions heavily emphasize ADU-specific patterns, slab-on-grade, single-story logic,
and All Electric fuel type. There is little guidance for multi-family, multi-story,
alterations, basements, or mixed fuel types. The instructions would likely underperform on
a more diverse building set.

**Recommendation:** Expand the eval set to include multi-family, multi-story, alteration,
gas-fuel, and basement projects.

---

### Note: Critic anti-overfitting rules exist but came too late

The critic instructions (`.claude/instructions/critic/instructions.md`, lines 36-89)
contain strong anti-overfitting rules. However, much of the overfitting in current
instructions occurred through manual tuning or earlier improvement iterations before
these guards were added.

---

## Action Items

| Priority | Action | Files Affected |
|----------|--------|----------------|
| P0 | Replace orientation examples with synthetic ones | orientation-extractor/instructions.md, pass1-north-arrow.md |
| P0 | Remove Canterbury Rd reference from pass1 | orientation-extractor/pass1-north-arrow.md |
| P1 | Soften zone naming from MUST to guideline | zones-extractor/instructions.md |
| P1 | Generalize construction type guidance | zones-extractor/instructions.md, field-guide.md |
| P1 | Remove ceiling height 8.5 bias | zones-extractor/instructions.md, field-guide.md |
| P2 | Remove test-derived SHGC counterexamples | windows-extractor/instructions.md |
| P2 | Diversify window code examples | windows-extractor/instructions.md |
| P2 | Make city-zone table comprehensive or remove | project-extractor/field-guide.md |
| P3 | Add diverse building types to eval set | evals/ |
