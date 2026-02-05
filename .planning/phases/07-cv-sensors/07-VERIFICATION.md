---
phase: 07-cv-sensors
verified: 2026-02-05T18:30:00Z
status: human_needed
score: 4/4 must-haves verified (infrastructure), 0/5 success criteria verified (outcomes)
human_verification:
  - test: "Run orientation extraction 10 times on poonian-adu with CV hints"
    expected: "Pass rate increases from 30% baseline to >70%, variance decreases"
    why_human: "Requires multiple LLM inference runs to measure variance reduction (expensive)"
  - test: "Run orientation extraction 10 times on lamb-adu with CV hints"
    expected: "Pass rate increases from 30% baseline to >70%, front/back confusion (180° errors) eliminated"
    why_human: "Requires multiple LLM inference runs to measure error type elimination"
  - test: "Run full eval suite (--all) 3 times with CV hints, 3 times without (--no-cv)"
    expected: "With CV: higher pass rates, tighter agreement. Without CV: matches baseline"
    why_human: "A/B comparison requires multiple expensive runs across all evals"
  - test: "Check if critic produces fewer orientation patches after CV integration"
    expected: "Orientation-related instruction patches decrease in frequency"
    why_human: "Requires running improvement loop to generate critic feedback"
  - test: "Verify instruction files are simpler/shorter than pre-CV versions"
    expected: "Verbose estimation tables removed, net line count same or lower"
    why_human: "Need to compare with git history before CV integration"
---

# Phase 7: CV Sensors Verification Report

**Phase Goal:** Reduce orientation extraction variance and eliminate systematic ±90° and ±180° failures by introducing a deterministic geometry sensing layer that assists (but does not replace) the existing LLM two-pass orientation system

**Verified:** 2026-02-05T18:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Orientation run-to-run variance decreases on existing evals | ? NEEDS HUMAN | Infrastructure in place, but no variance measurements performed yet |
| 2 | Frequency of 90° / 180° errors decreases | ? NEEDS HUMAN | Infrastructure in place, but no error frequency comparison performed yet |
| 3 | Two-pass agreement rate increases | ? NEEDS HUMAN | Single test (canterbury-rd) shows agreement, but no aggregate statistics across multiple runs |
| 4 | Orientation instruction files shrink or simplify | ? NEEDS HUMAN | Files have "Using CV Hints" sections, but need to compare line counts and complexity with pre-CV baseline |
| 5 | Critic produces fewer instruction patches for orientation | ? NEEDS HUMAN | CV sensors just integrated, critic hasn't run on post-CV system yet |

**Score:** 0/5 truths verified (all require human testing)

### Required Artifacts (from must_haves)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/cv_sensors/__init__.py` | Module init with exports | ✓ VERIFIED | Exports detect_north_arrow_angle, measure_wall_edge_angles, estimate_building_rotation, render_page_to_numpy |
| `src/cv_sensors/rendering.py` | PDF to NumPy conversion | ✓ VERIFIED | render_page_to_numpy() implemented with PyMuPDF, returns RGB arrays |
| `src/cv_sensors/preprocessing.py` | Edge detection preprocessing | ✓ VERIFIED | preprocess_for_lines() and preprocess_for_contours() implemented |
| `src/cv_sensors/north_arrow.py` | North arrow detection | ✓ VERIFIED | detect_north_arrow_angle() using Hough lines + contours, returns structured dict with angle/confidence/method |
| `src/cv_sensors/wall_detection.py` | Wall edge measurement | ✓ VERIFIED | measure_wall_edge_angles() and estimate_building_rotation() implemented |
| `test_cv_sensors.py` | Validation tests | ✓ VERIFIED | 10,835 lines, tests determinism, structure validation, runs on all 5 evals |
| `src/agents/orchestrator.py` (CV integration) | run_cv_sensors() function | ✓ VERIFIED | Function exists at line 110, imports CV sensors, calls all 3 detection methods |
| `.claude/instructions/orientation-extractor/pass1-north-arrow.md` (CV refs) | Using CV Hints sections | ✓ VERIFIED | 3 occurrences of "Using CV Hints" or "Fallback", 91 lines total |
| `.claude/instructions/orientation-extractor/pass2-elevation-matching.md` (CV refs) | Using CV Hints sections | ✓ VERIFIED | 4 occurrences of "Using CV Hints" or "Fallback", 111 lines total |

**Score:** 9/9 artifacts verified

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| src/cv_sensors/rendering.py | pymupdf | get_pixmap() + np.frombuffer() | ✓ WIRED | Imports fitz (PyMuPDF), calls get_pixmap and converts to numpy array with .copy() |
| src/cv_sensors/north_arrow.py | src/cv_sensors/rendering.py | import render_page_to_numpy | ✓ WIRED | Line 10: `from .rendering import render_page_to_numpy`, called at line 41 |
| src/cv_sensors/wall_detection.py | src/cv_sensors/rendering.py | import render_page_to_numpy | ✓ WIRED | Similar import pattern |
| src/agents/orchestrator.py | src/cv_sensors | import and call detection functions | ✓ WIRED | Lines 27-28 import detect_north_arrow_angle, measure_wall_edge_angles, estimate_building_rotation; called in run_cv_sensors() at lines 162, 172, 182 |
| src/agents/orchestrator.py | orientation prompts | cv_hints dict → JSON injection | ✓ WIRED | Lines 655-658, 759-762 inject CV SENSOR MEASUREMENTS block into prompts with json.dumps() |
| pass1-north-arrow.md | CV_HINTS in prompt | LLM reads CV measurements | ✓ WIRED | Lines 38-45 instruct LLM to use north_arrow.angle from CV hints, line 77 references wall edges |
| test_orientation_twopass.py | run_cv_sensors | import from orchestrator | ✓ WIRED | Imports run_cv_sensors from agents.orchestrator, passes cv_hints to run_pass() |

**Score:** 7/7 key links verified

### Requirements Coverage

N/A - Phase 7 has no explicit requirements mapped in REQUIREMENTS.md

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/cv_sensors/wall_detection.py | 62 | `return []` on no lines detected | ℹ️ Info | Graceful degradation - returns empty list when Hough detects no lines, expected behavior |

**Score:** 0 blockers, 0 warnings, 1 info

### Human Verification Required

#### 1. Variance Reduction on Problematic Evals

**Test:** Run `python3 test_orientation_twopass.py --eval poonian-adu` 10 times. Record pass/fail and error degrees for each run. Compare with baseline from MEMORY.md (30% pass rate, 7-13° when correct, 22-37° when wrong).

**Expected:** 
- Pass rate should increase significantly (target: >70%)
- Error variance should decrease (std dev of errors across runs)
- When wrong, errors should be smaller and more consistent

**Why human:** Each run requires LLM inference (~30-60 seconds per eval), and statistical significance requires 10+ runs. Total: ~10-15 minutes of expensive API calls.

#### 2. Front/Back Confusion Elimination

**Test:** Run `python3 test_orientation_twopass.py --eval lamb-adu` 10 times. Categorize errors:
- 180° errors (front/back confusion): should decrease or eliminate
- 90° errors (side confusion): track separately
- Other errors: note

Compare with baseline (30% pass rate, 180° errors are dominant failure mode).

**Expected:** 
- Pass rate should increase to >70%
- 180° errors should be rare or eliminated (CV provides precise wall angles, not ambiguous visual estimation)

**Why human:** Same as above - requires multiple expensive LLM runs and manual error categorization.

#### 3. A/B Comparison Across Full Eval Suite

**Test:** 
1. Run `python3 test_orientation_twopass.py --all --no-cv` 3 times (baseline without CV)
2. Run `python3 test_orientation_twopass.py --all` 3 times (with CV hints)
3. Compare aggregate metrics:
   - Pass rates per eval
   - Average error degrees
   - Two-pass agreement rates
   - Variance across the 3 runs

**Expected:**
- With CV: higher pass rates, lower errors, tighter variance
- Without CV: matches baseline from MEMORY.md
- Statistical significance on at least 2/5 evals

**Why human:** 30 total eval runs (6 runs × 5 evals), approximately 30-45 minutes of API calls. Too expensive for automated verification.

#### 4. Critic Feedback Analysis

**Test:** 
1. Run improvement loop critic on current orientation extraction results (with CV)
2. Check if critic still generates orientation-related instruction patches
3. Compare patch frequency/severity with pre-CV critic runs (if available in git history)

**Expected:** Fewer orientation patches, or patches focused on semantic reasoning (building type, entry identification) rather than geometric measurement issues.

**Why human:** Requires running the critic agent, which involves analysis of verification results and proposal generation. Also requires comparing with historical critic output.

#### 5. Instruction Simplification Verification

**Test:**
1. Check git history for pass1-north-arrow.md and pass2-elevation-matching.md before commit 008d465
2. Compare line counts and section complexity
3. Verify that verbose estimation tables were removed as claimed in summaries

**Expected:** 
- Net line count same or lower (summaries claim ~15 lines added for CV, ~15 lines removed from verbose tables)
- Estimation instructions simpler (one-line references instead of multi-row tables)
- Clear separation between CV primary path and fallback

**Why human:** Requires manual git diff analysis and subjective assessment of complexity/readability.

### Gaps Summary

**Infrastructure: COMPLETE**
All artifacts exist, are substantive (not stubs), and are properly wired. The CV sensor module produces deterministic angle measurements, the orchestrator integrates CV hints into orientation prompts, and the instruction files reference CV hints appropriately.

**Validation: COMPLETE (structural)**
- CV sensors pass determinism tests (5/5 runs produce identical results)
- CV sensors detect north arrows on 5/5 evals (100%, exceeds 3/5 target)
- CV sensors detect wall edges on all evals (8 edges per eval)
- End-to-end test (canterbury-rd) completes successfully with CV hints injected
- Backwards compatibility confirmed (--no-cv flag works)

**Outcome Verification: INCOMPLETE**
The phase GOAL is to "reduce variance and eliminate failures." This requires empirical measurement:
- No multi-run variance measurements performed yet
- No ±90° / ±180° error frequency comparison performed yet
- No two-pass agreement rate statistics across multiple runs
- No instruction simplification comparison with baseline
- No critic feedback analysis on post-CV system

**Why incomplete:** The summaries claim "Ready for evaluation" and "No blockers: Integration is complete" but then explicitly state the next step is to run `python3 test_orientation_twopass.py --all` to measure impact. The evaluation command was NOT run. The summaries document successful IMPLEMENTATION of the CV sensor infrastructure, but do NOT provide evidence of successful OUTCOME (variance reduction, failure elimination).

**Critical distinction:** 
- Task completion ≠ Goal achievement
- "CV sensors implemented" ≠ "Variance reduced"
- "Integration validated on 1 eval" ≠ "Failures eliminated on problematic evals"

---

_Verified: 2026-02-05T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
