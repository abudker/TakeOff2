# Agent-Critic Improvement Loop: System Architecture Report

## Executive Summary

This document describes the complete **agent-critic self-improvement loop** built into the Takeoff2 extraction system. The system extracts building specifications from Title 24 architectural plan PDFs using a pipeline of specialized Claude Code agents. When extraction accuracy falls short, an automated critic agent analyzes failure patterns and proposes targeted instruction improvements — creating a closed-loop optimization cycle that iteratively improves extraction quality without changing any code.

The key insight: **extraction behavior is controlled by markdown instruction files**, not code. This means a critic agent can improve the system by rewriting instructions, and those improvements generalize to new documents.

---

## 1. System Overview

### What the System Does

Takeoff2 reads architectural plan PDFs (site plans, floor plans, elevations, equipment schedules) and extracts structured building data needed for California Title 24 energy compliance modeling. The output includes:

- **Project info**: address, climate zone, fuel type, stories, bedrooms
- **Building orientation**: front-facing azimuth in degrees from true north
- **Thermal zones**: conditioned/unconditioned spaces with areas and ceiling heights
- **Wall components**: 4 orientation walls (N/S/E/W) with areas, constructions, R-values
- **Windows (fenestration)**: per-wall window entries with U-factor, SHGC, area
- **HVAC systems**: heating/cooling equipment with SEER, HSPF, AFUE ratings
- **Domestic hot water**: water heater type, capacity, UEF/EF ratings

### Why a Critic Loop?

LLM-based extraction from architectural drawings is inherently noisy. The same model reading the same PDF can produce different results on different runs. Traditional approaches would require hand-coding extraction rules, which don't scale across the wide variety of Title 24 plan formats.

Instead, we control extraction behavior through **natural-language instruction files** (markdown). This creates an opportunity: a separate "critic" agent can read verification results, diagnose failure patterns, and propose instruction edits — just as a senior engineer would review a junior's work and update the procedure manual.

---

## 2. Architecture

### 2.1 The Agent Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                        EXTRACTION PIPELINE                            │
│                                                                       │
│  PDF Files ──► Discovery Agent ──► Document Map                       │
│                                        │                              │
│                              ┌─────────┴──────────┐                  │
│                              │                     │    ◄─ Parallel   │
│                              ▼                     ▼                  │
│                    Orientation Extractor    Project Extractor          │
│                    (CV Sensors + Two-Pass                              │
│                     + Verification)                                    │
│                              │                     │                  │
│                              └─────────┬───────────┘                  │
│                                        │                              │
│                              ┌─────────┴──────────┐                  │
│                              │    Domain Extraction │  ◄─ Parallel    │
│                              │  (semaphore = 4)     │                  │
│                              ├─ Zones Extractor     │                  │
│                              ├─ Windows Extractor   │                  │
│                              ├─ HVAC Extractor      │                  │
│                              └─ DHW Extractor       │                  │
│                              └──────────────────────┘                  │
│                                        │                              │
│  Results ──► Merge ──► TakeoffSpec ──► BuildingSpec (final output)    │
└──────────────────────────────────────────────────────────────────────┘
```

Each agent in the pipeline is a Claude Code sub-agent invoked via:
```bash
claude --agent <agent-name> --print "<prompt>"
```

Agents read their behavior instructions from:
```
.claude/instructions/<agent-name>/instructions.md
```

### 2.2 The Agents

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| `discovery` | Classify PDF pages by type/subtype | Raw PDFs | `DocumentMap` (page types, subtypes, content tags) |
| `orientation-extractor` | Determine building front orientation | Site plans, floor plans, elevations | `front_orientation` (degrees from true north) |
| `project-extractor` | Extract project metadata + envelope | Schedules, CBECC forms, drawings | `ProjectInfo` + `EnvelopeInfo` |
| `zones-extractor` | Extract thermal zones and walls | Floor plans, sections, wall schedules | `HouseWalls` + `ThermalBoundary` |
| `windows-extractor` | Extract fenestration | Window schedules, elevations | Per-wall `FenestrationEntry` lists |
| `hvac-extractor` | Extract HVAC systems | Equipment schedules, mechanical plans | `HVACSystemEntry` list |
| `dhw-extractor` | Extract water heating | Equipment schedules, plumbing plans | `DHWSystem` list |
| `critic` | Analyze failures and propose instruction changes | Verification results + instruction files | `InstructionProposal` (JSON) |

### 2.3 The Improvement Loop

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        IMPROVEMENT LOOP                                  │
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐       │
│  │ Extract  │───►│ Verify   │───►│ Analyze  │───►│ Critic Agent │       │
│  │ (agents) │    │ (vs GT)  │    │ Failures │    │ (proposes    │       │
│  └──────────┘    └──────────┘    └──────────┘    │  changes)    │       │
│       ▲                                           └──────┬───────┘       │
│       │                                                  │               │
│       │          ┌───────────┐    ┌──────────┐          │               │
│       └──────────│ Apply     │◄───│ Review   │◄─────────┘               │
│                  │ Changes   │    │ Proposal │                           │
│                  └───────────┘    └──────────┘                           │
│                       │                                                  │
│                       ▼                                                  │
│               Instruction files updated                                  │
│               Version bumped                                             │
│               Snapshot saved                                             │
│               Git committed with metrics                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Descriptions

### 3.1 Discovery Phase

**File:** `src/agents/orchestrator.py` → `run_discovery()`

The discovery agent reads every page of every PDF in the evaluation directory and classifies it into a `DocumentMap`:

- **Page types:** `schedule`, `cbecc`, `drawing`, `other`
- **Subtypes:** `site_plan`, `floor_plan`, `elevation`, `section`, `detail`, `mechanical_plan`, `plumbing_plan`, `window_schedule`, `equipment_schedule`, `room_schedule`, `wall_schedule`, `energy_summary`
- **Content tags:** `north_arrow`, `room_labels`, `area_callouts`, `ceiling_heights`, `window_callouts`, `glazing_performance`, `hvac_equipment`, `hvac_specs`, `water_heater`, `dhw_specs`, `wall_assembly`, `insulation_values`

**Native PDF mode (v2.1):** The system reads PDFs directly using `Read(file_path="plans.pdf", pages="1-10")` instead of pre-rasterizing to PNGs. This preserves vector graphics quality (dimension lines, text) that was lost during rasterization. Discovery results are cached to `evals/.cache/{eval_id}_discovery.json` with version-based invalidation.

**Multi-PDF support:** Each evaluation can contain multiple PDFs (e.g., `plans.pdf` + `spec_sheet.pdf`). Pages are assigned global numbers across all PDFs for unified routing, with `pdf_name` and `pdf_page_number` tracked for the Read tool.

### 3.2 Intelligent Page Routing

**File:** `src/agents/orchestrator.py` → `get_relevant_pages_for_domain()`

Instead of sending all pages to every extractor, the system routes only relevant pages to each domain:

| Domain | Primary Pages | Tag-Based Pages |
|--------|--------------|-----------------|
| `orientation` | Site plans, floor plans, elevations | Pages with `north_arrow` tag |
| `zones` | Floor plans, sections, details, room/wall schedules | Pages with `room_labels`, `area_callouts`, `ceiling_heights`, `wall_assembly` |
| `windows` | Window schedules, elevations, floor plans | Pages with `glazing_performance`, `window_callouts` |
| `hvac` | Equipment schedules, mechanical plans | Pages with `hvac_equipment`, `hvac_specs` |
| `dhw` | Equipment schedules, plumbing plans | Pages with `water_heater`, `dhw_specs` |

This reduces context size per agent, improves accuracy (less irrelevant information), and reduces cost.

### 3.3 CV Sensors (Computer Vision Pre-Processing)

**Files:**
- `src/cv_sensors/north_arrow.py` — North arrow angle detection
- `src/cv_sensors/wall_detection.py` — Wall edge angle measurement
- `src/cv_sensors/preprocessing.py` — Canny edge detection, Otsu thresholding
- `src/cv_sensors/rendering.py` — PDF page rasterization via PyMuPDF

**What it does:** Before orientation extraction, the pipeline runs deterministic computer vision algorithms on the site plan page to produce *advisory hints* for the LLM. These are not authoritative — the LLM is told to verify them visually and override if inconsistent.

**Pipeline:**
```
PDF page → PyMuPDF render (2x zoom) → NumPy array → OpenCV
  ├── Canny edges → Hough lines → North arrow angle
  └── Canny edges → Hough lines → Dominant wall edge angles
```

This is **rasterized CV**, not vector extraction. The PDF is rendered to a bitmap, then processed with standard OpenCV pipelines (edge detection, Hough line transform, angle measurement).

**North arrow detection:**
1. Search 25% corner regions of the site plan (north arrows appear in margins)
2. Find Hough lines in valid length range (30-250px — filters out page borders and noise)
3. Prefer **non-axis-aligned** lines (tilted arrows stand out; horizontal/vertical lines are dimension marks)
4. Filter contours by area (100-10,000px²) for triangular arrowhead detection
5. Return angle + confidence, or `"none"` if only axis-aligned lines found

**Wall edge detection:**
1. Find Hough lines in building wall length range (50-800px)
2. Cluster by angle (within 5° tolerance)
3. Return dominant angles, perpendicular calculations, and confidence

**Key design insight — advisory, not authoritative:** The CV data acts as *cognitive scaffolding* for the LLM. Even when CV angles are imprecise, their presence primes the LLM toward more careful spatial reasoning. Instructions say "verify visually, override if inconsistent" rather than "trust this value." This prevents bad CV from corrupting results while still providing the cross-reference benefit.

**Impact:** With CV hints, orientation accuracy is 100% on hard evals (ADUs). Without CV, accuracy drops to 80% due to front/back and side/front confusion. The LLM doesn't blindly trust CV — it uses it as a sanity check.

### 3.4 Orientation Extraction (Two-Pass System)

**Files:**
- `.claude/instructions/orientation-extractor/pass1-north-arrow.md`
- `.claude/instructions/orientation-extractor/pass2-elevation-matching.md`
- `src/agents/orchestrator.py` → `run_orientation_twopass_async()`

Orientation is the highest-leverage extraction: a wrong orientation cascades to ~11 downstream errors (4 wall azimuths + 7 window azimuths). The system first runs CV sensors (§3.3) to produce advisory hints, then runs two independent LLM methods in parallel:

**Pass 1 — North Arrow + Street/Entry Direction:**
1. Receive CV hints (north arrow angle, wall edge angles) as advisory reference
2. Find north arrow on site plan → measure angle from page vertical (verify against CV hint)
3. Identify building front (street-facing for homes, entry-facing for ADUs)
4. Measure front direction on the page (drawing angle, cross-reference with CV wall edges)
5. Calculate: `front_orientation = (drawing_angle - north_arrow_angle + 360) % 360`

**Pass 2 — Elevation Labels + Wall Edge Angle:**
1. Receive same CV hints as advisory reference
2. Find which elevation drawing shows the entry door (3'0" swing door, not 6'0" sliders)
3. On the site plan, identify the entry wall using spatial context (closest to street/main house)
4. Measure the wall edge angle on the site plan (verify against CV wall edge hints)
5. Compute perpendicular outward direction → drawing angle
6. Same formula as Pass 1

**Verification logic (confidence-based):**
1. If passes agree within ±20°: average them → high confidence
2. If passes disagree:
   - 70-110° difference → "side/front confusion" detected
   - 160-200° difference → "front/back confusion" detected
   - Other → arbitrary disagreement
3. Trust the pass with higher self-reported confidence
4. On confidence tie: prefer Pass 1

Both passes output structured intermediate JSON (wall angle, north arrow reading, drawing angle) for debugging — not just the final number.

### 3.5 Parallel Domain Extraction

**File:** `src/agents/orchestrator.py` → `run_parallel_extraction()`

After orientation and project extraction complete, the four domain extractors run in parallel using `asyncio`:

```python
tasks = [
    extract_with_retry("zones-extractor", zones_prompt),
    extract_with_retry("windows-extractor", windows_prompt),
    extract_with_retry("hvac-extractor", hvac_prompt),
    extract_with_retry("dhw-extractor", dhw_prompt),
]
results = await asyncio.gather(*tasks)
```

A semaphore (`asyncio.Semaphore(4)`) allows all four extractors to run truly in parallel. Each extractor gets one automatic retry on failure.

**Orientation context propagation:** The zones and windows extractors receive pre-calculated wall azimuths derived from `front_orientation`:

```
E Wall (front) = front_orientation
W Wall (back)  = (front_orientation + 180) % 360
N Wall (left)  = (front_orientation - 90 + 360) % 360
S Wall (right) = (front_orientation + 90) % 360
```

This ensures wall and window azimuths are consistent with the determined building orientation.

### 3.6 Result Merging

**File:** `src/agents/orchestrator.py` → `merge_to_takeoff_spec()`

Domain extraction results are merged into a `TakeoffSpec` (orientation-based: walls keyed as N/E/S/W), then transformed to a `BuildingSpec` (flat arrays) for verification.

Merging handles:
- **Partial failures:** If one extractor fails, others' results are still included
- **Deduplication:** Items with the same name are deduplicated, tracking conflicts
- **Legacy format conversion:** Flat window lists converted to per-wall fenestration
- **Uncertainty flags:** Each extractor can report flags that propagate to the final output

### 3.7 Verification and Ground Truth

**Directory:** `evals/<eval-id>/ground_truth.csv`

Each evaluation case has a ground truth CSV exported from CBECC-Res compliance reports. The verifier compares extracted values against ground truth and computes:

- **Precision:** Fraction of extracted fields that match ground truth
- **Recall:** Fraction of ground truth fields that were extracted
- **F1:** Harmonic mean of precision and recall
- **Error classification:** Each discrepancy is typed as `omission`, `hallucination`, `wrong_value`, or `format_error`
- **Domain breakdown:** Errors counted per domain (project, envelope, walls, windows, zones, hvac, dhw)

### 3.8 The Critic Agent

**Files:**
- `.claude/instructions/critic/instructions.md`
- `.claude/instructions/critic/proposal-format.md`
- `src/improvement/critic.py`

The critic agent is the core of the self-improvement loop. It receives:
1. Aggregated failure analysis across all evaluations
2. List of available instruction files
3. Optionally: a focus directive (e.g., "focus on orientation-extractor")

**Anti-overfitting safeguards:**
The critic instructions contain extensive anti-overfitting rules:

- **Forbidden:** Referencing eval IDs, specific addresses, or hardcoded angle values from test cases
- **Forbidden:** Creating heuristics that only work for observed test images
- **Required:** Proposals must be generic and transferable to unseen buildings
- **Required:** Changes must follow from architectural principles, not test memorization
- **Self-check:** "Would this rule make sense to someone who has never seen these test cases?"

**Output format:** The critic returns a structured `InstructionProposal` JSON:

```json
{
  "target_file": ".claude/instructions/orientation-extractor/instructions.md",
  "current_version": "v2.7.0",
  "proposed_version": "v2.8.0",
  "change_type": "add_section|modify_section|clarify_rule",
  "failure_pattern": "Description of what went wrong",
  "hypothesis": "Why — instruction gap, not code bug",
  "proposed_change": "Exact markdown text to add/modify",
  "expected_impact": "What should improve and by how much",
  "affected_error_types": ["wrong_value"],
  "affected_domains": ["orientation"],
  "estimated_f1_delta": 0.15
}
```

### 3.9 Proposal Application

**File:** `src/improvement/apply.py`

When a proposal is accepted:

1. **Snapshot saved:** The current instruction file is copied to `evals/<eval-id>/results/iteration-NNN/instruction-changes/` before modification
2. **Change applied:** New content is appended (for `add_section`) or merged (for `modify_section`)
3. **Version bumped:** Semantic versioning — minor bump for new sections, patch for clarifications
4. **File written:** Updated instruction file saved back to `.claude/instructions/`

Rollback is always possible by restoring snapshots from any previous iteration.

### 3.10 Interactive Review

**File:** `src/improvement/review.py`

The review UI (powered by Rich) presents proposals with:
- Syntax-highlighted markdown preview of the proposed change
- Failure pattern and hypothesis context
- Expected impact and estimated F1 delta
- Actions: Accept / Edit (opens `$EDITOR`) / Reject / Skip

In `--auto` mode, proposals are accepted without human review for autonomous iteration.

---

## 4. Two Improvement Workflows

### 4.1 Full-Pipeline Loop (`python3 -m improvement improve`)

For comprehensive, all-domain improvement:

```bash
# Single iteration with human review
python3 -m improvement improve

# Autonomous iteration focused on orientation
for i in {1..5}; do
  python3 -m improvement improve --auto --focus orientation-extractor \
    --focus-reason "Orientation errors cascade to wall/window azimuths"
done
```

**Cycle time:** ~10-15 minutes per iteration (extraction + verification + critique)

**Steps:**
1. Load latest verification results from all evals
2. Aggregate failure patterns (error types, domains, sample discrepancies)
3. Invoke critic agent → get proposal
4. Present for review (or auto-accept)
5. Apply proposal, bump version, save snapshot
6. Re-run full extraction pipeline
7. Re-run verification
8. Show before/after metrics comparison (F1, precision, recall, error counts)
9. Git commit with metrics delta

### 4.2 Fast Orientation Loop (`python3 improve_orientation_fast.py`)

For rapid, focused orientation improvement:

```bash
# Single iteration
python3 improve_orientation_fast.py --single

# Up to 10 iterations
python3 improve_orientation_fast.py --max-iterations 10
```

**Cycle time:** ~3-4 minutes per iteration (orientation-only, cached discovery)

**Steps:**
1. Run orientation extraction (parallel across evals, cached discovery)
2. Build orientation-specific failure analysis
3. Invoke critic with orientation focus
4. Extract and auto-apply proposal
5. Re-test orientation
6. Log iteration results to `orientation_improvement_log.json`
7. Repeat until target accuracy or max iterations

### 4.3 Two-Pass Orientation Testing

```bash
# Test all 5 evals with two-pass verification
python3 test_orientation_twopass.py --all

# Test single eval
python3 test_orientation_twopass.py --eval martinez-adu
```

Runs both orientation passes in parallel per eval, applies verification logic, and reports:
- Per-eval: Pass 1 result, Pass 2 result, final result, expected, error, verification type
- Summary: correct count, pass agreement rate, average error

---

## 5. Pipeline Performance

### 5.1 Timing Breakdown (Single Eval)

The pipeline makes **8 total `claude --agent` subprocess invocations** per evaluation. Measured on chamberlin-circle (19 pages, cached discovery):

```
Stage                    Duration   Agent Calls   Parallelism
─────────────────────────────────────────────────────────────
Discovery (cached)         0.0s     0 (cached)    —
Orientation + Project    ~120s      3 total       ◄─ Parallel
  ├─ CV sensors            ~2s      0 (OpenCV)
  ├─ Pass 1 (north arrow) ~70s      1 agent       ┐
  ├─ Pass 2 (elevation)   ~70s      1 agent       ├─ concurrent
  └─ Project extraction  ~110s      1 agent       ┘
Domain extraction        ~160s      4 total       ◄─ Parallel
  ├─ Zones               ~130s      1 agent       ┐
  ├─ Windows             ~130s      1 agent       ├─ concurrent
  ├─ HVAC                ~100s      1 agent       │  (semaphore=4)
  └─ DHW                  ~80s      1 agent       ┘
Merge + transform         0.0s     0              —
─────────────────────────────────────────────────────────────
Total                    ~280s     8 agents       (~4.7 min)
```

### 5.2 Parallelization Strategy

**Before optimization:** Orientation → Project → Domain extraction ran strictly sequentially. A single eval took ~7 minutes.

**After optimization:** Orientation and project extraction now run concurrently via `asyncio.gather()`, since project extraction doesn't depend on orientation data. Combined with bumping the domain extraction semaphore from 3 to 4 (matching the 4 extractors), a single eval dropped to ~4-5 minutes.

```python
# Orientation (async) and Project (sync via to_thread) run concurrently
orientation_data, project_extraction = asyncio.run(
    asyncio.gather(
        run_orientation_twopass_async(eval_dir, document_map),
        asyncio.to_thread(run_project_extraction, eval_dir, document_map)
    )
)
```

### 5.3 Discovery Caching

Discovery is the most expensive single step when not cached (~60s). Since page classifications rarely change between iterations, results are cached to `evals/.cache/{eval_id}_discovery.json` with version-based invalidation. This makes iterative development cycles much faster — the first run classifies pages, subsequent runs skip straight to extraction.

---

## 6. Instruction Files (The Knobs We Turn)

The entire system's behavior is controlled by these instruction files:

| File | Lines | Controls |
|------|-------|----------|
| `discovery/instructions.md` | ~314 | Page classification, subtypes, content tags |
| `orientation-extractor/instructions.md` | ~290 | Single-pass orientation (legacy) |
| `orientation-extractor/pass1-north-arrow.md` | ~90 | Pass 1: north arrow + direction |
| `orientation-extractor/pass2-elevation-matching.md` | ~118 | Pass 2: elevation + wall edge angle |
| `project-extractor/instructions.md` | ~250 | Project metadata, envelope info |
| `zones-extractor/instructions.md` | ~300 | Thermal zones, walls, boundaries |
| `windows-extractor/instructions.md` | ~300 | Fenestration per wall |
| `hvac-extractor/instructions.md` | ~200 | HVAC systems and distribution |
| `dhw-extractor/instructions.md` | ~200 | Water heating systems |
| `critic/instructions.md` | ~294 | Critic behavior and anti-overfitting rules |
| `critic/proposal-format.md` | ~236 | Proposal JSON schema and examples |

Each instruction file follows a consistent structure:
- **Version header** (semantic versioning, e.g., `v2.8.0`)
- **How to Read PDFs** section (Read tool usage)
- **Output schema** (exact JSON structure expected)
- **Step-by-step extraction process**
- **Examples** (worked calculations with numbers)
- **Common mistakes** (explicitly called out anti-patterns)
- **Confidence levels** (high/medium/low criteria)

---

## 7. Evaluation Dataset

| Eval ID | Building | Location | CZ | Type | Key Challenge |
|---------|----------|----------|----|------|---------------|
| `chamberlin-circle` | 4720 Chamberlin Cir | Elk Grove, CA | 12 | ADU (320 SF) | Small building, ductless heat pump |
| `canterbury-rd` | 1961 Canterbury Rd | Sacramento, CA | 12 | Single Family | Natural gas, multi-story |
| `martinez-adu` | 745 Wyoming St ADU | Martinez, CA | 12 | ADU (2BR) | Rotated building on lot, long axis vertical |
| `poonian-adu` | Poonian Residence ADU | San Jose, CA | 4 | ADU (1160 SF) | Subtle footprint tilt, heat pump WH |
| `lamb-adu` | Lamb ADU | Napa, CA | 2 | ADU | Front/back confusion (entry vs deck) |

---

## 8. Key Design Decisions

### 8.1 Instructions Over Code

By encoding extraction logic in natural-language instructions rather than Python code, we gain:
- **Critic-accessible:** An LLM can read, analyze, and modify instructions
- **Transparent:** Anyone (including non-engineers) can read and understand extraction rules
- **Flexible:** No code deployment needed to change behavior
- **Generalizable:** Instructions describe *how* to extract, not hard-coded rules for specific documents

### 8.2 Implementation-Blind Critic

The critic agent is explicitly forbidden from reading agent code or orchestrator logic. It only sees:
- Verification results (what was wrong)
- Instruction files (what the agent was told to do)

This forces proposals to be about *instruction clarity*, not implementation details, which produces more robust improvements.

### 8.3 Two-Pass Verification for Orientation

Rather than trusting a single LLM call for the highest-leverage extraction, we run two independent methods and cross-validate. This:
- **Catches systematic errors:** 90° side/front confusion and 180° front/back confusion are explicitly detected
- **Increases confidence:** Agreement between independent methods is a strong signal
- **Provides diagnostics:** Disagreement type tells us *what* went wrong, not just that it's wrong

### 8.4 Anti-Overfitting by Design

The improvement loop includes multiple layers of overfitting prevention:

1. **Critic instructions:** Explicitly forbid eval-specific references, hardcoded test angles, test-case-derived heuristics
2. **Self-check protocol:** "Would this rule make sense to someone who has never seen these test cases?"
3. **Aggregate analysis:** Critic sees aggregate patterns across all evals, not individual case details (in the full-pipeline mode)
4. **Version tracking:** Every change is versioned and snapshot-saved, enabling rollback if a change hurts generalization
5. **Metrics comparison:** Before/after F1, precision, recall shown after each iteration

### 8.5 CV Hints as Advisory, Not Authoritative

Computer vision measurements on architectural drawings are inherently noisy — Hough line detection finds hundreds of valid-length lines from dimension marks, text annotations, and detail symbols. Rather than trying to make CV perfectly accurate, we present its results as *advisory hints* the LLM should verify visually.

This works because:
- **LLMs are good at visual verification** — confirming "does this angle match what I see?" is easier than measuring from scratch
- **Bad authority corrupts reasoning** — "do NOT re-estimate" prevents the LLM from correcting wrong values
- **Cross-reference primes careful analysis** — the mere presence of a reference value causes the LLM to reason more carefully about spatial relationships, reducing front/back and side/front confusion errors

### 8.6 Pipeline Parallelization

The pipeline exploits data dependencies to maximize concurrency:
- **Orientation + Project run in parallel** after discovery (project doesn't need orientation)
- **All 4 domain extractors run concurrently** (semaphore=4 matches extractor count)
- **Two orientation passes run in parallel** within the orientation stage

This reduced single-eval time from ~7 minutes to ~4-5 minutes without any accuracy tradeoffs.

### 8.7 Cached Discovery

Discovery is expensive (~2-3 minutes per eval). Since page classifications rarely change, results are cached with version-based invalidation. This reduces the fast orientation loop from ~15 minutes to ~3 minutes per iteration.

---

## 9. Results and Observations

### Orientation Extraction

**Latest results (5 runs per eval, two-pass + CV sensors):**

| Eval | With CV | Without CV | Avg Error | Key Insight |
|------|---------|------------|-----------|-------------|
| canterbury-rd | 5/5 (100%) | 5/5 (100%) | 0° | Stable |
| chamberlin-circle | 5/5 (100%) | 5/5 (100%) | 0° | Stable |
| poonian-adu | 5/5 (100%) | 5/5 (100%) | 0.2° | Was 30% before CV fix |
| lamb-adu | **5/5 (100%)** | 3/5 (60%) | 2.5° | CV prevents front/back confusion |
| martinez-adu | **5/5 (100%)** | 4/5 (80%) | 2.2° | CV prevents side/front confusion |
| **Total** | **25/25 (100%)** | **22/25 (88%)** | | |

**Evolution:** Early in development, poonian-adu (30%) and lamb-adu (30%) were the hardest cases. Instruction tuning improved them partially, but the two-pass system + CV sensors eliminated the remaining errors. The CV data acts as cognitive scaffolding — it doesn't need to be perfectly accurate to help the LLM reason more carefully about spatial relationships.

### Lessons from the Improvement Loop

1. **Simpler instructions are more robust.** After ~15 iterations, instructions accumulate cruft. A manual rewrite to simpler, clearer instructions often outperforms incremental additions.

2. **Complexity trades off across evals.** Adding a complex rule to fix one eval often breaks another. The improvement loop naturally discovers this because it tests across all evals.

3. **Run-to-run variability sets a floor.** LLM non-determinism means the same instructions can produce different results. After a point, instruction tuning can't reduce variability further — only architectural changes (like two-pass verification) can.

4. **Structured intermediate values are essential for debugging.** Requiring agents to output their intermediate calculations (north arrow angle, drawing angle, wall edge direction) makes it possible to diagnose *where* in the reasoning chain errors occur.

5. **The critic catches patterns humans miss.** Aggregate analysis across 5+ evals reveals systematic biases (e.g., "model confuses left-of-vertical vs right-of-vertical north arrows") that are hard to spot from individual test failures.

6. **CV data as cognitive scaffolding works better than CV data as authority.** When CV hints are presented as "verify visually, override if inconsistent," the LLM benefits from the cross-reference without being corrupted by bad measurements. When presented as "do NOT re-estimate," even slightly wrong CV values propagate directly to the output. The presence of advisory CV data changes LLM reasoning behavior — it primes more careful spatial analysis even when the data itself is imprecise.

---

## 10. How to Run

### Full Extraction
```bash
# Run complete extraction pipeline on an eval
python3 -m agents extract chamberlin-circle

# Run on all evals
python3 -m agents extract-all
```

### Verification
```bash
# Verify extraction against ground truth
python3 -m verifier verify-all --save
```

### Improvement Loop
```bash
# Interactive improvement iteration
python3 -m improvement improve

# Autonomous focused iteration
python3 -m improvement improve --auto --focus orientation-extractor

# Fast orientation-only iteration
python3 improve_orientation_fast.py --single

# Two-pass orientation test
python3 test_orientation_twopass.py --all
```

### Rollback
```bash
# Rollback to iteration 5's instructions
python3 -m improvement rollback 5
```

---

## 11. File Reference

### Core Pipeline
| File | Purpose |
|------|---------|
| `src/agents/orchestrator.py` | Pipeline orchestration, agent invocation, merging |
| `src/schemas/discovery.py` | `DocumentMap`, `PageInfo`, `PDFSource` models |
| `src/schemas/building_spec.py` | `BuildingSpec` output schema |
| `src/schemas/takeoff_spec.py` | `TakeoffSpec` orientation-based schema |
| `src/schemas/transform.py` | TakeoffSpec → BuildingSpec transformation |

### CV Sensors
| File | Purpose |
|------|---------|
| `src/cv_sensors/north_arrow.py` | North arrow angle detection (Hough lines + contour analysis) |
| `src/cv_sensors/wall_detection.py` | Wall edge angle measurement |
| `src/cv_sensors/preprocessing.py` | Canny edge detection, Otsu thresholding |
| `src/cv_sensors/rendering.py` | PDF page rasterization via PyMuPDF |

### Improvement Loop
| File | Purpose |
|------|---------|
| `src/improvement/critic.py` | Failure aggregation, critic invocation, proposal parsing |
| `src/improvement/apply.py` | Proposal application, version management, snapshots |
| `src/improvement/review.py` | Interactive proposal review (Rich UI) |
| `src/improvement/cli.py` | CLI commands: `improve`, `apply`, `rollback`, `context` |

### Fast Iteration Scripts
| File | Purpose |
|------|---------|
| `test_orientation_fast.py` | Fast single-pass orientation testing |
| `test_orientation_twopass.py` | Two-pass orientation testing with verification |
| `improve_orientation_fast.py` | Automated orientation improvement loop |

### Instructions
| File | Purpose |
|------|---------|
| `.claude/instructions/discovery/instructions.md` | Page classification rules |
| `.claude/instructions/orientation-extractor/pass1-north-arrow.md` | Pass 1 method |
| `.claude/instructions/orientation-extractor/pass2-elevation-matching.md` | Pass 2 method |
| `.claude/instructions/orientation-extractor/instructions.md` | Legacy single-pass |
| `.claude/instructions/critic/instructions.md` | Critic behavior rules |
| `.claude/instructions/critic/proposal-format.md` | Proposal JSON schema |

### Evaluation Data
| Path | Contents |
|------|----------|
| `evals/manifest.yaml` | Evaluation case registry |
| `evals/<id>/plans.pdf` | Source architectural plans |
| `evals/<id>/spec_sheet.pdf` | Additional spec sheets |
| `evals/<id>/ground_truth.csv` | CBECC-Res ground truth |
| `evals/<id>/results/iteration-NNN/` | Per-iteration extraction results and instruction snapshots |

---

## 12. Future Directions

1. **More evaluation cases:** 5 evals is a small dataset. Adding 10-20 more diverse building types (multi-story, mixed-use, additions) would improve generalization confidence.

2. **~~CV-based north arrow detection~~** ~~Using computer vision (OpenCV) to detect and measure north arrow angles programmatically.~~ **Done.** CV sensors for north arrow and wall edge detection are integrated with advisory hints. Orientation now at 100% accuracy across all evals.

3. **Domain-specific fast loops:** Extending the fast orientation loop pattern to other domains (windows, HVAC) for rapid, focused improvement.

4. **Regression testing:** Automatically running all evals after every instruction change and blocking changes that regress any previously-passing case.

5. **Smaller/faster models for cost optimization:** Early testing shows Haiku can handle some extraction passes at 1.2x speed improvement and significantly lower cost. A hybrid approach using Haiku for simpler domains (DHW, project) and Sonnet for complex domains (orientation, zones) could reduce cost without sacrificing accuracy.

6. **Further pipeline parallelization:** Domain extraction could potentially start immediately after discovery rather than waiting for orientation, since orientation is only needed at the merge step. This would save another ~120s per eval.
