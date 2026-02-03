# Takeoff v2

## What This Is

An agentic extraction system that pulls building specifications from California Title 24 plans and outputs structured data for EnergyPlus energy modeling. Uses Claude Code agents with a self-improvement loop to iterate on agent structure and prompts, hill-climbing toward 0.90 F1 on a set of 5 evaluation cases.

## Core Value

Extract building specs from Title 24 PDFs accurately enough to feed EnergyPlus modeling (0.90 F1 target).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] PDF preprocessing pipeline that handles Claude's size/structured output limits
- [ ] Multi-agent extraction system for Title 24 plans → BuildingSpec JSON
- [ ] Evaluation harness that scores extractions against ground truth (precision/recall/F1)
- [ ] Self-improvement loop that analyzes failures and proposes agent/prompt changes
- [ ] Versioning system for prompts, agent definitions, and evaluation results
- [ ] Achieve 0.90 F1 across all 5 evals

### Out of Scope

- Changing the output schema — dictated by downstream EnergyPlus requirements
- Supporting non-Title 24 documents
- Production deployment / API — this is an R&D system for now
- UI — CLI/agent-driven workflow

## Context

**Previous work (../takeoff):**
- Attempted multi-agent orchestration with discovery → parallel extractors → merge
- Architecture never fully worked; legacy from non-agentic v1 approach
- Reached 0.43 F1 in iteration 1 before stalling
- Key insight: PDF preprocessing (rasterizing) is critical due to Claude's limits
- Key insight: Multiple passes with specialized agents matters

**Extraction schema:**
- ~50+ fields across: project, envelope, zones, walls, windows, HVAC, water heaters
- Ground truth format is CBECC-Res/EnergyPro CSV export structure
- See `evals/*/ground_truth.csv` for exact schema

**Evaluation set:**
- 5 evals in `evals/` directory (ADUs and single-family homes in CA climate zones 2, 4, 12)
- Each has: `plans.pdf`, `spec_sheet.pdf` (optional), `ground_truth.csv`
- Manifest at `evals/manifest.yaml`

**Research interest:**
- Best practices for self-improving Claude Code agents
- Prompt optimization techniques
- Eval-driven development patterns
- Existing tools/frameworks in this space

## Constraints

- **Output schema**: Fixed by EnergyPlus requirements — cannot change field names or structure
- **PDF size**: Claude has strict limits; preprocessing (rasterization, simplification) required
- **Eval set**: 5 cases for hill-climbing; no additional ground truth available currently
- **Structured output**: Large PDFs cause issues with structured output; must manage context carefully

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start fresh (v2) vs iterate on v1 | v1 architecture was legacy from non-agentic approach, never worked properly | — Pending |
| Research before building | User wants to learn from prior art on self-improving agents | — Pending |

---
*Last updated: 2026-02-03 after initialization*
