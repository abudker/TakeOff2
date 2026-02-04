---
phase: 04-multi-domain-extraction
plan: 02
subsystem: extraction
tags: [hvac, dhw, water-heating, heat-pump, ductwork, title-24, claude-code-agents]

# Dependency graph
requires:
  - phase: 03-single-domain-extraction
    provides: thin agent pattern, extractor workflow conventions
provides:
  - HVAC extractor agent for heating/cooling/distribution systems
  - DHW extractor agent for water heating systems
  - Field guides mapping 45 total fields to Title 24 document sources
affects: [04-03, 04-04, orchestration, verifier]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Thin agent definition referencing external instruction files
    - Field guide format with document sources, extraction tips, typical values
    - Page prioritization (CBECC > CF1R > schedules > drawings)

key-files:
  created:
    - .claude/agents/hvac-extractor.md
    - .claude/instructions/hvac-extractor/instructions.md
    - .claude/instructions/hvac-extractor/field-guide.md
    - .claude/agents/dhw-extractor.md
    - .claude/instructions/dhw-extractor/instructions.md
    - .claude/instructions/dhw-extractor/field-guide.md
  modified: []

key-decisions:
  - "HVAC system_type enum: Heat Pump, Furnace, Split System, Package Unit, Ductless, Other"
  - "Water heater fuel enum: Electric Resistance, Natural Gas, Heat Pump"
  - "UEF preferred over EF for energy efficiency (current standard)"
  - "SEER2 preferred over SEER for cooling efficiency (current standard)"

patterns-established:
  - "Field guide includes California Title 24 typical values and thresholds"
  - "Extraction tips include unit conversion guidance (tons to Btuh, kW to watts)"
  - "Confidence scoring: high (CBECC), medium (schedule), low (inferred)"

# Metrics
duration: 6min
completed: 2026-02-04
---

# Phase 04 Plan 02: HVAC & DHW Extractor Agents Summary

**Created HVAC and DHW extractor agents with comprehensive field guides covering 45 total fields for heating, cooling, distribution, and water heating system extraction from Title 24 documents.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-04T04:18:44Z
- **Completed:** 2026-02-04T04:24:43Z
- **Tasks:** 2
- **Files created:** 6

## Accomplishments
- Created hvac-extractor agent with field guide mapping 27 fields (HVACSystem, HeatPumpHeating, HeatPumpCooling, DistributionSystem)
- Created dhw-extractor agent with field guide mapping 18 fields (WaterHeatingSystem, WaterHeater)
- Documented California Title 24 2022/2023 requirements (heat pump mandates, SEER2/HSPF2 standards)
- Included typical value ranges for efficiency ratings, capacities, and duct specifications

## Task Commits

Each task was committed atomically:

1. **Task 1: Create HVAC Extractor Agent** - `d42e467` (feat)
2. **Task 2: Create DHW Extractor Agent** - `74ff6c8` (feat)

## Files Created

- `.claude/agents/hvac-extractor.md` - Thin agent definition (35 lines)
- `.claude/instructions/hvac-extractor/instructions.md` - Extraction workflow (277 lines)
- `.claude/instructions/hvac-extractor/field-guide.md` - Field mappings (715 lines)
- `.claude/agents/dhw-extractor.md` - Thin agent definition (35 lines)
- `.claude/instructions/dhw-extractor/instructions.md` - Extraction workflow (249 lines)
- `.claude/instructions/dhw-extractor/field-guide.md` - Field mappings (588 lines)

## Decisions Made

1. **HVAC system type enum:** Heat Pump, Furnace, Split System, Package Unit, Ductless, Other - covers all residential HVAC configurations
2. **Water heater fuel types:** Electric Resistance, Natural Gas, Heat Pump - distinguishes heat pump from standard electric
3. **Efficiency standards:** SEER2/HSPF2 for HVAC, UEF for water heating - current Title 24 2022 standards
4. **Duct location types:** DuctsInConditioned, DuctsInAttic, DuctsInGarage, etc. - from CBECC-Res terminology

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both agents followed the established thin agent pattern from Phase 03.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four domain extractors now complete (project, zones, hvac, dhw)
- Ready for 04-03: Remaining components (windows, ceilings, floors) extractors
- Ready for 04-04: Orchestrator integration with all extractors
- Field guide format proven and can be replicated for remaining domains

---
*Phase: 04-multi-domain-extraction*
*Completed: 2026-02-04*
