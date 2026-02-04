---
phase: 04-multi-domain-extraction
plan: 03
subsystem: extraction
tags: [asyncio, parallel, orchestrator, conflict-detection, merge]

# Dependency graph
requires:
  - phase: 04-01
    provides: Zones and windows extractor field guides
  - phase: 04-02
    provides: HVAC and DHW extractor field guides
provides:
  - Parallel multi-domain extraction via asyncio
  - Extraction result merging with conflict detection
  - Per-domain extraction status tracking
  - Name-based deduplication for array elements
affects: [04-04, 05-evaluation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncio.gather for parallel agent invocation
    - Semaphore-based concurrency control (max 3 concurrent)
    - Retry-on-failure pattern for extraction robustness
    - Name-based deduplication with conflict tracking

key-files:
  created: []
  modified:
    - src/schemas/building_spec.py
    - src/agents/orchestrator.py

key-decisions:
  - "Semaphore limit of 3 concurrent extractors to avoid overwhelming system"
  - "One retry on failure before marking extraction as failed"
  - "Name-based deduplication keeps first occurrence, logs conflict"
  - "Extraction continues with partial results if one domain fails"

patterns-established:
  - "Async wrapper pattern: asyncio.to_thread for blocking subprocess calls"
  - "ExtractionStatus model for per-domain tracking"
  - "ExtractionConflict model for flagging values needing review"

# Metrics
duration: 3min
completed: 2026-02-04
---

# Phase 4 Plan 03: Parallel Multi-Domain Extraction Summary

**Asyncio-based parallel extraction for 4 domain extractors with merge logic, conflict detection, and graceful partial failure handling**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-04T04:27:20Z
- **Completed:** 2026-02-04T04:29:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended BuildingSpec schema with ExtractionConflict and ExtractionStatus models
- Implemented asyncio-based parallel extraction for zones, windows, HVAC, and DHW
- Created merge logic with name-based deduplication and conflict flagging
- Updated orchestrator to support parallel extraction by default with legacy fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Extraction Metadata to Schema** - `98ce9e4` (feat)
2. **Task 2: Implement Parallel Extraction with Merge Logic** - `de88f8e` (feat)

## Files Created/Modified

- `src/schemas/building_spec.py` - Added ExtractionConflict, ExtractionStatus models and fields to BuildingSpec
- `src/agents/orchestrator.py` - Extended from 377 to 714 lines with parallel extraction infrastructure

## Key Functions Added to orchestrator.py

| Function | Purpose |
|----------|---------|
| `invoke_claude_agent_async` | Async wrapper with semaphore for concurrent agent calls |
| `extract_with_retry` | Single retry on failure, returns (data, status) tuple |
| `build_domain_prompt` | Constructs domain-specific extraction prompts |
| `run_parallel_extraction` | Runs 4 extractors in parallel via asyncio.gather |
| `deduplicate_by_name` | Removes duplicates by name, tracks conflicts |
| `merge_extractions` | Combines all extractions into BuildingSpec |

## Decisions Made

- **Semaphore limit (3):** Balances parallelism with system resource constraints
- **One retry policy:** Quick recovery from transient failures without excessive delays
- **First-occurrence wins:** For duplicates, keep first and log conflict for review
- **Partial failure tolerance:** Extraction continues even if one domain fails

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Orchestrator ready for full multi-domain extraction
- All 4 domain extractors (zones, windows, hvac, dhw) can now be invoked in parallel
- Conflict detection ready for reconciliation phase (04-04)
- Extraction status tracking enables debugging and monitoring

---
*Phase: 04-multi-domain-extraction*
*Completed: 2026-02-04*
