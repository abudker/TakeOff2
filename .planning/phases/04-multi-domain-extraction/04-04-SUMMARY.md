---
phase: 04-multi-domain-extraction
plan: 04
subsystem: cli
tags: [click, yaml, extraction, diagnostics, verbose]

# Dependency graph
requires:
  - phase: 04-03
    provides: orchestrator with parallel multi-domain extraction
provides:
  - extract-all command runs extraction on all 5 evals
  - verbose diagnostics for extract-one and extract-all
  - per-domain extraction status display
  - conflict count reporting
affects: [05-scoring-iteration, 06-multi-project]

# Tech tracking
tech-stack:
  added: []
  patterns: [verbose diagnostics pattern with show_diagnostics helper]

key-files:
  created: []
  modified: [src/agents/cli.py]

key-decisions:
  - "Verbose flag shows per-domain status, retry count, and conflicts"
  - "Extract-all outputs concise component counts in normal mode, detailed diagnostics in verbose"

patterns-established:
  - "show_diagnostics() pattern: reusable helper for extraction status display"

# Metrics
duration: 2min
completed: 2026-02-04
---

# Phase 04 Plan 04: CLI Verbose Diagnostics Summary

**CLI extended with extract-all for all 5 evals and --verbose flag for per-domain extraction diagnostics**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-04T04:32:17Z
- **Completed:** 2026-02-04T04:34:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `show_diagnostics()` helper for verbose extraction status display
- Added `--verbose/-v` flag to both `extract-one` and `extract-all` commands
- Updated `extract-all` to properly handle manifest.yaml dict format
- Summary output shows per-eval component counts and conflict tallies

## Task Commits

Each task was committed atomically:

1. **Task 1: Add extract-all Command with Verbose Diagnostics** - `af91dfe` (feat)
2. **Task 2: Verify End-to-End Pipeline** - verification only (no commit)

## Files Created/Modified
- `src/agents/cli.py` - Added show_diagnostics(), verbose flag to extract-one and extract-all

## Decisions Made
- Verbose flag shows extraction status per domain, retry count, items extracted, and errors
- First 5 conflicts displayed in verbose mode, with count of remaining
- Per-eval summary in verbose mode uses compact format: zones/walls/windows/hvac/dhw

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 complete: all requirements met (EXT-03 through EXT-08)
- 5 extractor agents in place: project, zones, windows, hvac, dhw
- 7 instruction files present (6 extractors + verifier)
- extract-all ready to run extraction across all 5 evals
- Ready for Phase 5: Scoring and Iteration

---
*Phase: 04-multi-domain-extraction*
*Completed: 2026-02-04*
