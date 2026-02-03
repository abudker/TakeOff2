# Feature Research: Self-Improving Agentic Extraction System

**Domain:** Self-improving agent systems for document extraction + prompt optimization
**Researched:** 2026-02-03
**Confidence:** MEDIUM (synthesized from multiple credible sources; some domain-specific aspects extrapolated)

## Executive Summary

This research identifies features for a self-improving agentic extraction system targeting California Title 24 building plans. The system uses Claude Code agents to extract ~50 fields into EnergyPlus format, with a self-improvement loop iterating on agent structure and prompts to achieve 0.90 F1 using 5 eval cases.

Key insight: With only 5 eval cases, the primary risk is **overfitting to the validation set**. Features must balance optimization power against overfitting risk. The system should optimize for **robust generalization**, not just training metrics.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the system must have to function as a self-improving extraction system. Missing these = system does not work.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Ground truth comparison** | Cannot measure improvement without knowing what "correct" looks like | LOW | Store expected outputs for each eval case; compute field-level precision/recall/F1 |
| **Automated evaluation metric (F1)** | Manual evaluation does not scale; need consistent scoring | LOW | Field-level exact match or fuzzy match scoring; aggregated F1 across all fields |
| **Iteration tracking** | Must know which prompt/config produced which score | LOW | Log each run: timestamp, config hash, per-case scores, aggregate score |
| **Prompt versioning** | Must track what changed between iterations | LOW | Git-based or simple file versioning; diff-able prompts |
| **Single improvement step** | Core of hill-climbing: make one change, measure impact | MEDIUM | Generate candidate modification, run eval, accept/reject based on score delta |
| **Structured output schema** | Extraction requires defined output format for comparison | LOW | JSON schema for EnergyPlus fields; validation against schema |
| **Error capture and logging** | Must see why extractions fail (parse errors, missing fields, wrong values) | LOW | Capture LLM output, schema validation errors, field-level mismatches |

### Differentiators (Competitive Advantage)

Features that make the self-improvement loop actually effective. Not required, but dramatically improve results.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Error categorization/analysis** | Know WHY failures happen (wrong format vs. wrong value vs. missing field) | MEDIUM | Classify errors: schema violation, value mismatch, omission, hallucination; enables targeted fixes |
| **Feedback-driven prompt refinement** | Use error analysis to guide specific improvements | MEDIUM | LLM analyzes errors, proposes targeted prompt modifications; like FIPO/PromptWizard approach |
| **Few-shot example selection** | Right examples dramatically improve extraction accuracy | MEDIUM | Bootstrap from successful extractions; DSPy BootstrapFewShot pattern; select diverse exemplars |
| **Multi-restart optimization** | Avoid local optima; explore prompt space more broadly | MEDIUM | Run N independent optimization trajectories with different starting points; keep best |
| **Cross-validation / held-out testing** | Detect overfitting before it destroys generalization | HIGH | With 5 cases: leave-one-out CV; report both train and held-out scores |
| **Field-level diagnostic dashboard** | See which specific fields are problematic; focus improvement efforts | MEDIUM | Per-field F1 scores; trend over iterations; identify persistently failing fields |
| **Confidence scoring per extraction** | Know when to trust outputs vs. flag for review | MEDIUM | LLM confidence, multi-sample agreement, schema compliance score |
| **Retry with self-correction** | Agent catches own errors and retries | MEDIUM | Validation check after extraction; if fails, re-extract with error context; up to 3 retries |
| **Visual grounding / source tracing** | Know WHERE in document each field came from | HIGH | Store page/section references for each extracted value; enables debugging |
| **Instruction optimization (not just examples)** | Systematic prompt instruction improvement | HIGH | DSPy MIPROv2 / COPRO style; propose instruction variants, evaluate, select best |

### Anti-Features (Deliberately NOT Build for R&D System)

Features that seem good but create problems for an R&D system with small eval sets.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Production-grade UI** | Looks professional | Massive distraction; R&D needs speed not polish | CLI + simple logging; invest in eval quality instead |
| **Real-time streaming** | Feels responsive | Complicates debugging; unnecessary for batch R&D | Batch processing with progress logs |
| **Aggressive caching** | Saves API costs | Hides non-determinism; masks whether changes actually work | Minimal caching; run fresh for eval |
| **Fine-tuning the model** | Higher performance ceiling | Requires much more data (100s-1000s examples); overkill for 5 eval cases | Prompt optimization only; fine-tune later if needed |
| **Complex multi-agent orchestration** | Sophisticated architecture | Hard to debug; attribution unclear; changes have unclear effects | Single agent with clear responsibility; add agents only when single fails |
| **Automated prompt rewriting at scale** | Explore more options | With 5 cases, overfits instantly; explores noise not signal | Conservative changes; one modification at a time; validate generalization |
| **LLM-as-judge for quality** | Automate evaluation | Unreliable for structured extraction; you have ground truth, use it | Direct field comparison against ground truth |
| **Database-backed experiment tracking** | Professional tooling | Over-engineering for R&D; files are simpler and sufficient | JSON/CSV logs; SQLite only if genuinely needed |
| **Hyperparameter sweep automation** | Systematic exploration | With 5 cases, any sweep overfits; false confidence in "optimal" settings | Manual iteration with hypothesis-driven changes |
| **Ensemble extraction** | Higher accuracy | Expensive; complex; diminishing returns when prompts are not yet good | Single best prompt; ensemble only after diminishing returns |

---

## Feature Dependencies

```
[Ground Truth Comparison]
    |
    +---> [Automated F1 Metric]
              |
              +---> [Single Improvement Step]
                        |
                        +---> [Iteration Tracking]
                        |
                        +---> [Multi-Restart Optimization]
                        |
                        +---> [Instruction Optimization]

[Error Capture]
    |
    +---> [Error Categorization]
              |
              +---> [Feedback-Driven Refinement]

[Structured Output Schema]
    |
    +---> [Retry with Self-Correction]
    |
    +---> [Confidence Scoring]

[Prompt Versioning]
    |
    +---> [Few-Shot Example Selection]
              |
              +---> [Cross-Validation]
```

### Dependency Notes

- **F1 Metric requires Ground Truth**: Cannot compute F1 without knowing expected outputs
- **Improvement Step requires F1 Metric**: Cannot evaluate changes without scoring function
- **Error Categorization requires Error Capture**: Must capture errors before classifying them
- **Feedback-Driven Refinement requires Error Categorization**: Targeted fixes need error diagnosis
- **Cross-Validation requires Iteration Tracking**: Must record scores to compare train vs. held-out
- **Few-Shot Selection requires Prompt Versioning**: Must track which examples used in which version

---

## MVP Definition

### Launch With (v1) - Minimum Viable Self-Improvement Loop

The absolute minimum to validate that self-improvement works for this extraction task.

- [x] **Ground truth comparison** - Store 5 eval cases with expected outputs
- [x] **Automated F1 metric** - Compute field-level and aggregate F1
- [x] **Iteration tracking** - Log each run with config, scores, timestamp
- [x] **Prompt versioning** - Version control for prompts/agent configs
- [x] **Single improvement step** - Make change, measure, accept/reject
- [x] **Structured output schema** - JSON schema for EnergyPlus fields
- [x] **Error capture** - Log extraction failures and mismatches

**Why this is MVP:** These features enable the core loop: run extraction, measure F1, make change, re-measure. Everything else is optimization.

### Add After Validation (v1.x) - Make Self-Improvement Effective

Features to add once the basic loop works but results plateau.

- [ ] **Error categorization** - Add when improvements stall and you need to diagnose WHY
- [ ] **Feedback-driven refinement** - Add when manual prompt iteration feels random
- [ ] **Few-shot example selection** - Add when base prompts are decent but need polish
- [ ] **Leave-one-out cross-validation** - Add when you suspect overfitting (train score high, new docs fail)
- [ ] **Field-level diagnostics** - Add when aggregate F1 is acceptable but specific fields still fail

### Future Consideration (v2+) - After 0.90 F1 Achieved

Features to defer until the primary goal is met.

- [ ] **Visual grounding** - Useful for debugging but expensive to implement
- [ ] **Multi-restart optimization** - Useful when local optima become the bottleneck
- [ ] **Instruction optimization (MIPROv2-style)** - Powerful but complex; requires more eval data to avoid overfitting
- [ ] **Confidence scoring** - Useful for production but not for R&D metric optimization
- [ ] **Retry with self-correction** - Optimization of extraction quality, not self-improvement loop

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Rationale |
|---------|------------|---------------------|----------|-----------|
| Ground truth comparison | HIGH | LOW | P1 | Foundation of everything |
| Automated F1 metric | HIGH | LOW | P1 | Required for optimization |
| Iteration tracking | HIGH | LOW | P1 | Required for learning |
| Prompt versioning | HIGH | LOW | P1 | Required for reproducibility |
| Single improvement step | HIGH | MEDIUM | P1 | Core loop |
| Structured output schema | HIGH | LOW | P1 | Required for comparison |
| Error capture | HIGH | LOW | P1 | Required for debugging |
| Error categorization | HIGH | MEDIUM | P2 | Accelerates improvement |
| Feedback-driven refinement | HIGH | MEDIUM | P2 | Makes optimization smarter |
| Few-shot example selection | MEDIUM | MEDIUM | P2 | Improves extraction quality |
| Leave-one-out CV | MEDIUM | LOW | P2 | Protects against overfitting |
| Field-level diagnostics | MEDIUM | LOW | P2 | Focuses improvement effort |
| Retry with self-correction | MEDIUM | MEDIUM | P3 | Extraction optimization |
| Confidence scoring | MEDIUM | MEDIUM | P3 | Production feature |
| Visual grounding | LOW | HIGH | P3 | Debugging aid |
| Multi-restart optimization | MEDIUM | MEDIUM | P3 | Local optima mitigation |
| Instruction optimization | HIGH | HIGH | P3 | Powerful but risky with small data |

**Priority key:**
- P1: Must have for launch - enables basic self-improvement loop
- P2: Should have - makes self-improvement actually effective
- P3: Nice to have - advanced optimization or production features

---

## Critical Constraints for Small Eval Sets (5 Cases)

With only 5 eval cases, several constraints apply:

### Overfitting Risk

**Problem:** Any optimization with 5 cases risks memorizing the cases rather than learning general patterns.

**Mitigations:**
1. **Leave-one-out cross-validation**: Always report held-out performance
2. **Conservative changes**: One modification per iteration; reject if held-out regresses
3. **Qualitative review**: Human reviews prompt changes for reasonableness
4. **Track variance**: Report score variance across cases, not just mean

### Statistical Significance

**Problem:** With 5 cases, differences in F1 may be noise.

**Mitigations:**
1. **Require large deltas**: Only accept changes with >5% improvement
2. **Multiple runs**: Run each config 2-3 times to measure variance
3. **Field-level analysis**: Look for consistent patterns, not aggregate wins

### Few-Shot Selection

**Problem:** Cannot bootstrap many few-shot examples from 5 cases.

**Mitigations:**
1. **Use 1-2 examples max**: More examples = more overfitting
2. **Manual curation**: Hand-select representative examples
3. **Diversity over volume**: Different doc types, not multiple similar docs

---

## Relevant Systems and Approaches

### DSPy Optimization Patterns (HIGH confidence - official docs)

DSPy provides optimizers relevant to this task:

| Optimizer | Use Case | Data Required | Our Applicability |
|-----------|----------|---------------|-------------------|
| BootstrapFewShot | Generate few-shot examples | 10+ examples | LOW - 5 cases is borderline |
| BootstrapFewShotWithRandomSearch | Search over generated examples | 50+ examples | NOT APPLICABLE |
| MIPROv2 | Joint instruction + example optimization | 200+ examples | NOT APPLICABLE for now |
| COPRO | Instruction optimization via contrast | 40+ trials | MAYBE later with more data |

**Recommendation:** Manual prompt iteration with simple hill-climbing. DSPy optimizers need more data than we have.

### PromptWizard Pattern (MEDIUM confidence - Microsoft Research)

Feedback-driven refinement:
1. Generate candidate prompt
2. Run evaluation
3. LLM critiques failures
4. LLM proposes refinement
5. Repeat

**Recommendation:** Adapt this pattern manually. Don't need full PromptWizard automation.

### Self-Correcting Extraction (MEDIUM confidence - recent research)

From arXiv (arxiv.org/html/2505.13504v1):
- Multi-agent framework with task-specific prompts
- RL policy guides meta-prompting agent
- Boosted exact match from 30% to 96.2%

**Recommendation:** Consider self-correction AFTER basic extraction works. Adds complexity.

---

## Sources

### HIGH Confidence (Official Documentation)
- [DSPy Optimizers](https://dspy.ai/learn/optimization/optimizers/) - DSPy official documentation
- [DSPy MIPROv2](https://dspy.ai/api/optimizers/MIPROv2/) - MIPROv2 API reference
- [DSPy BootstrapFewShot](https://dspy.ai/api/optimizers/BootstrapFewShot/) - BootstrapFewShot API reference

### MEDIUM Confidence (Verified Multiple Sources)
- [Microsoft PromptWizard](https://www.microsoft.com/en-us/research/blog/promptwizard-the-future-of-prompt-optimization-through-feedback-driven-self-evolving-prompts/) - Microsoft Research blog
- [LLM-as-a-judge Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) - Evidently AI
- [Langfuse Error Analysis](https://langfuse.com/blog/2025-08-29-error-analysis-to-evaluate-llm-applications) - Langfuse blog
- [IBM Iterative Prompting](https://www.ibm.com/think/topics/iterative-prompting) - IBM Think
- [Agentic Document Extraction](https://landing.ai/agentic-document-extraction) - LandingAI

### LOW Confidence (Single Source, Needs Validation)
- [Overfitting in Prompt Engineering](https://medium.com/@arbaazkan96/challenges-in-prompt-engineering-overfitting-1ca1179aafff) - Medium article
- [FIPO: Feedback-Integrated Prompt Optimiser](https://www.nature.com/articles/s41598-025-27495-8) - Nature Scientific Reports
- [Self-Corrective Extraction with RL](https://arxiv.org/html/2505.13504v1) - arXiv preprint

---

*Feature research for: Self-improving agentic extraction system*
*Researched: 2026-02-03*
