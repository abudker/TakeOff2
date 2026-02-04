# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Extract building specs from Title 24 PDFs accurately enough to feed EnergyPlus modeling (0.90 F1 target)
**Current focus:** Phase 4 Complete - Ready for Phase 5

## Current Position

Phase: 5 of 6 (Manual Improvement Loop)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-02-03 - Completed 05-02-PLAN.md

Progress: [████████░░] ~80%

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: 3.3 min
- Total execution time: 0.79 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 11 min | 3.7 min |
| 02-document-processing | 1 | 3 min | 3.0 min |
| 03-single-domain-extraction | 4 | 13 min | 3.2 min |
| 04-multi-domain-extraction | 4 | 17 min | 4.25 min |
| 05-manual-improvement-loop | 2 | 7 min | 3.5 min |

**Recent Trend:**
- Last 5 plans: 04-03 (3 min), 04-04 (2 min), 05-01 (5 min), 05-02 (2 min)
- Trend: Phase 5 averaging 3.5 min/plan, trending down from 5.0

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Start fresh (v2) vs iterate on v1: v1 architecture was legacy from non-agentic approach, never worked properly
- Research before building: User wants to learn from prior art on self-improving agents
- Agent definitions kept under 50 lines, all behavioral details in separate instruction files (01-01)
- Four error types: omission, hallucination, format_error, wrong_value (01-01)
- Macro-F1 as primary aggregate metric (01-01, 01-02)
- Python csv module over pandas for CBECC CSV parsing (variable column handling) (01-02)
- Tolerance-based numeric comparison: 1% for areas, 0.5% for ratios (01-02)
- Dark theme HTML reports with pagination (50 discrepancies/page) (01-03)
- Iteration format: iteration-NNN zero-padded directories (01-03)
- PyMuPDF over pdf2image: no external dependencies, faster, self-contained (02-01)
- 1568px max longest edge: Claude's recommended max before auto-resize (02-01)
- PNG format for lossless text legibility in building plans (02-01)
- PageType enum with four categories: schedule, cbecc, drawing, other (03-01)
- Three-level confidence system for page classification: high/medium/low (03-01)
- Thin agent pattern: definitions under 50 lines, behavior in separate instruction files (03-02)
- CBECC-Res pages highest priority for extraction (most reliable/standardized) (03-02)
- Claude Code agent architecture: invoke agents via subprocess instead of direct API calls (03-04)
- Sequential orchestration over LangGraph: simple workflow doesn't need complex graph (03-04)
- JSON extraction with fallbacks: parse agent responses robustly regardless of format (03-04)
- Page filtering before extraction: send only schedule/cbecc pages to reduce tokens (03-03)
- Orientation-based wall naming (Zone 1 - N Wall) for consistent linking (04-01)
- Include glazed doors (SGD) in windows extraction for complete fenestration (04-01)
- HVAC system_type enum: Heat Pump, Furnace, Split System, Package Unit, Ductless, Other (04-02)
- Water heater fuel types: Electric Resistance, Natural Gas, Heat Pump (04-02)
- UEF preferred over EF for water heater efficiency (current standard) (04-02)
- SEER2/HSPF2 preferred over SEER/HSPF for HVAC efficiency (current standard) (04-02)
- Semaphore limit of 3 concurrent extractors for parallel execution (04-03)
- One retry on failure before marking extraction as failed (04-03)
- Name-based deduplication keeps first occurrence, logs conflict (04-03)
- Extraction continues with partial results if one domain fails (04-03)
- Verbose flag shows per-domain status, retry count, and conflicts (04-04)
- Critic operates implementation-blind: analyzes verification results only, not code (05-01)
- Domain extraction from field_path: walls[0].name -> walls, project.run_id -> project (05-01)
- Proposals target ONE instruction file (Phase 5 manual, one at a time) (05-01)
- Version bump rules: add_section/modify_section=minor, clarify_rule=patch (05-01)
- Critic invoked via subprocess (claude --agent critic) not direct API (05-01)
- Rich library for terminal UI with syntax highlighting and tables (05-02)
- Semantic versioning on instruction files (vX.Y.Z in header) (05-02)
- Snapshots saved to iteration directories before modification (05-02)
- Editor integration via $EDITOR environment variable (05-02)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-03T22:12:22Z
Stopped at: Completed 05-02-PLAN.md
Resume file: None

---
*Last updated: 2026-02-03 after 05-02 execution*
