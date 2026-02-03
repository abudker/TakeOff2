# Architecture Research: Self-Improving Agentic Extraction Systems

**Domain:** Self-improving document extraction for California Title 24 building plans
**Researched:** 2026-02-03
**Confidence:** MEDIUM (established patterns exist; domain-specific application requires validation)

## Executive Summary

Self-improving agentic extraction systems follow a **layered architecture** with clear separation between extraction execution, evaluation, analysis, and improvement. The key insight from current research: don't conflate the extraction agents with the improvement loop. The improvement loop is a separate system that observes extraction performance and proposes changes.

Your previous approach (discovery agent -> parallel extractors -> merge/validate) failed because orchestration complexity exploded without clear state management. The recommended pattern is **supervisor-worker with explicit state** (LangGraph pattern), combined with a **DSPy-style optimization loop** for self-improvement.

---

## Recommended Architecture

### System Overview

```
+==============================================================================+
|                         EXTRACTION SYSTEM (Runtime)                          |
+==============================================================================+
|                                                                              |
|  +------------------+     +------------------------------------------+       |
|  |   Document       |     |            Supervisor Agent              |       |
|  |   Ingestion      |---->|  (orchestrates extraction, manages state)|       |
|  +------------------+     +------------------------------------------+       |
|                                    |                                         |
|            +-------------+---------+---------+-------------+                 |
|            |             |                   |             |                 |
|            v             v                   v             v                 |
|     +-----------+  +-----------+      +-----------+  +-----------+          |
|     | Project   |  | Envelope  |      | HVAC      |  | Water     |          |
|     | Extractor |  | Extractor | ...  | Extractor |  | Heater    |          |
|     +-----------+  +-----------+      +-----------+  +-----------+          |
|            |             |                   |             |                 |
|            +-------------+---------+---------+-------------+                 |
|                                    |                                         |
|                                    v                                         |
|                          +------------------+                                |
|                          |   Aggregator     |                                |
|                          | (merge, validate)|                                |
|                          +------------------+                                |
|                                    |                                         |
|                                    v                                         |
|                          +------------------+                                |
|                          | Extraction Result|                                |
|                          | + Confidence     |                                |
|                          +------------------+                                |
|                                    |                                         |
+==============================================================================+
                                     |
                                     | (logged to eval store)
                                     v
+==============================================================================+
|                      IMPROVEMENT SYSTEM (Async/Background)                   |
+==============================================================================+
|                                                                              |
|  +------------------+     +------------------+     +------------------+      |
|  |   Eval Store     |---->|   Evaluator      |---->|   Analyzer       |      |
|  | (extractions +   |     | (score against   |     | (identify        |      |
|  |  ground truth)   |     |  ground truth)   |     |  failure modes)  |      |
|  +------------------+     +------------------+     +------------------+      |
|                                                            |                 |
|                                                            v                 |
|                                                   +------------------+       |
|                                                   |   Proposer       |       |
|                                                   | (generate prompt |       |
|                                                   |  improvements)   |       |
|                                                   +------------------+       |
|                                                            |                 |
|                                                            v                 |
|                                                   +------------------+       |
|                                                   |   Validator      |       |
|                                                   | (test on holdout)|       |
|                                                   +------------------+       |
|                                                            |                 |
|                          +------------------+              |                 |
|                          |  Prompt Registry |<-------------+                 |
|                          |  (versions,      |  (if improves)                 |
|                          |   rollback)      |                                |
|                          +------------------+                                |
|                                                                              |
+==============================================================================+
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **Document Ingestion** | PDF parsing, page segmentation, image extraction | Supervisor |
| **Supervisor Agent** | Route to extractors, manage state, handle failures | All extractors, Aggregator |
| **Domain Extractors** | Extract specific field groups from documents | Supervisor (receive), Aggregator (send) |
| **Aggregator** | Merge results, cross-validate, resolve conflicts | Supervisor, Eval Store |
| **Eval Store** | Persist extractions with metadata for evaluation | Evaluator |
| **Evaluator** | Score extractions against ground truth | Analyzer |
| **Analyzer** | Identify patterns in failures, categorize errors | Proposer |
| **Proposer** | Generate improved prompts/configurations | Validator |
| **Validator** | Test proposals on holdout set | Prompt Registry |
| **Prompt Registry** | Version prompts, manage rollback, serve active prompts | All extractors |

---

## Data Flow

### Extraction Flow (Runtime)

```
Document (PDF)
    |
    v
[1] Ingest: Parse PDF -> pages[] + metadata
    |
    v
[2] Supervisor: Analyze document, plan extraction strategy
    |
    +---> [3a] Project Extractor: project_id, address, permit_no...
    |
    +---> [3b] Envelope Extractor: zones[], walls[], insulation...
    |
    +---> [3c] Window Extractor: window_specs[], SHGC, U-factor...
    |
    +---> [3d] HVAC Extractor: systems[], efficiency, tonnage...
    |
    +---> [3e] Water Heater Extractor: type, efficiency, fuel...
    |
    v
[4] Aggregator:
    - Merge partial results
    - Cross-validate (e.g., zone count matches window zones)
    - Flag conflicts with confidence scores
    |
    v
[5] Result: Structured extraction + confidence + audit trail
    |
    v
[6] Log to Eval Store (async)
```

### Improvement Flow (Background/Scheduled)

```
[1] COLLECT: Batch extractions with ground truth labels
    |
    v
[2] EVALUATE: Score each extraction
    - Field-level accuracy
    - Confidence calibration
    - Error categorization
    |
    v
[3] ANALYZE: Identify improvement opportunities
    - Which extractors are failing?
    - What types of errors? (hallucination, omission, wrong location)
    - Are failures correlated with document types?
    |
    v
[4] PROPOSE: Generate candidate improvements
    - New prompt variants
    - Few-shot example additions
    - Extraction strategy changes
    |
    v
[5] VALIDATE: Test on holdout set
    - Must improve target metric
    - Must not regress on other metrics
    |
    v
[6] APPLY (if validated):
    - Commit new prompt version to registry
    - Keep old version for rollback
    - Log change rationale
```

---

## Architectural Patterns

### Pattern 1: Supervisor-Worker with Explicit State (LangGraph Style)

**What:** A central supervisor agent manages workflow state and routes to specialized workers. State is a first-class citizen, persisted via checkpoints.

**When to use:** Complex multi-step workflows where you need auditability, resumability, and explicit control flow.

**Why for Title 24:** Building plans are complex documents requiring multiple extraction passes. You need to track what's been extracted, handle partial failures gracefully, and resume interrupted extractions.

**Trade-offs:**
- PRO: Deterministic, debuggable, resumable
- PRO: Clear ownership of state
- CON: More boilerplate than emergent conversation
- CON: Requires explicit routing logic

**Implementation approach:**
```python
# Conceptual structure (LangGraph-style)
class ExtractionState(TypedDict):
    document_id: str
    pages: List[Page]
    extractions: Dict[str, Any]  # field_group -> extracted data
    pending_extractors: List[str]
    completed_extractors: List[str]
    conflicts: List[Conflict]
    confidence_scores: Dict[str, float]

# Supervisor decides routing based on state
def supervisor(state: ExtractionState) -> str:
    if state["pending_extractors"]:
        return state["pending_extractors"][0]
    elif state["conflicts"]:
        return "conflict_resolver"
    else:
        return "aggregator"
```

### Pattern 2: DSPy-Style Optimization Loop

**What:** Separate the "what to optimize" (metrics) from "how to optimize" (optimizers). Define signatures (input/output contracts), write programs using modules, let optimizers tune prompts and demonstrations.

**When to use:** When you need systematic prompt improvement rather than ad-hoc tweaking.

**Why for Title 24:** ~50 fields means ~50 opportunities for prompts to go wrong. Manual tuning doesn't scale. DSPy's approach treats prompts as optimizable parameters.

**Trade-offs:**
- PRO: Systematic improvement with metrics
- PRO: Composable optimizers
- CON: Requires training data (30+ examples minimum, 300+ ideal)
- CON: Optimization runs can be expensive (many LLM calls)

**Implementation approach:**
```python
# Conceptual DSPy structure
class WindowExtraction(dspy.Signature):
    """Extract window specifications from Title 24 building plan pages."""
    pages: List[str] = dspy.InputField(desc="OCR text from relevant pages")
    schema_hint: str = dspy.InputField(desc="Expected fields and formats")

    windows: List[WindowSpec] = dspy.OutputField(desc="Extracted window data")
    confidence: float = dspy.OutputField(desc="Extraction confidence 0-1")

class WindowExtractor(dspy.Module):
    def __init__(self):
        self.extract = dspy.Predict(WindowExtraction)

    def forward(self, pages, schema_hint):
        return self.extract(pages=pages, schema_hint=schema_hint)

# Optimization loop
optimizer = dspy.MIPROv2(metric=extraction_accuracy_metric)
optimized_extractor = optimizer.compile(
    WindowExtractor(),
    trainset=window_training_examples,
    valset=window_validation_examples
)
```

### Pattern 3: Prompt Registry with Version Control

**What:** Treat prompts as deployable artifacts with version history, not as hardcoded strings. Enable hot-swapping and rollback without code deploys.

**When to use:** Production systems where prompts change frequently, where you need to rollback bad changes, or where non-engineers need to iterate on prompts.

**Why for Title 24:** Extraction quality will evolve as you encounter more document variations. You need to track what prompt version produced what results, and quickly rollback if a change causes regressions.

**Trade-offs:**
- PRO: Rapid iteration without code deploys
- PRO: Clear audit trail of changes
- PRO: Easy A/B testing
- CON: Additional infrastructure (registry service or file-based system)
- CON: Versioning complexity

**Implementation approach:**
```python
# Simple file-based registry structure
prompts/
  extractors/
    project/
      v1.0.0.yaml      # original
      v1.0.1.yaml      # fixed permit number format
      v1.1.0.yaml      # added few-shot examples
      active.yaml      # symlink to current version
    windows/
      v1.0.0.yaml
      active.yaml
  meta/
    changelog.md
    rollback_log.md

# Prompt file structure
# prompts/extractors/windows/v1.1.0.yaml
version: "1.1.0"
parent_version: "1.0.0"
created: "2026-02-03"
author: "improvement-loop"
reason: "Added 3 few-shot examples for complex window schedules"

system_prompt: |
  You are an expert at extracting window specifications from Title 24 plans...

few_shot_examples:
  - input: "..."
    output: "..."

metrics_at_release:
  accuracy: 0.87
  recall: 0.92
  precision: 0.83
```

### Pattern 4: Feedback Signal Architecture

**What:** Structure the path from evaluation results to actionable prompt changes. Don't just log errors; categorize them in ways that inform improvements.

**When to use:** When building the self-improvement loop.

**Implementation approach:**
```
Evaluation Output Structure:
{
  "extraction_id": "...",
  "extractor": "windows",
  "prompt_version": "v1.0.0",
  "field_results": {
    "window_count": {"predicted": 12, "actual": 14, "error_type": "omission"},
    "shgc_values": {"predicted": [...], "actual": [...], "error_type": "partial_match"}
  },
  "error_analysis": {
    "primary_error": "omission",
    "likely_cause": "window_schedule_on_separate_page",
    "document_feature": "multi_page_schedule"
  }
}

Analyzer -> Proposer Signal:
{
  "extractor": "windows",
  "failure_pattern": "omission_multi_page",
  "frequency": 0.23,  # 23% of failures
  "example_docs": ["doc_123", "doc_456"],
  "proposed_fix_type": "instruction_addition",
  "proposed_fix": "When extracting windows, check ALL pages marked 'FENESTRATION' or 'WINDOW SCHEDULE'..."
}
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Parallel Extraction Without State Coordination

**What people do:** Fire off multiple extractors in parallel, then try to merge results.

**Why it's wrong:** Without shared state, extractors can't coordinate on ambiguous cases. Merging becomes exponentially complex as you add extractors. Your previous architecture suffered from this.

**Do this instead:** Use a supervisor that maintains extraction state. Extractors read from and write to shared state. Supervisor handles conflicts before they accumulate.

### Anti-Pattern 2: Improvement Loop in Hot Path

**What people do:** Try to improve prompts during extraction (real-time optimization).

**Why it's wrong:** Optimization is expensive (many LLM calls). Introduces unpredictable latency. Makes debugging harder because prompts change mid-flight.

**Do this instead:** Separate extraction (fast, deterministic with fixed prompts) from improvement (background, batch-oriented). Extraction uses whatever prompts are active; improvement proposes changes that get validated before activation.

### Anti-Pattern 3: Single Monolithic Extraction Prompt

**What people do:** One mega-prompt that tries to extract all 50 fields at once.

**Why it's wrong:** Too many failure modes conflated. Hard to improve one area without regressing another. Context window gets consumed by irrelevant fields.

**Do this instead:** Decompose by semantic domain (project metadata, envelope, windows, HVAC, water heaters). Each extractor has focused prompts that can be independently optimized.

### Anti-Pattern 4: Unstructured Feedback Signals

**What people do:** Log extraction errors as freeform text, then manually review to find patterns.

**Why it's wrong:** Doesn't scale. Can't automate improvement. Loses structured information about error types.

**Do this instead:** Define an error taxonomy (omission, hallucination, format_error, wrong_location, confidence_miscalibration). Categorize every error. This enables automated analysis and targeted improvements.

---

## Build Order (Dependencies)

### Phase 1: Foundation (No AI yet)
Build order rationale: You need somewhere to store results and prompts before you can improve them.

1. **Document Ingestion Pipeline** - PDF parsing, page extraction, OCR integration
2. **Schema Definition** - Define all 50 fields with types, validation rules
3. **Prompt Registry** - File-based versioning for prompts (can be simple YAML initially)
4. **Eval Store Schema** - Database structure for extraction results + ground truth

### Phase 2: Basic Extraction
Build order rationale: Get extraction working before optimizing it.

1. **Single Domain Extractor** - Start with project metadata (simplest domain)
2. **Supervisor Agent** - Basic routing to single extractor
3. **Evaluation Harness** - Score extractions against labeled data
4. **Manual Labeling Tool** - Build ground truth dataset

### Phase 3: Multi-Domain Extraction
Build order rationale: Expand horizontally once one domain works.

1. **Additional Extractors** - Envelope, Windows, HVAC, Water Heaters
2. **Aggregator** - Merge results, cross-validate
3. **Conflict Resolution** - Handle disagreements between extractors
4. **Confidence Calibration** - Train confidence scores to be meaningful

### Phase 4: Improvement Loop
Build order rationale: Only automate improvement once you have enough data and stable extraction.

1. **Analyzer Component** - Categorize errors, identify patterns
2. **Proposer Component** - Generate prompt improvements (can use DSPy optimizers)
3. **Validator Component** - Test proposals on holdout set
4. **Auto-Apply Pipeline** - Promote validated improvements to registry

### Phase 5: Production Hardening
Build order rationale: Operational concerns for production deployment.

1. **Rollback Automation** - Detect regressions, auto-rollback
2. **A/B Testing Framework** - Safely test prompt variants
3. **Monitoring Dashboard** - Track extraction quality over time
4. **Alert System** - Notify on quality degradation

---

## Framework Recommendations

Based on current ecosystem research:

| Component | Recommended | Alternative | Rationale |
|-----------|-------------|-------------|-----------|
| **Orchestration** | LangGraph | CrewAI | LangGraph's explicit state management and checkpointing essential for complex extraction. [LangGraph 1.0](https://www.langchain.com/langgraph) released Jan 2026. |
| **Optimization** | DSPy | Manual prompt tuning | DSPy's systematic approach scales to 50+ fields. [MIPROv2](https://dspy.ai/learn/optimization/optimizers/) optimizer handles instruction + few-shot optimization. |
| **Prompt Versioning** | File-based YAML | PromptLayer, Braintrust | Start simple. Move to platform if team grows or you need collaboration features. |
| **Eval Framework** | Custom + DSPy metrics | LangSmith | Keep evals close to the code initially. DSPy integrates metrics directly into optimization. |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-100 docs/day** | Single-process, synchronous extraction. File-based prompt registry. SQLite eval store. |
| **100-1K docs/day** | Queue-based async extraction. Postgres eval store. Batch improvement runs nightly. |
| **1K+ docs/day** | Worker pool for extraction. Consider caching repeated document patterns. Continuous improvement loop. |

### What Breaks First

1. **LLM API costs** - At scale, extraction costs dominate. Mitigation: smaller models for confident cases, expensive models only for difficult extractions.
2. **Ground truth labeling** - Improvement loop needs labeled data. Mitigation: active learning to prioritize labeling effort on high-value examples.
3. **Prompt version explosion** - Too many versions becomes unmanageable. Mitigation: prune old versions, enforce promotion criteria.

---

## Sources

**Multi-Agent Orchestration (MEDIUM confidence - multiple sources agree):**
- [LangGraph vs AutoGen Architecture Comparison](https://www.zenml.io/blog/langgraph-vs-autogen)
- [Agent Orchestration Frameworks 2026](https://iterathon.tech/blog/ai-agent-orchestration-frameworks-2026)
- [Multi-Agent AI Systems Enterprise Guide](https://neomanex.com/posts/multi-agent-ai-systems-orchestration)

**DSPy Optimization (HIGH confidence - official documentation):**
- [DSPy Optimizers Official Docs](https://dspy.ai/learn/optimization/optimizers/)
- [DSPy Optimization Overview](https://dspy.ai/learn/optimization/overview/)

**LangGraph Memory/State (MEDIUM confidence - official docs + tutorials):**
- [LangGraph Memory Documentation](https://docs.langchain.com/oss/python/langgraph/memory)
- [LangGraph Agent Memory Architecture](https://dev.to/sreeni5018/the-architecture-of-agent-memory-how-langgraph-really-works-59ne)

**Prompt Versioning (MEDIUM confidence - multiple sources):**
- [Prompt Versioning Best Practices](https://latitude-blog.ghost.io/blog/prompt-versioning-best-practices/)
- [Prompt Rollback in Production](https://latitude-blog.ghost.io/blog/prompt-rollback-in-production-systems/)
- [Top 5 Prompt Versioning Tools 2026](https://www.getmaxim.ai/articles/top-5-prompt-versioning-tools-for-enterprise-ai-teams-in-2026/)

**Agentic Document Extraction (LOW confidence - emerging patterns):**
- [Agentic Document Extraction LLMMultiAgent](https://llmmultiagent.com/en/blogs/agentic-document-extraction)

---

*Architecture research for: Self-improving agentic extraction for Title 24 building plans*
*Researched: 2026-02-03*
