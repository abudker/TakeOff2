# Phase 4: Multi-Domain Extraction - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete multi-agent extraction system covering zones, windows, HVAC, and DHW. Orchestrator merges results from all extractors into complete BuildingSpec. User can run extraction on all 5 evals with one command and measure F1 scores across all domains.

</domain>

<decisions>
## Implementation Decisions

### Extractor Boundaries
- Four domain extractors: Zones, Windows, HVAC, DHW (water heaters separate from HVAC)
- Extractors gather all data they find — orchestrator deduplicates and reconciles
- Shared discovery: discovery agent maps document once, extractors receive relevant page subsets
- Parallel initial extraction, then sequential reconciliation by orchestrator

### Merge Strategy
- When extractors report different values for same field: flag for review (don't auto-resolve)
- Conflicts appear in separate 'conflicts' section in BuildingSpec output
- Array deduplication uses name matching (match by zone/window/system name)
- Orchestrator always runs reconciliation pass after parallel extraction to clarify conflicts

### Error Handling
- Extractor failure: retry once, then continue with partial results
- Partial extractions indicated via top-level 'extraction_status' field with per-domain details
- Diagnostics (tokens, timing, retries) available via --verbose flag

### Output Completeness
- 90% F1 is current target, 100% is ultimate goal
- Metrics tell the full story — any extraction that produces output is technically successful

### Claude's Discretion
- Heuristics for detecting "suspiciously sparse" extractor output
- Missing field representation (null vs omit vs default) per field type
- Whether confidence scores add value for improvement loop
- Whether provenance info (source page/section) aids debugging

</decisions>

<specifics>
## Specific Ideas

- Parallel extraction → sequential reconciliation pattern: extract fast, reconcile carefully
- Conflicts section rather than inline conflict metadata — keeps main output clean
- User wants to reach 100% accuracy eventually; 90% F1 is the milestone target

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-multi-domain-extraction*
*Context gathered: 2026-02-03*
