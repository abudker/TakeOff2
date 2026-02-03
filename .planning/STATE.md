# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Extract building specs from Title 24 PDFs accurately enough to feed EnergyPlus modeling (0.90 F1 target)
**Current focus:** Phase 3 - Single-Domain Extraction (next)

## Current Position

Phase: 3 of 6 (Single-Domain Extraction)
Plan: 3 of TBD in current phase
Status: In progress
Last activity: 2026-02-03 — Completed 03-03-PLAN.md

Progress: [███░░░░░░░] ~40%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 3.1 min
- Total execution time: 0.36 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 11 min | 3.7 min |
| 02-document-processing | 1 | 3 min | 3.0 min |
| 03-single-domain-extraction | 3 | 9 min | 3.0 min |

**Recent Trend:**
- Last 5 plans: 02-01 (3 min), 03-01 (2 min), 03-02 (3 min), 03-03 (4 min)
- Trend: Stable

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
- LangGraph StateGraph for extraction orchestration: clear state management, node-based execution (03-03)
- Anthropic Files API for image upload: required for structured outputs with vision (03-03)
- Combined ProjectExtraction schema: single API call for project + envelope (03-03)
- Page filtering before extraction: send only schedule/cbecc pages to reduce tokens (03-03)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-03T23:12:41Z
Stopped at: Completed 03-03-PLAN.md
Resume file: None

---
*Last updated: 2026-02-03 after 03-03 execution*
