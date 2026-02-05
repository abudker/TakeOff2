# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Extract building specs from Title 24 PDFs accurately enough to feed EnergyPlus modeling (0.90 F1 target)
**Current focus:** Phase 7 Complete - Human verification needed for outcomes

## Current Position

Phase: 7 of 7 (CV Sensors)
Plan: 2 of 2 in current phase
Status: Phase complete (infrastructure verified, outcomes need human testing)
Last activity: 2026-02-05 - Completed 07-02-PLAN.md

Progress: [█████████░] ~90%

## Performance Metrics

**Velocity:**
- Total plans completed: 17
- Average duration: 3.6 min
- Total execution time: 1.05 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 11 min | 3.7 min |
| 02-document-processing | 1 | 3 min | 3.0 min |
| 03-single-domain-extraction | 4 | 13 min | 3.2 min |
| 04-multi-domain-extraction | 4 | 17 min | 4.25 min |
| 05-manual-improvement-loop | 3 | 9 min | 3.0 min |
| 07-cv-sensors | 2 | 13 min | 6.5 min |

**Recent Trend:**
- Last 5 plans: 05-02 (2 min), 05-03 (2 min), 07-01 (5 min), 07-02 (8 min)
- Trend: Phase 7 plans taking longer (integration complexity, CV validation)

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
- CLI orchestrates via subprocess (python3 -m agents, python3 -m verifier) not direct imports (05-03)
- Iteration number tracked globally (max across all evals + 1) (05-03)
- Auto-commit with metrics delta in commit message (05-03)
- Rollback by copying snapshots from iteration directories (05-03)
- Dual detection (Hough lines + contours) for north arrow robustness (07-01)
- Coordinate system: negate dy for inverted y-axis, convert to compass bearing (07-01)
- Wall angles normalized to [0, 180) since direction doesn't matter (07-01)
- K-means clustering (k=2) for building rotation from wall angles (07-01)
- CV sensors run in orchestrator before agent invocation, not inside agents (07-02)
- CV hints injected as JSON text block in prompts, not as tool calls (07-02)
- LLM retains all semantic reasoning, CV provides only geometric measurements (07-02)
- Optional cv_hints parameter maintains backwards compatibility (07-02)

### Roadmap Evolution

- Phase 7 added: CV Sensors — deterministic geometry sensing to reduce orientation variance and eliminate ±90°/±180° errors
- OpenRouter multi-model experiment parked on branch `experiment/openrouter-multi-model` — results not compelling (Claude's advantage is multi-turn tool use, not vision)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-05T18:30:00Z
Stopped at: Phase 7 complete — human verification needed for outcome metrics
Resume file: None

---
*Last updated: 2026-02-05 after Phase 7 execution*
