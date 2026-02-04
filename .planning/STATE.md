# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Extract building specs from Title 24 PDFs accurately enough to feed EnergyPlus modeling (0.90 F1 target)
**Current focus:** Phase 3 - Single-Domain Extraction (next)

## Current Position

Phase: 3 of 6 (Single-Domain Extraction)
Plan: 4 of 4 in current phase
Status: Phase complete
Last activity: 2026-02-04 — Completed 03-04-PLAN.md

Progress: [████░░░░░░] ~50%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 3.2 min
- Total execution time: 0.43 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 11 min | 3.7 min |
| 02-document-processing | 1 | 3 min | 3.0 min |
| 03-single-domain-extraction | 4 | 13 min | 3.2 min |

**Recent Trend:**
- Last 5 plans: 03-01 (2 min), 03-02 (3 min), 03-03 (4 min), 03-04 (4 min)
- Trend: Stable around 3 min/plan

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-04T00:34:58Z
Stopped at: Completed 03-04-PLAN.md (Phase 3 complete)
Resume file: None

---
*Last updated: 2026-02-04 after 03-04 execution*
