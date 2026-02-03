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
| PDF-01 | TBD | Pending |
| PDF-02 | TBD | Pending |
| EXT-01 | TBD | Pending |
| EXT-02 | TBD | Pending |
| EXT-03 | TBD | Pending |
| EXT-04 | TBD | Pending |
| EXT-05 | TBD | Pending |
| EXT-06 | TBD | Pending |
| EXT-07 | TBD | Pending |
| EXT-08 | TBD | Pending |
| EVAL-01 | TBD | Pending |
| EVAL-02 | TBD | Pending |
| EVAL-03 | TBD | Pending |
| EVAL-04 | TBD | Pending |
| EVAL-05 | TBD | Pending |
| ARCH-01 | TBD | Pending |
| ARCH-02 | TBD | Pending |
| ARCH-03 | TBD | Pending |
| IMP-01 | TBD | Pending |
| IMP-02 | TBD | Pending |
| IMP-03 | TBD | Pending |
| IMP-04 | TBD | Pending |
| IMP-05 | TBD | Pending |
| IMP-06 | TBD | Pending |
| IMP-07 | TBD | Pending |
| IMP-08 | TBD | Pending |
| IMP-09 | TBD | Pending |
| TARGET-01 | TBD | Pending |

---
*Last updated: 2026-02-03 after requirements definition*
