---
phase: 07-cv-sensors
plan: 02
subsystem: cv-sensors
tags: [opencv, orchestrator, hybrid-cv-llm, orientation-extraction, prompt-injection]

# Dependency graph
requires:
  - phase: 07-cv-sensors-01
    provides: CV sensor module with north arrow and wall edge detection
  - phase: 04-multi-domain-extraction
    provides: Orchestrator pattern and orientation extraction pipeline
provides:
  - Hybrid CV+LLM orientation pipeline with deterministic geometry inputs
  - CV hints injected into orientation pass prompts as structured JSON
  - Backwards-compatible --no-cv flag for A/B testing
  - Integration tests validating end-to-end orientation with CV hints
affects: [orientation-extractor, two-pass-verification, hybrid-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hybrid CV+LLM pattern: CV for geometry, LLM for semantics"
    - "CV hint injection via JSON block in agent prompts"
    - "Numpy type conversion helper for JSON serialization"
    - "Graceful degradation when CV sensors fail"

key-files:
  created: []
  modified:
    - src/agents/orchestrator.py
    - .claude/instructions/orientation-extractor/pass1-north-arrow.md
    - .claude/instructions/orientation-extractor/pass2-elevation-matching.md
    - test_orientation_twopass.py

key-decisions:
  - "CV sensors run in orchestrator before agent invocation (not inside agent)"
  - "CV hints injected as JSON text block in prompt, not as tool calls"
  - "LLM retains ALL semantic reasoning (which wall, building type, entry location)"
  - "Simplified fallback instructions (removed verbose tables, kept one-line references)"
  - "Optional cv_hints parameter maintains backwards compatibility"

patterns-established:
  - "run_cv_sensors() as module-level function for easy import/reuse"
  - "_convert_numpy_types() helper recursively handles numpy int32/float64 in nested dicts"
  - "Using CV Hints sections in instructions separate from Fallback sections"
  - "CV confidence 'none' signals fallback to visual estimation"

# Metrics
duration: 8min
completed: 2026-02-05
---

# Phase 7 Plan 2: Hybrid CV+LLM Orientation Pipeline

**CV-measured angles injected into orientation prompts as structured hints, LLM uses precise measurements for geometry while retaining semantic reasoning**

## Performance

- **Duration:** 8 minutes 18 seconds
- **Started:** 2026-02-05T18:13:05Z
- **Completed:** 2026-02-05T18:21:23Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- CV sensors integrated into orchestrator orientation pipeline
- CV hints (north arrow angle, wall edges, building rotation) injected into both orientation passes
- Instruction files updated with "Using CV Hints" sections and simplified fallback paths
- End-to-end validation passes on canterbury-rd (90° orientation, 0° error)
- Backwards compatibility maintained via --no-cv flag

## Task Commits

Each task was committed atomically:

1. **Task 1: Integrate CV sensors into orchestrator orientation pipeline** - `8f49f2c` (feat)
2. **Task 2: Update orientation instruction files to use CV hints** - `008d465` (feat)
3. **Task 3: Update test runner and run orientation evaluation** - `557c2f7` (feat)

## Files Created/Modified

- `src/agents/orchestrator.py` - Added run_cv_sensors(), cv_hints injection in orientation passes, numpy type conversion helper
- `.claude/instructions/orientation-extractor/pass1-north-arrow.md` - Added CV hints section to Steps 1 and 3, simplified fallback to one-line references
- `.claude/instructions/orientation-extractor/pass2-elevation-matching.md` - Added CV hints sections to Steps 2 and 3, simplified fallback instructions
- `test_orientation_twopass.py` - Import run_cv_sensors, inject cv_hints into passes, add --no-cv flag

## Decisions Made

**CV sensors run in orchestrator, not in agent:** The orchestrator invokes agents via subprocess (`claude --agent`), so CV sensors must run in the orchestrator's Python process before building the prompt. This keeps the agent stateless and focused on reasoning.

**CV hints as JSON text, not tool calls:** CV measurements are injected as a JSON block in the prompt text. The agent reads them as part of the prompt context, not via Read tool calls. This is simpler and more transparent than creating intermediate files or extending the agent's tool access.

**Division of labor - CV for geometry, LLM for semantics:** CV sensors provide precise angle measurements (north arrow, wall edges, building rotation). The LLM still does ALL semantic reasoning: which elevation shows the entry? is this an ADU? which wall on the site plan is the entry wall? This preserves the LLM's strengths while eliminating visual estimation variance.

**Simplified fallback instructions:** Removed verbose tables (8-row direction table, 3-bullet tilt disambiguation) and replaced with one-line references. CV hints sections add ~15 lines, simplifications remove ~15 lines, net zero change in file length. Instructions stay under 91-111 lines.

**Backwards compatibility via optional parameter:** The `cv_hints` parameter is Optional with None default. If cv_hints is None or CV sensors fail, the pipeline works exactly as before. This enables A/B testing via --no-cv flag.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Numpy type serialization:** CV sensor functions return dicts with numpy int32/float64 values, which aren't JSON serializable. Added `_convert_numpy_types()` helper that recursively converts all numpy types to native Python types (int, float, list). This handles nested structures like debug info cleanly.

## Validation Results

**End-to-end test with CV hints (canterbury-rd):**
- CV sensors detected: north=90.0°, walls=8 edges, building_rot=90.0°
- Pass 1 orientation: 90°
- Pass 2 orientation: 90°
- Final orientation: 90° (agreement)
- Expected: 90°
- Error: 0.0°
- Status: ✓ PASS

**Backwards compatibility test without CV hints (--no-cv):**
- Pass 1 orientation: 90°
- Pass 2 orientation: 90°
- Final orientation: 90° (agreement)
- Expected: 90°
- Error: 0.0°
- Status: ✓ PASS

Both tests produce identical results on canterbury-rd, confirming backwards compatibility.

## Architecture Notes

**Integration flow:**
1. Orchestrator calls `run_cv_sensors(eval_dir, document_map)` before orientation passes
2. `run_cv_sensors()` finds site plan page, renders to NumPy array, runs 3 CV detections
3. Results converted to Python-native types and packaged as cv_hints dict
4. cv_hints serialized to JSON and injected into orientation pass prompts
5. Agent reads CV measurements from prompt and applies them per instructions
6. Agent still reads instruction files via Read tool for method details

**Error handling:**
- If CV sensors fail entirely (exception), pipeline proceeds without hints
- If CV detection returns low confidence, LLM falls back to visual estimation
- Graceful degradation at multiple levels ensures robustness

**Instruction file structure:**
- Step 1/2/3 sections gain "Using CV Hints" subsections at the top
- "Fallback (no CV hints)" subsections replace verbose estimation tables
- Clear separation: CV hints are primary path, fallback is backup
- LLM knows to check cv_hints.confidence field before using measurements

## Next Phase Readiness

**Ready for evaluation:** The hybrid CV+LLM pipeline is complete and validated on one eval (canterbury-rd). Next step is to run on all 5 evals to measure impact:
- Does CV reduce variance on poonian-adu (currently 30% pass rate)?
- Does CV prevent front/back confusion on lamb-adu (currently 30% pass rate)?
- Does CV maintain 100% on chamberlin-circle and martinez-adu?

**Evaluation command:**
```bash
python3 test_orientation_twopass.py --all
```

**A/B comparison:**
```bash
python3 test_orientation_twopass.py --all --no-cv  # baseline without CV
python3 test_orientation_twopass.py --all          # with CV hints
```

**No blockers:** Integration is complete. Ready to measure performance improvement on full eval suite.

---
*Phase: 07-cv-sensors*
*Completed: 2026-02-05*
