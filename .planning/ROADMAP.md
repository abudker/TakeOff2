# Roadmap: Takeoff v2

## Overview

Build a self-improving agentic extraction system that pulls building specifications from California Title 24 plans and outputs structured data for EnergyPlus modeling. The system starts with evaluation infrastructure (can't improve what you can't measure), builds a robust PDF processing pipeline, creates a multi-agent extraction system using Claude Code agents, and implements a self-improvement loop that analyzes failures and proposes changes to agent instructions. Target: 0.90 F1 across 5 evaluation cases through hill-climbing optimization.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Agent architecture + evaluation infrastructure
- [x] **Phase 2: Document Processing** - PDF preprocessing pipeline
- [x] **Phase 3: Single-Domain Extraction** - Discovery + first extractor + orchestrator foundation
- [x] **Phase 4: Multi-Domain Extraction** - Complete extraction system
- [ ] **Phase 5: Manual Improvement Loop** - Critic analysis + proposal system
- [ ] **Phase 6: Automated Improvement Loop** - Full automation + iteration management

## Phase Details

### Phase 1: Foundation
**Goal**: Establish dynamic agent architecture and evaluation infrastructure to measure extraction quality
**Depends on**: Nothing (first phase)
**Requirements**: ARCH-01, ARCH-02, ARCH-03, EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06
**Success Criteria** (what must be TRUE):
  1. Agent definitions load instructions from external files (not hardcoded prompts)
  2. User can run verification on a single extraction result and see precision/recall/F1
  3. User can run verification on all 5 evals with one command and see aggregate metrics
  4. Verifier outputs field-level discrepancies categorized by failure type (omission, hallucination, format error, wrong value)
  5. Verifier generates HTML report showing results, field comparisons, and failure details
  6. Evaluation results persist and can be tracked across iterations
**Plans**: 3 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md — Dynamic agent architecture (instructions in external files)
- [x] 01-02-PLAN.md — Verifier core (comparison, metrics, CLI)
- [x] 01-03-PLAN.md — HTML reporting and iteration persistence

### Phase 2: Document Processing
**Goal**: PDF preprocessing pipeline that handles Claude's size and structured output limits
**Depends on**: Phase 1
**Requirements**: PDF-01, PDF-02
**Success Criteria** (what must be TRUE):
  1. User can rasterize a Title 24 PDF into Claude-readable format with one command
  2. User can preprocess all eval PDFs with one command
  3. Preprocessed PDFs stay within Claude's context window limits
  4. Preprocessing preserves critical information (schedules, diagrams, CBECC pages)
**Plans**: 1 plan in 1 wave

Plans:
- [x] 02-01-PLAN.md — PDF rasterization pipeline (PyMuPDF + CLI)

### Phase 3: Single-Domain Extraction
**Goal**: Validate extraction pattern with discovery agent, first domain extractor, and orchestrator foundation
**Depends on**: Phase 2
**Requirements**: EXT-01, EXT-02, EXT-06
**Success Criteria** (what must be TRUE):
  1. Discovery agent successfully scans a Title 24 PDF and maps document structure (schedules, CBECC pages, drawings)
  2. Project extractor accurately extracts project metadata and envelope data from mapped structure
  3. Orchestrator coordinates discovery → extraction flow and produces BuildingSpec JSON
  4. User can run extraction on a single eval and verify output against ground truth
  5. Baseline F1 established for project/envelope domain
**Plans**: 4 plans in 3 waves

Plans:
- [x] 03-01-PLAN.md — Discovery agent (schema + agent definition + classification instructions)
- [x] 03-02-PLAN.md — Project extractor (agent definition + field extraction guide)
- [x] 03-03-PLAN.md — Orchestrator + CLI (direct API - superseded by 03-04)
- [x] 03-04-PLAN.md — Rewrite orchestrator to use Claude Code agents (fix architecture)

### Phase 4: Multi-Domain Extraction
**Goal**: Complete multi-agent extraction system covering all domains
**Depends on**: Phase 3
**Requirements**: EXT-03, EXT-04, EXT-05, EXT-07, EXT-08
**Success Criteria** (what must be TRUE):
  1. Zones extractor successfully extracts zones and walls from Title 24 plans
  2. Windows extractor successfully extracts all fenestration data
  3. HVAC extractor successfully extracts mechanical systems and water heaters
  4. Orchestrator merges results from all extractors into complete BuildingSpec
  5. User can run extraction on all 5 evals with one command
  6. Full extraction pipeline produces measurable F1 scores across all domains
**Plans**: 4 plans in 3 waves

Plans:
- [x] 04-01-PLAN.md — Zones and Windows extractor agents
- [x] 04-02-PLAN.md — HVAC and DHW extractor agents
- [x] 04-03-PLAN.md — Parallel orchestration with asyncio and merge logic
- [x] 04-04-PLAN.md — CLI extract-all command and verbose diagnostics

### Phase 5: Manual Improvement Loop
**Goal**: Critic analyzes failures and proposes instruction file changes
**Depends on**: Phase 4
**Requirements**: IMP-01, IMP-02, IMP-03
**Success Criteria** (what must be TRUE):
  1. Critic agent analyzes verification results and identifies specific failure patterns
  2. Critic proposes targeted changes to instruction files (not agent definitions)
  3. Proposals include clear rationale and expected impact
  4. User can manually apply a proposal, re-run extraction/eval, and measure improvement
  5. At least one iteration demonstrates measurable F1 improvement
**Plans**: 4 plans in 4 waves

Plans:
- [ ] 05-01-PLAN.md — Critic agent and failure analysis foundation
- [ ] 05-02-PLAN.md — Interactive review and proposal application
- [ ] 05-03-PLAN.md — CLI integration and iteration tracking
- [ ] 05-04-PLAN.md — End-to-end verification (checkpoint)

### Phase 6: Automated Improvement Loop
**Goal**: Full automation of improvement loop to reach 0.90 F1 target
**Depends on**: Phase 5
**Requirements**: IMP-04, IMP-05, IMP-06, IMP-07, IMP-08, IMP-09, TARGET-01
**Success Criteria** (what must be TRUE):
  1. Loop runner automatically applies proposals, re-runs extraction/eval, and commits results
  2. Loop runs for N iterations or until target F1 reached (whichever first)
  3. Each iteration is committed with metrics enabling rollback
  4. Loop tracks iteration history showing F1 progression and changes made
  5. Loop detects plateau (no improvement for K iterations) and stops early
  6. User can resume loop from any previous iteration
  7. System achieves 0.90 F1 across all 5 evals
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD
- [ ] 06-04: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-02-03 |
| 2. Document Processing | 1/1 | Complete | 2026-02-03 |
| 3. Single-Domain Extraction | 4/4 | Complete | 2026-02-04 |
| 4. Multi-Domain Extraction | 4/4 | Complete | 2026-02-04 |
| 5. Manual Improvement Loop | 0/4 | Planned | - |
| 6. Automated Improvement Loop | 0/TBD | Not started | - |

---
*Last updated: 2026-02-04 after Phase 5 planning*
