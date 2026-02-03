---
phase: 03-single-domain-extraction
plan: 01
subsystem: extraction
tags: [pydantic, claude, discovery, document-mapping]

# Dependency graph
requires:
  - phase: 02-document-processing
    provides: PDF rasterization pipeline for page images
provides:
  - DocumentMap schema for structure mapping
  - Discovery agent with Title 24 page classification
  - Classification instructions for schedule/cbecc/drawing/other pages
affects: [03-02-orchestrator, 03-03-schedule-extraction, 03-04-cbecc-extraction]

# Tech tracking
tech-stack:
  added: [schemas.discovery]
  patterns: [thin agent wrapper with external instructions]

key-files:
  created:
    - src/schemas/discovery.py
    - .claude/agents/discovery.md
    - .claude/instructions/discovery/instructions.md
  modified:
    - src/schemas/__init__.py

key-decisions:
  - "PageType enum with four categories: schedule, cbecc, drawing, other"
  - "Three-level confidence system: high (explicit markers), medium (clear content), low (ambiguous)"
  - "DocumentMap provides convenience properties for filtering page lists by type"

patterns-established:
  - "Agent definitions stay under 50 lines, reference external instructions via @-syntax"
  - "Classification instructions include visual markers, content patterns, and examples per category"

# Metrics
duration: 2min
completed: 2026-02-03
---

# Phase 03 Plan 01: Discovery Agent Summary

**Pydantic DocumentMap schema with PageType enum and discovery agent for Title 24 page classification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-03T23:01:45Z
- **Completed:** 2026-02-03T23:04:01Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- DocumentMap and PageInfo Pydantic models with page type classification
- Discovery agent definition following thin-wrapper pattern (29 lines)
- Comprehensive classification instructions with visual markers and confidence criteria
- Ready for orchestrator to invoke discovery and receive structured document map

## Task Commits

Each task was committed atomically:

1. **Task 1: Create discovery schema** - `73f223f` (feat)
2. **Task 2: Create discovery agent with instructions** - `1bc6af1` (feat)

## Files Created/Modified
- `src/schemas/discovery.py` - DocumentMap, PageInfo, PageType models for structure mapping
- `src/schemas/__init__.py` - Export discovery schema models
- `.claude/agents/discovery.md` - Discovery agent definition (29 lines)
- `.claude/instructions/discovery/instructions.md` - Page classification criteria and workflow

## Decisions Made
- **PageType categories:** Chose four types (schedule, cbecc, drawing, other) based on Title 24 document structure and extraction needs
- **Confidence levels:** Three-tier system allows downstream extractors to prioritize high-confidence pages first
- **Convenience properties:** DocumentMap.schedule_pages, cbecc_pages, drawing_pages provide filtered lists for easier orchestrator logic

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Discovery schema validates and exports correctly
- Agent definition ready for orchestrator invocation
- Classification instructions provide clear criteria for all four page types
- Ready for Plan 02 (orchestrator) to integrate discovery into extraction pipeline
- Confidence levels enable prioritization strategies (process high-confidence pages first)

---
*Phase: 03-single-domain-extraction*
*Completed: 2026-02-03*
