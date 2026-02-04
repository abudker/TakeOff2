---
phase: 04-multi-domain-extraction
plan: 01
subsystem: extraction
tags: [claude-code-agents, zones, walls, windows, fenestration, thin-agent-pattern]

# Dependency graph
requires:
  - phase: 03-single-domain-extraction
    provides: Thin agent pattern (project-extractor) and orchestration (extract.py)
provides:
  - Zones extractor agent for ZoneInfo and WallComponent extraction
  - Windows extractor agent for WindowComponent extraction
  - Field guides mapping schema fields to Title 24 document sources
affects: [04-02, 04-03, 05-orchestration, extraction-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Domain-specific extractors with dedicated field guides"
    - "Wall-to-zone and window-to-wall linking conventions"

key-files:
  created:
    - ".claude/agents/zones-extractor.md"
    - ".claude/instructions/zones-extractor/instructions.md"
    - ".claude/instructions/zones-extractor/field-guide.md"
    - ".claude/agents/windows-extractor.md"
    - ".claude/instructions/windows-extractor/instructions.md"
    - ".claude/instructions/windows-extractor/field-guide.md"
  modified: []

key-decisions:
  - "Use orientation-based wall naming (Zone 1 - N Wall) for consistent linking"
  - "Include glazed doors (SGD) in windows extraction for complete fenestration"
  - "Field guides provide extraction tips and typical value ranges for validation"

patterns-established:
  - "Domain extractor pattern: agent definition + instructions + field-guide"
  - "Linking convention: child components reference parent by exact name match"

# Metrics
duration: 6 min
completed: 2026-02-04
---

# Phase 4 Plan 1: Zones and Windows Extractors Summary

**Two domain extractors created following thin agent pattern: zones-extractor (ZoneInfo + WallComponent) and windows-extractor (WindowComponent) with comprehensive field guides mapping all schema fields to Title 24 document sources.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-04T04:17:56Z
- **Completed:** 2026-02-04T04:24:00Z
- **Tasks:** 2
- **Files created:** 6

## Accomplishments

- Zones extractor agent with instructions for thermal zone and wall component extraction
- Windows extractor agent with instructions for fenestration extraction
- Field guides mapping 13 ZoneInfo fields, 10 WallComponent fields, and 11 WindowComponent fields
- Extraction tips including typical value ranges, common document labels, and validation checks
- Linking conventions for wall-to-zone and window-to-wall relationships

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Zones Extractor Agent** - `6e36d05` (feat)
2. **Task 2: Create Windows Extractor Agent** - `3988fb4` (feat)

## Files Created/Modified

- `.claude/agents/zones-extractor.md` - Agent definition with thin wrapper pattern
- `.claude/instructions/zones-extractor/instructions.md` - Zone/wall extraction workflow (292 lines)
- `.claude/instructions/zones-extractor/field-guide.md` - Field mapping for ZoneInfo and WallComponent (738 lines)
- `.claude/agents/windows-extractor.md` - Agent definition for fenestration
- `.claude/instructions/windows-extractor/instructions.md` - Window extraction workflow (338 lines)
- `.claude/instructions/windows-extractor/field-guide.md` - Field mapping for WindowComponent (516 lines)

## Decisions Made

1. **Orientation-based wall naming:** Use format "Zone 1 - N Wall" for multi-zone buildings to enable clear wall-to-zone linking
2. **Glazed door inclusion:** Include sliding glass doors and glazed entry doors in windows extraction since they function as fenestration
3. **Field guide depth:** Include typical value ranges, common document labels, and extraction tips for each field to aid accuracy
4. **Linking convention:** Child components (walls, windows) reference parent by exact name string match

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Zones and windows extractors ready for orchestration integration
- Field guides provide comprehensive mapping for extraction accuracy
- Ready for 04-02: HVAC and Ceilings Extractors
- Pattern established for remaining domain extractors

---
*Phase: 04-multi-domain-extraction*
*Completed: 2026-02-04*
