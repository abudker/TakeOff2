# Requirements

## v1 Requirements

### PDF Processing
- [ ] **PDF-01**: User can rasterize a Title 24 PDF into Claude-readable format
- [ ] **PDF-02**: User can run preprocessing on all eval PDFs with one command

### Extraction Agents
- [ ] **EXT-01**: Discovery agent scans PDF and maps document structure (schedules, CBECC pages, drawings)
- [ ] **EXT-02**: Project extractor agent extracts project metadata and envelope data
- [ ] **EXT-03**: Zones extractor agent extracts zones and walls
- [ ] **EXT-04**: Windows extractor agent extracts all fenestration
- [ ] **EXT-05**: HVAC extractor agent extracts mechanical systems and water heaters
- [ ] **EXT-06**: Orchestrator agent coordinates extraction flow and merges results into BuildingSpec
- [ ] **EXT-07**: User can run full extraction pipeline on a single eval
- [ ] **EXT-08**: User can run extraction on all 5 evals with one command

### Evaluation Agents
- [ ] **EVAL-01**: Verifier agent compares extracted JSON against ground_truth.csv
- [ ] **EVAL-02**: Verifier outputs precision/recall/F1 and field-level discrepancies
- [ ] **EVAL-03**: Verifier categorizes failures (omission, hallucination, format error, wrong value)
- [ ] **EVAL-04**: User can run verification on a single extraction result
- [ ] **EVAL-05**: User can run verification on all 5 evals and see aggregate metrics
- [ ] **EVAL-06**: Verifier generates HTML report showing results, field comparisons, and failure details

### Agent Architecture
- [ ] **ARCH-01**: Agent definitions (.claude/agents/*.md) are thin wrappers that load dynamic instructions
- [ ] **ARCH-02**: Dynamic instructions stored in separate files (e.g., prompts/*.md) that can be edited without restart
- [ ] **ARCH-03**: Critic proposes edits to instruction files, not agent definitions

### Improvement Loop
- [ ] **IMP-01**: Critic agent analyzes verification results and identifies failure patterns
- [ ] **IMP-02**: Critic agent proposes specific changes to instruction files
- [ ] **IMP-03**: Proposals include rationale and expected impact
- [ ] **IMP-04**: Loop runner can automatically apply proposals and re-run extraction/eval
- [ ] **IMP-05**: Loop runs for N iterations or until target F1 reached (whichever first)
- [ ] **IMP-06**: Each iteration is committed with metrics (enables rollback)
- [ ] **IMP-07**: Loop tracks iteration history (F1 progression, changes made)
- [ ] **IMP-08**: Loop detects plateau (no improvement for K iterations) and stops early
- [ ] **IMP-09**: User can resume loop from any previous iteration

### Target
- [ ] **TARGET-01**: Achieve 0.90 F1 across all 5 evals

## v2 Requirements (Deferred)

- Automated prompt improvement suggestions
- DSPy integration for systematic optimization
- Multi-agent orchestration with supervisor pattern
- A/B testing of prompt variants
- Regression detection

## Out of Scope

- Production deployment / API — this is R&D
- UI — CLI and agent-driven only
- Changing output schema — fixed by EnergyPlus
- Supporting non-Title 24 documents
- Complex Python infrastructure (Instructor, LangGraph, etc.)

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 1 | Pending |
| ARCH-02 | Phase 1 | Pending |
| ARCH-03 | Phase 1 | Pending |
| EVAL-01 | Phase 1 | Pending |
| EVAL-02 | Phase 1 | Pending |
| EVAL-03 | Phase 1 | Pending |
| EVAL-04 | Phase 1 | Pending |
| EVAL-05 | Phase 1 | Pending |
| EVAL-06 | Phase 1 | Pending |
| PDF-01 | Phase 2 | Pending |
| PDF-02 | Phase 2 | Pending |
| EXT-01 | Phase 3 | Pending |
| EXT-02 | Phase 3 | Pending |
| EXT-06 | Phase 3 | Pending |
| EXT-03 | Phase 4 | Pending |
| EXT-04 | Phase 4 | Pending |
| EXT-05 | Phase 4 | Pending |
| EXT-07 | Phase 4 | Pending |
| EXT-08 | Phase 4 | Pending |
| IMP-01 | Phase 5 | Pending |
| IMP-02 | Phase 5 | Pending |
| IMP-03 | Phase 5 | Pending |
| IMP-04 | Phase 6 | Pending |
| IMP-05 | Phase 6 | Pending |
| IMP-06 | Phase 6 | Pending |
| IMP-07 | Phase 6 | Pending |
| IMP-08 | Phase 6 | Pending |
| IMP-09 | Phase 6 | Pending |
| TARGET-01 | Phase 6 | Pending |

---
*Last updated: 2026-02-03 after roadmap creation*
