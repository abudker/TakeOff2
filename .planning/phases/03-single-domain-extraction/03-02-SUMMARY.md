---
phase: 03
plan: 02
subsystem: extraction-agents
tags: [agent-definition, extraction-instructions, field-mapping, project-metadata, envelope-data]
dependencies:
  requires: [01-02-schema-definitions, 02-01-preprocessing, 03-01-discovery]
  provides: [project-extractor-agent, extraction-workflow, field-guide]
  affects: [03-03-orchestrator, 04-multi-domain-extraction]
tech-stack:
  added: []
  patterns: [thin-agent-wrapper, instruction-separation, field-to-source-mapping]
key-files:
  created:
    - .claude/agents/project-extractor.md
    - .claude/instructions/project-extractor/instructions.md
    - .claude/instructions/project-extractor/field-guide.md
  modified: []
decisions:
  - id: thin-agent-pattern
    choice: "Agent definition under 50 lines, all behavior in separate instruction files"
    rationale: "Follows verifier pattern for maintainability and clear separation of concerns"
  - id: field-guide-format
    choice: "Detailed field-by-field mapping with document sources, extraction tips, and examples"
    rationale: "Provides extractor agent with precise guidance on where to find each schema field in Title 24 docs"
  - id: extraction-priority
    choice: "CBECC-Res pages highest priority, then CF1R forms, then schedules, then title block"
    rationale: "CBECC software output is most standardized and reliable for extraction"
metrics:
  duration: 3 minutes
  completed: 2026-02-03
---

# Phase 3 Plan 2: Project Extractor Agent Summary

**One-liner:** Created project extraction agent with comprehensive field guide mapping 14 schema fields to Title 24 document sources

## What Was Built

### Agent Definition (40 lines)
Created `.claude/agents/project-extractor.md` following thin-wrapper pattern:
- Name: project-extractor
- Tools: Read, Bash
- References: @.claude/instructions/project-extractor/instructions.md and field-guide.md
- Input: Page images + DocumentMap JSON
- Output: JSON with ProjectInfo and EnvelopeInfo

### Extraction Instructions (170 lines)
Created `.claude/instructions/project-extractor/instructions.md` covering:

**Extraction workflow:**
1. Input reception (page images + document map)
2. Page prioritization (CBECC → CF1R → schedules → title block)
3. Field extraction using field guide
4. Data merging (later pages override earlier values)
5. Schema validation
6. Confidence reporting
7. JSON output formatting

**Key features:**
- Handles missing data (required vs optional fields)
- Cross-referencing strategy for validation
- Error handling for illegible text, conflicting values, missing pages
- Unit conversion guidance
- Quality checks before output

### Field Guide (440 lines)
Created `.claude/instructions/project-extractor/field-guide.md` with detailed mappings:

**ProjectInfo fields (9):**
1. `run_title` → Cover page, CBECC, CF1R title blocks
2. `address` → Title block, CBECC project location
3. `city` → Title block, CBECC, jurisdiction field
4. `climate_zone` → CBECC (CZ field), CF1R header
5. `fuel_type` → CBECC, equipment schedules (gas vs electric)
6. `house_type` → CBECC building type, CF1R classification
7. `dwelling_units` → CBECC, CF1R building description
8. `stories` → CBECC, elevation drawings, floor plans
9. `bedrooms` → CBECC, floor plan room labels

**EnvelopeInfo fields (5):**
1. `conditioned_floor_area` → CBECC CFA field, CF1R, floor plans
2. `window_area` → Window schedule totals, CBECC fenestration
3. `window_to_floor_ratio` → CBECC WWR field, or calculate from areas
4. `exterior_wall_area` → Wall schedule totals, CBECC envelope summary
5. `fenestration_u_factor` → Window schedule (area-weighted avg), CBECC

**For each field:**
- Document sources prioritized by reliability
- Extraction tips with common labels and formats
- Example values showing typical ranges
- Calculation methods when direct extraction unavailable

## Implementation Details

### Extraction Pattern
The agent uses document map from discovery phase to focus on relevant pages:
- `schedule_pages`: Window/wall schedules with area calculations
- `cbecc_pages`: CBECC-Res software output (most reliable)
- `cf1r_pages`: Official compliance forms with structured fields
- `drawings`: Floor plans and elevations for counts

### Data Merging Strategy
When field appears on multiple pages:
1. Start with empty data structure
2. Process pages in priority order (CBECC → CF1R → schedules → title)
3. Later values override earlier values (CBECC most authoritative)
4. Track which page provided each field

### Confidence Reporting
Agent reports extraction confidence in notes field:
- **High:** From CBECC/CF1R, clearly legible, cross-referenced
- **Medium:** From schedule/drawing, legible, may be calculated
- **Low:** Hand-written, OCR uncertain, conflicting values

### Quality Checks
Built-in validation before output:
- All required fields populated (13 of 14 fields required)
- Climate zone in range 1-16
- Window-to-floor ratio < 1.0 and reasonable (0.10-0.30 typical)
- CFA matches floor plan dimensions (within ~5%)
- Bedroom/story counts match drawings
- Fuel type matches equipment schedules
- All areas in square feet

## Key Design Decisions

### Why Thin Agent Wrapper?
Following verifier pattern established in Phase 1:
- Agent definition focuses on role and workflow
- Detailed instructions in separate markdown files
- Easy to modify instructions without touching agent code
- Clear separation: agent = orchestration, instructions = domain knowledge

### Why Field Guide Format?
Detailed field-by-field mapping provides:
- **Precision:** Exact labels to look for ("CFA", "Climate Zone 12", "CZ 3")
- **Context:** Where fields appear in different document types
- **Examples:** Typical values to validate against (CZ 1-16, WWR 0.10-0.30)
- **Fallbacks:** Calculation methods when direct extraction fails

This is critical because Title 24 documents have:
- Multiple formats (CBECC, CF1R, hand-drawn plans)
- Inconsistent labeling ("CFA" vs "Conditioned Floor Area" vs "Heated Area")
- Data spread across multiple pages
- Need for cross-referencing to validate accuracy

### Why Source Prioritization?
CBECC-Res pages are highest priority because:
- Standardized software output format
- Calculated values (more accurate than hand-measured)
- Contains majority of required fields
- Most reliable for compliance verification

CF1R forms second priority:
- Official California compliance forms
- Structured field layout
- Legally required accuracy

Schedules and drawings lowest priority:
- Variable formats
- May have calculation errors
- Hand-written annotations less reliable

## What's Next

### Immediate Next Step (Plan 03-03)
Create orchestrator agent that:
1. Invokes discovery agent → DocumentMap
2. Invokes project-extractor → ProjectInfo + EnvelopeInfo
3. Saves extraction JSON to iteration directory
4. Returns structured output for verification

### Phase 3 Completion
After orchestrator (03-03), Phase 3 is complete and validates:
- End-to-end extraction pipeline (discovery → extraction → output)
- Pattern for later domain extraction (zones, windows, HVAC)
- Integration with preprocessing and verification

### Phase 4 Preview
Multi-domain extraction will follow same pattern:
- Zone extractor: Zone names, floor areas, volumes
- Window extractor: Individual windows with U-factors, SHGC
- HVAC extractor: System types, capacities, efficiencies
- Water heater extractor: Tank size, efficiency, fuel type

Each will have:
- Thin agent definition (~40 lines)
- Detailed extraction instructions
- Field guide mapping schema to documents

## Testing Readiness

The project extractor is ready to be:
1. **Invoked** by orchestrator with page images and document map
2. **Tested** against eval PDFs to measure extraction accuracy
3. **Verified** by comparing output against ground truth CSVs
4. **Improved** through self-improvement loop based on discrepancies

Target: F1 >= 0.90 across all 14 fields

## Commits

| Hash | Message | Files |
|------|---------|-------|
| 771ec32 | feat(03-02): create project extractor agent definition | .claude/agents/project-extractor.md |
| b873650 | feat(03-02): create extraction instructions and field guide | instructions.md, field-guide.md |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Phase 3 Plan 3 (Orchestrator) ready to start:**
- [x] Project extractor agent defined
- [x] Extraction instructions complete
- [x] Field guide covers all ProjectInfo + EnvelopeInfo fields
- [x] Schema references available (building_spec.py)
- [x] Discovery agent available (from 03-01)
- [x] Preprocessor available (from 02-01)

**Blockers:** None

**Confidence:** High - extraction pattern validated, ready for orchestration

---

*Completed: 2026-02-03*
*Duration: 3 minutes*
*Status: ✓ Success*
