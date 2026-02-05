# Automated Building Orientation Extraction from Title 24 Plans

## Technical Report — February 2026

---

## 1. Goal

Extract the **front orientation** (azimuth in degrees clockwise from true north) of a building from its architectural plan set — the same value entered into CBECC-Res as "Front Orientation." This is a single number (0-360) but it cascades: getting it wrong by 90 degrees causes ~11 downstream errors in the compliance report (4 wall azimuths + 7 window azimuths all shift).

We're using Claude (Anthropic's multimodal LLM) to read native PDF plan sets and extract this value. No computer vision preprocessing — the model reads the PDF pages directly and reasons about what it sees.

### Why It's Hard

1. **North arrows are rotated.** Most California site plans have north arrows tilted 10-45 degrees from vertical. The model must measure the arrow angle precisely.
2. **Buildings are rotated on lots.** The building footprint on the site plan is often rotated relative to the page. Floor plans are typically drawn axis-aligned (walls horizontal/vertical), but site plans show the actual lot rotation.
3. **ADU front != street-facing.** For single-family homes, the front faces the street. For ADUs, the front faces the entry door — typically toward the main house or access path, which may be sideways or backwards relative to the street.
4. **Entry vs. deck confusion.** ADUs often have a covered deck with sliding glass doors on one side and a small entry porch with a swing door on the other. The model frequently confuses them — both look like "the front."
5. **Run-to-run variability.** The same model with the same instructions produces different answers each time. Visual angle estimation has inherent noise of ±15-30 degrees.

---

## 2. System Architecture

### 2.1 Extraction Pipeline

```
PDF Discovery → Page Classification → Page Routing → Orientation Extraction → Downstream Extraction
```

1. **PDF Discovery** finds all PDFs and counts pages (plans.pdf, spec_sheet.pdf)
2. **Page Classification** (separate agent) classifies each page with type, subtype, and content tags
3. **Page Routing** selects relevant pages for orientation (site plans with north arrows, elevations, floor plans)
4. **Orientation Extraction** runs two passes in parallel, verifies results
5. **Downstream Extraction** uses the orientation to set wall/window azimuths

### 2.2 Two-Pass Verification (Current Approach)

We run two independent orientation extractions in parallel with different methods, then compare:

```
                    ┌─── Pass 1: North Arrow + Street/Entry Direction ───┐
PDF Pages ──────────┤                                                     ├──► Verification ──► Final Answer
                    └─── Pass 2: Elevation Labels + Wall Edge Angle  ────┘
```

**Pass 1 (Fast, Direct):**
- Find north arrow on site plan
- Identify building front (street for homes, entry door for ADUs)
- Estimate the front-facing direction on the page (0°=up, 90°=right, etc.)
- Calculate: `front_orientation = (drawing_angle - north_arrow_angle + 360) % 360`

**Pass 2 (Thorough, Cross-Referenced):**
- Find entry on elevation drawings (look for 3'0" swing door with porch, not sliding glass)
- Find entry wall on site plan using spatial context (closest wall to main house for ADUs, closest to street for homes)
- Measure the wall edge angle precisely on the site plan
- Calculate perpendicular outward direction
- Same formula as Pass 1

**Verification Logic:**
- **Agreement (±20°):** Average the two results → high confidence
- **90° difference:** Side/front confusion detected → trust higher-confidence pass
- **180° difference:** Front/back confusion detected → trust higher-confidence pass
- **Other disagreement:** Trust higher-confidence pass
- **Confidence tie:** Default to Pass 1

### 2.3 Agent Architecture

Each pass is run as a Claude agent (Claude Sonnet) with:
- **Tool access:** Read (for native PDF page reading)
- **Instructions:** Separate markdown files for Pass 1 and Pass 2
- **Input:** DocumentMap JSON (page classifications) + PDF read instructions
- **Output:** Structured JSON with intermediate values (north arrow angle, entry direction, calculation)
- **Timeout:** 300 seconds per pass

The structured intermediate values are critical for debugging — we can see exactly where each pass went wrong (north arrow misread vs. entry wall misidentified vs. angle measurement error).

---

## 3. Evaluation Dataset

| Eval | Address | Type | Front Orientation | Pages | Key Challenge |
|------|---------|------|------------------|-------|---------------|
| canterbury-rd | 1961 Canterbury Rd, Sacramento | Single-Family | 90° | 19 | Straightforward — clear north arrow, street-facing |
| chamberlin-circle | 4720 Chamberlin Cir, Elk Grove | ADU | 73° | 13 | Entry faces main house, not street |
| martinez-adu | 745 Wyoming St, Martinez | ADU | 284° | 14 | Building rotated 90° on site plan |
| poonian-adu | 3534 Meadowlands Ln, San Jose | ADU | 112° | 17 | Subtle footprint tilt on site plan |
| lamb-adu | 1500 Wooden Valley Rd, Napa | ADU | 22° | 12 | Entry door vs. deck confusion |

Ground truth comes from CBECC-Res compliance reports (the CSV files that the Title 24 software generates). Tolerance: ±15 degrees.

---

## 4. Historical Approaches

### 4.1 Single-Pass Extraction (v1.0 → v2.8.0)

**Period:** Initial development through ~38 iterations of instruction tuning

**Approach:** One instruction file (~275 lines, grew to ~289 lines), one agent call per eval.

**Key instruction versions:**

| Version | Change | Impact |
|---------|--------|--------|
| v2.1.0 | Added north arrow left/right confusion guidance | Fixed ~35° systematic error on poonian-adu |
| v2.3.0 | Added ADU-specific rules (front = entry, not street) | Fixed martinez-adu from failing to occasional exact match |
| v2.4.0 | Added entry porch vs deck guidance | Broke chamberlin-circle (0/7 from 4/8) |
| v2.5.0 | Simplified entry guidance | Partially recovered chamberlin-circle |
| v2.6.0 | Added 3-step north arrow process + California sanity check | poonian-adu went 8/8 perfect! But canterbury-rd biased |
| v2.7.0 | Softened California check | Mixed results |
| v2.8.0 | "Nearly vertical = use 0°" guidance | poonian-adu regressed |

**Typical results (single-pass, 8 runs):**

| Eval | Pass Rate | Notes |
|------|-----------|-------|
| canterbury-rd | 8/8 (100%) | Easy case |
| martinez-adu | 6/8 (75%) | When it gets the entry direction right |
| chamberlin-circle | 4/8 (50%) | Side/front confusion |
| poonian-adu | 0/8 (0%) | Consistent ~42° underestimate (north arrow misread) |
| lamb-adu | 0/8 (0%) | Catastrophic variability (22° to 180° errors) |

**Key learning:** After ~15 iterations, instruction tuning has diminishing returns. Fixing one eval breaks another. The instruction file becomes bloated with conflicting guidance.

### 4.2 Automated Hill Climbing (38 iterations)

**Approach:** Automated loop that runs tests, analyzes failures, proposes instruction changes, and repeats.

**Result:** poonian-adu temporarily reached 8/8 perfect, but the fix was fragile — subsequent changes caused regression. The automation couldn't navigate the trade-offs between evals. After 38 iterations (v2.3.0 → v2.8.0, 275 → 289 lines), we concluded that instruction tuning alone wouldn't solve this.

### 4.3 Research Phase: Alternative Approaches Considered

We evaluated four approaches:

**A. Two-Pass Verification (chosen):**
Run extraction twice with different methods, compare results. Catches systematic errors (90°/180° confusion). Even when wrong, the system identifies *why*.

**B. CV-Based North Arrow Detection:**
Use OpenCV/PIL to detect the north arrow programmatically. Would eliminate the largest source of error. Deferred — "feels like a can of worms" (client feedback). The variety of arrow styles makes this complex.

**C. Multi-Source Triangulation:**
Use 3+ independent signals (north arrow, elevation labels, street direction, building shape heuristics) and vote. More complex but more robust. The two-pass system is a simpler version of this.

**D. Human-in-the-Loop:**
Flag low-confidence results for manual review. Always an option as a fallback.

### 4.4 Two-Pass System — Iteration History

**Phase 1: Grid-Line Based Pass 2**

The initial Pass 2 used structural grid lines (circled numbers 1-6 and letters A-C on architectural drawings) to map elevation views to the site plan.

- **Result:** Unreliable. Grid lines aren't always present, and the multi-step mapping was too complex for the model.
- **Pass rates:** 3/5 correct with high variability

**Phase 2: Footprint Shape Matching**

Pass 2 tried to match the building shape from the floor plan to the site plan footprint.

- **Result:** Vague. The model couldn't reliably determine building rotation from footprint shape alone.
- **Pass rates:** Similar to Phase 1

**Phase 3: Wall Edge Angle Method (current)**

Pass 2 identifies the entry wall directly on the site plan (using spatial context — "wall closest to main house" for ADUs) and measures the wall edge angle precisely.

- **Result:** Major improvement. canterbury-rd and chamberlin-circle became stable.
- **Key insight:** Don't try to map floor plan → site plan. Instead, identify the entry wall directly on the site plan using contextual cues.

**Phase 4: Verification Logic Iterations**

| Strategy | Effect |
|----------|--------|
| Always trust Pass 1 | Misses lamb-adu corrections from Pass 2 |
| Always trust Pass 2 | Broke canterbury-rd (rare Pass 2 failures override good Pass 1) |
| Confidence-based (current) | Best overall balance — trusts the pass that's more confident |

**Phase 5: Floor Plan Rotation Mapping (reverted)**

Added a complex step to measure footprint dimensions on the site plan and compare to floor plan dimensions to determine building rotation.

- **Result:** Catastrophic. Canterbury-rd (previously 100%) broke to 0%. The added complexity confused the model on simple cases.
- **Learning:** Simpler instructions are more robust. Adding complexity to fix one case often breaks others.

---

## 5. Current Results

### 5.1 Baseline (10 consecutive runs)

| Run | canterbury | chamberlin | martinez | poonian | lamb | Score |
|-----|-----------|------------|----------|---------|------|-------|
| 1 | ✓ 0° | ✓ 0° | ✓ 2° | ✗ 26° | ✗ 27° | 3/5 |
| 2 | ✓ 0° | ✓ 0° | ✓ 2° | ✗ 25° | ✗ 42° | 3/5 |
| 3 | ✓ 0° | ✓ 0° | ✓ 4° | ✓ 7° | ✗ 170° | 4/5 |
| 4 | ✓ 0° | ✓ 0° | ✓ 7° | ✗ 25° | ✗ 16° | 3/5 |
| 5 | ✓ 0° | ✓ 0° | ✓ 2° | ✗ 31° | ✓ 10° | 4/5 |
| 6 | ✓ 0° | ✓ 0° | ✓ 9° | ✗ 37° | ✓ 12° | 4/5 |
| 7 | ✗ 90° | ✓ 9° | ✓ 7° | ✓ 13° | ✗ 42° | 3/5 |
| 8 | ✓ 0° | ✓ 4° | ✓ 6° | ✓ 7° | ✓ 4° | **5/5** |
| 9 | ✓ 0° | ✓ 0° | ✓ 0° | ✗ 22° | ✗ 34° | 3/5 |
| 10 | ✓ 0° | ✓ 0° | ✓ 2° | ✗ 35° | ✗ 34° | 3/5 |

### 5.2 Per-Eval Summary

| Eval | Pass Rate | Avg Error (correct) | Avg Error (incorrect) | Dominant Failure Mode |
|------|-----------|--------------------|-----------------------|----------------------|
| **canterbury-rd** | **9/10** | 0° | 90° (1 run) | Rare Pass 1 glitch |
| **chamberlin-circle** | **10/10** | 0-9° | — | Fixed |
| **martinez-adu** | **10/10** | 0-9° | — | Fixed |
| **poonian-adu** | **3/10** | 7-13° | 22-37° | Drawing angle noise |
| **lamb-adu** | **3/10** | 4-16° | 27-170° | Front/back confusion |

**Score distribution:** 3/5 (6 runs), 4/5 (3 runs), 5/5 (1 run)
**Average score:** 3.5/5
**Best run:** 5/5 with 4.0° average error

### 5.3 Comparison: Before vs. After Two-Pass System

| Eval | Single-Pass (v2.3.0) | Two-Pass (current) | Change |
|------|---------------------|-------------------|--------|
| canterbury-rd | 100% | 90% | Slight regression (rare P1 bug) |
| chamberlin-circle | 50% | **100%** | Fixed |
| martinez-adu | 75% | **100%** | Fixed |
| poonian-adu | 0% | 30% | Improved |
| lamb-adu | 0% | 30% | Improved |

---

## 6. Remaining Failure Modes

### 6.1 poonian-adu (30% pass rate)

**Ground truth:** 112°. North arrow tilts ~20° left (340°). Entry faces right/upper-right on site plan.

**Problem:** The entry drawing angle varies widely between runs (68-110°). The correct value is ~92° (entry faces RIGHT on the page). Both passes read the north arrow correctly (~340°) but can't precisely estimate the outward direction of the entry wall. The ADU footprint has a subtle ~10° tilt from horizontal on the site plan, and the model sometimes sees the entry facing "upper-right" (70°) instead of "right" (90°).

**What would fix it:** A more precise wall edge measurement, or an anchor like a surveyor bearing annotation (the site plan has "S88°36'40"W" and "N15°39'34"E" labels on property lines that could help but the model doesn't use them consistently).

### 6.2 lamb-adu (30% pass rate)

**Ground truth:** 22°. Entry is on the North Elevation (small covered porch with swing door).

**Problem:** The ADU has a large covered deck with sliding glass doors on the south side and a small entry porch on the north side. Pass 1 consistently confuses the deck for the entry — the deck looks more impressive and prominent. Pass 2 correctly identifies the North Elevation entry about 70% of the time, but when the passes disagree by 180° (front/back confusion), the confidence tie-breaking often picks Pass 1 (both report "medium" confidence).

**What would fix it:** Better front/back disambiguation. Possible approaches:
- Use the 3D perspective views (this plan has "Northwest" and "Southwest" 3D views that show the entry clearly)
- Weight Pass 2 higher when it reports a front/back disagreement (since it directly reads elevation labels)
- Add explicit guidance about deck doors (6'0"+ sliders) vs. entry doors (3'0" swing)

---

## 7. Key Technical Insights

### 7.1 The Formula

Everything reduces to one calculation:

```
front_orientation = (entry_drawing_angle - north_arrow_angle + 360) % 360
```

Where:
- `entry_drawing_angle` = direction the entry faces on the page (0°=top, 90°=right, 180°=bottom, 270°=left)
- `north_arrow_angle` = direction the north arrow points relative to vertical (0°=up, 340°=20° left of up)

The model must estimate two angles from visual inspection and plug them into this formula. Each angle has ~10-20° of estimation noise, so the combined error is typically 15-30°.

### 7.2 Structured Intermediate Values

Both passes output detailed intermediate values, not just the final answer. This is critical for debugging:

```json
{
  "pass": 2,
  "elevation_analysis": {
    "entry_elevation": "North Elevation",
    "entry_evidence": "3'0\" swing door with covered porch"
  },
  "site_plan_measurement": {
    "entry_wall_edge": {
      "wall_angle_from_horizontal": 5,
      "entry_faces_outward": "toward TOP of page"
    },
    "entry_drawing_angle": 355
  },
  "north_arrow": { "angle": 330 },
  "calculation": { "formula": "(355 - 330 + 360) % 360 = 25" },
  "front_orientation": 25
}
```

From this, we can see: the model identified the correct elevation (North), measured the wall angle correctly (nearly horizontal), calculated the outward direction correctly (355°), but the north arrow reading (330° vs actual ~340°) introduced 10° of error.

### 7.3 What Works

1. **Simple, clear instructions** outperform complex multi-step procedures
2. **Spatial context** ("wall closest to main house") outperforms geometric matching ("match footprint dimensions")
3. **Two independent methods** catch errors that either method alone would miss
4. **Confidence-based verification** is better than always trusting one pass
5. **Native PDF reading** (vs. rasterized PNG) preserves fine line details for north arrows

### 7.4 What Doesn't Work

1. **Instruction bloat** — adding rules for edge cases hurts common cases
2. **Complex multi-step mappings** — floor plan → site plan rotation mapping confused the model
3. **8-direction bucketing** — "faces upper-right" is too imprecise; measuring wall edge angles is better
4. **Automated instruction tuning** — diminishing returns after ~15 iterations; trade-offs between evals make hill climbing ineffective

---

## 8. Open Questions

1. **Is 3.5/5 average good enough?** With the 15° tolerance, we're correct 70% of the time. The remaining 30% comes from two hard cases (poonian-adu and lamb-adu).

2. **Would CV preprocessing help?** Programmatic north arrow detection and building footprint measurement could eliminate the two largest error sources. But the variety of arrow styles and footprint representations makes this non-trivial.

3. **Should we accept low-confidence flags for human review?** The system already identifies disagreements. We could route low-confidence results to a human reviewer — this would catch most of the remaining errors.

4. **Would a third pass help?** A third extraction method (e.g., using 3D perspective views, or surveyor bearings) could break ties more reliably. But it adds cost and latency.

5. **How does this generalize?** Our 5-eval test set is small. Performance on unseen plan sets is unknown. The two evals we struggle with (poonian-adu, lamb-adu) represent specific challenges (subtle footprint tilt, entry/deck confusion) that may or may not be common in practice.

---

## 9. Cost and Performance

- **Per extraction:** 2 agent calls in parallel (one per pass), ~2-4 minutes total
- **Pages read per pass:** 5-8 PDF pages (site plans + elevations + floor plans)
- **Model:** Claude Sonnet (via Claude Code agent SDK)
- **Token usage:** ~15-25K tokens per pass (PDF reading is token-heavy)

---

## 10. Files Reference

| File | Purpose |
|------|---------|
| `src/agents/orchestrator.py` | Main pipeline, two-pass orchestration |
| `.claude/agents/orientation-extractor.md` | Agent definition |
| `.claude/instructions/orientation-extractor/pass1-north-arrow.md` | Pass 1 instructions |
| `.claude/instructions/orientation-extractor/pass2-elevation-matching.md` | Pass 2 instructions |
| `.claude/instructions/orientation-extractor/instructions.md` | Legacy single-pass instructions (v2.8.0) |
| `test_orientation_twopass.py` | Two-pass test runner |
| `test_orientation_fast.py` | Single-pass test runner |
| `.claude/workflows/targeted-improvement.md` | Improvement workflow |

---

*Report prepared February 4, 2026. System uses Claude Sonnet via Claude Code agent SDK for all extraction. No CV preprocessing — the model reads native PDF pages directly.*
