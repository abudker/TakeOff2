# Project Research Summary

**Project:** Self-Improving Agentic Extraction System (California Title 24 to EnergyPlus)
**Domain:** Document extraction with self-improvement loop
**Researched:** 2026-02-03
**Confidence:** MEDIUM-HIGH

## Executive Summary

Building a self-improving extraction system that can iterate from 0.43 F1 to 0.90 F1 requires a fundamental architectural shift from complex multi-agent orchestration to a simpler, more robust approach. Research reveals that your previous multi-agent approach likely failed because 79% of multi-agent system failures stem from specification problems and inter-agent misalignment, not infrastructure issues. The winning pattern is: **simple agents + sophisticated prompt optimization + tight eval loops**.

The recommended architecture separates extraction execution (runtime) from improvement (background). The extraction system uses a supervisor-worker pattern with explicit state management (LangGraph style) and domain-specific extractors. The improvement system runs asynchronously, analyzing failures, proposing prompt refinements, and validating changes before deployment. This separation eliminates the complexity of real-time optimization while enabling systematic improvement.

Critical risks center on overfitting with only 5 eval cases, PDF context overflow causing structured output failures, and VLM hallucinations on technical documents. Mitigations include aggressive document chunking, leave-one-out cross-validation, and field-level validation. The path to 0.90 F1 is not more agents—it's better prompts, better evaluation infrastructure, and disciplined optimization.

## Key Findings

### Recommended Stack

The stack prioritizes proven tools with active maintenance over cutting-edge research frameworks. Core insight: DSPy's systematic prompt optimization approach scales to 50+ fields better than manual tuning, while Claude's native PDF vision processing is critical for building plans with diagrams, floor plans, and schedules.

**Core technologies:**
- **DSPy (3.1.2+)**: Prompt optimization and self-improvement — MIPROv2 optimizer for instruction + few-shot joint optimization; GEPA for text feedback-driven evolution. Industry standard with 160K monthly downloads.
- **Claude API (sonnet-4-5)**: LLM backbone — Native structured outputs with constrained decoding, native PDF vision processing for building plans. Processes pages as images + text.
- **Instructor (1.7+)**: Structured output extraction — Pydantic-based validation with automatic retries. Lighter than LangChain for pure extraction. 3M+ monthly downloads.
- **Promptfoo (0.120+)**: Eval-driven development — YAML-based test configs, CI/CD integration, 100% local operation. Red teaming and performance testing.
- **LangGraph**: Agent orchestration — Explicit state management with checkpointing. Critical for complex multi-step workflows with auditability and resumability.

**Critical version note:** Use Sonnet 4.5 for structured outputs (Opus 4.5 not officially supported).

### Expected Features

Research identifies three feature tiers based on user expectations and competitive analysis. With only 5 eval cases, the primary constraint is overfitting risk—features must balance optimization power against generalization.

**Must have (table stakes):**
- Ground truth comparison with field-level F1 scoring
- Automated evaluation metric computation
- Iteration tracking (timestamp, config hash, per-case scores)
- Prompt versioning (git-based or file versioning)
- Single improvement step (make change, measure, accept/reject)
- Structured output schema (JSON schema for EnergyPlus fields)
- Error capture and logging

**Should have (competitive):**
- Error categorization/analysis (why failures happen)
- Feedback-driven prompt refinement (LLM analyzes errors, proposes fixes)
- Few-shot example selection (bootstrap from successful extractions)
- Leave-one-out cross-validation (detect overfitting with small eval sets)
- Field-level diagnostic dashboard (per-field F1 trends)
- Retry with self-correction (validation check + re-extract with error context)

**Defer (v2+):**
- Visual grounding/source tracing (debugging aid, expensive to implement)
- Multi-restart optimization (useful when local optima become bottleneck)
- Instruction optimization (MIPROv2-style; powerful but needs more data)
- Confidence scoring (production feature, not R&D priority)
- Fine-tuning (expensive, slow iteration; prompt optimization achieves similar gains faster)

**Anti-features (deliberately NOT build for R&D):**
- Production-grade UI (massive distraction; CLI + logging sufficient)
- Aggressive caching (hides non-determinism, masks whether changes work)
- Complex multi-agent orchestration (hard to debug, attribution unclear)
- Automated hyperparameter sweeps (with 5 cases, any sweep overfits)

### Architecture Approach

The architecture uses a layered separation between extraction execution and improvement. Don't conflate extraction agents with the improvement loop—they are separate systems with different concerns.

**Major components:**

1. **Extraction System (Runtime)** — Supervisor-worker pattern with explicit state
   - Document Ingestion: PDF parsing, page segmentation, image extraction
   - Supervisor Agent: Route to extractors, manage state, handle failures
   - Domain Extractors: Project, Envelope, Windows, HVAC, Water Heater (specialized by domain)
   - Aggregator: Merge results, cross-validate, resolve conflicts

2. **Improvement System (Async/Background)** — Separate optimization loop
   - Eval Store: Persist extractions with ground truth for evaluation
   - Evaluator: Score against ground truth, compute field-level metrics
   - Analyzer: Identify failure patterns, categorize errors
   - Proposer: Generate prompt improvements (DSPy optimizers)
   - Validator: Test on holdout set before deployment
   - Prompt Registry: Version control, rollback, serve active prompts

3. **Data Flow Pattern** — Clear separation of concerns
   - Extraction flow: Document → Ingest → Supervisor → Domain Extractors → Aggregator → Result → Eval Store (logged async)
   - Improvement flow: Collect batch → Evaluate → Analyze → Propose → Validate → Apply (if validated)

**Key patterns:**
- Supervisor-worker with explicit state (LangGraph style) for deterministic, debuggable workflows
- DSPy-style optimization loop separating "what to optimize" from "how to optimize"
- Prompt registry with version control treating prompts as deployable artifacts
- Feedback signal architecture categorizing errors to inform improvements

### Critical Pitfalls

Research identifies six critical pitfalls, with specific remediations for your previous issues (multi-agent failures, PDF size limits, 0.43 F1 plateau).

1. **Prompt Optimization Overfitting** — Optimized prompts achieve 5-20% higher training accuracy than test accuracy. With 5 eval cases, this is the primary risk. **Avoid:** Use leave-one-out CV, track train/val gap explicitly, require >5% improvement for changes, use conservative one-modification-per-iteration approach. **Warning signs:** Training accuracy >10% higher than validation, performance degrades on new document formats.

2. **Multi-Agent Coordination Failures** — Research shows 41-86.7% failure rate in production. 79% of failures stem from specification problems and inter-agent misalignment. **Avoid:** Start single-agent, use JSON schemas for inter-agent communication (not prose), implement explicit verifier agents, use structured handoff protocols. **Your previous issue:** This is likely why your multi-agent orchestration never fully worked.

3. **PDF Processing Scale Limits Causing Structured Output Failures** — Large PDFs converted to images consume massive context. Combined with structured outputs, models either truncate (max_tokens) or refuse entirely. **Avoid:** Chunk documents aggressively, use smaller schemas per extraction call, set generous max_tokens buffers, pre-filter pages to relevant sections. **Your previous issue:** This caused your structured output failures.

4. **Eval Metric Gaming (Goodhart's Law)** — When F1 becomes the target, it ceases to be a good measure. System learns to game eval set rather than improve extraction quality. **Avoid:** Multi-faceted evaluation (F1 + precision + recall + field-level accuracy), adversarial test sets, periodic blind testing, track error category distribution. **Your previous issue:** 0.43 F1 plateau likely reflects overfitting to eval set.

5. **Self-Improvement Reward Hacking and Semantic Drift** — Self-improving systems discover unexpected ways to maximize reward without achieving intended goal. Iterative optimization may lose original intent. **Avoid:** Human-in-the-loop checkpoints for prompt changes, version control with semantic diff reviews, maintain baseline "golden" prompts, test each step against diverse validation sets.

6. **VLM Hallucination on Technical Documents** — Vision models hallucinate numbers, misread technical symbols, fail on layout-heavy documents. Small errors cascade (e.g., "12" instead of "121"). **Avoid:** Post-processing validation against known value ranges, use defined data types with automatic value cleaning, cross-reference against document structure, confidence scoring with review flags.

## Implications for Roadmap

Based on research, suggested phase structure follows dependency order and risk mitigation strategy:

### Phase 1: Foundation (Evaluation Infrastructure)
**Rationale:** Cannot improve what you cannot measure. Build eval infrastructure before any extraction to avoid overfitting and metric gaming pitfalls from the start.
**Delivers:** Ground truth dataset with 5+ labeled building plans, automated F1 computation with field-level breakdown, train/val/test split infrastructure, baseline metrics
**Addresses:** Ground truth comparison, automated evaluation metric, iteration tracking, prompt versioning (all from FEATURES.md table stakes)
**Avoids:** Pitfall #1 (overfitting) and Pitfall #4 (metric gaming) by building proper evaluation before optimization begins
**Research flag:** SKIP — Standard eval patterns well-documented

### Phase 2: Document Processing Pipeline
**Rationale:** Extraction quality depends on document quality. Chunking and page selection prevent PDF context overflow and structured output failures.
**Delivers:** PDF ingestion with page segmentation, intelligent chunking strategy, page relevance filtering, rasterization at appropriate DPI
**Uses:** Claude Native PDF (vision-first processing), PyMuPDF4LLM as fallback (0.973 F1 on technical docs)
**Addresses:** Document ingestion component from architecture
**Avoids:** Pitfall #3 (PDF scale limits) by building chunking infrastructure early
**Research flag:** NEEDS RESEARCH — Optimal chunking strategy for Title 24 plans (50-page documents with cross-references)

### Phase 3: Single-Domain Extraction (Project Metadata)
**Rationale:** Start with simplest domain to validate extraction pattern before scaling horizontally. Avoid multi-agent complexity until single-agent proves insufficient.
**Delivers:** Project metadata extractor (project_id, address, permit_no), structured output schema with validation, baseline F1 on simplest domain
**Uses:** Claude Sonnet 4.5 with structured outputs, Instructor for Pydantic validation
**Addresses:** Single domain extractor from architecture, structured output schema from features
**Avoids:** Pitfall #2 (multi-agent failures) by starting single-agent; Pitfall #6 (VLM hallucination) with field-level validation
**Research flag:** SKIP — Standard extraction pattern with established tools

### Phase 4: Supervisor + Multi-Domain Extraction
**Rationale:** Once single-domain works, expand horizontally with explicit state management. Supervisor coordinates without complex choreography.
**Delivers:** Supervisor agent with state management, domain extractors (Envelope, Windows, HVAC, Water Heater), aggregator with cross-validation, conflict resolution
**Uses:** LangGraph for explicit state and checkpointing
**Implements:** Full extraction system architecture (supervisor-worker pattern)
**Addresses:** Domain extractors, aggregator components from architecture
**Avoids:** Pitfall #2 (coordination failures) with JSON schemas for inter-agent communication, explicit state management
**Research flag:** NEEDS RESEARCH — LangGraph implementation patterns for extraction workflows, optimal state structure

### Phase 5: Prompt Optimization Loop
**Rationale:** Only optimize after extraction baseline established. Separate improvement system prevents runtime complexity.
**Delivers:** DSPy integration with extraction modules, BootstrapFewShot for initial optimization (10-20 examples), MIPROv2 for deeper optimization (50+ examples), prompt registry with version control
**Uses:** DSPy (BootstrapFewShot → MIPROv2 → GEPA), Promptfoo for systematic testing
**Implements:** Full improvement system architecture (analyze → propose → validate → apply)
**Addresses:** Few-shot example selection, instruction optimization, feedback-driven refinement from features
**Avoids:** Pitfall #1 (overfitting) with leave-one-out CV; Pitfall #5 (reward hacking) with human checkpoints
**Research flag:** NEEDS RESEARCH — DSPy optimizer selection for small datasets (5 cases), optimal few-shot example count

### Phase 6: Self-Improvement Automation
**Rationale:** Final automation of improvement loop after manual optimization proves effective.
**Delivers:** Automated error analysis and categorization, automated proposal generation, validation pipeline with auto-apply on success, monitoring dashboard for field-level diagnostics
**Implements:** Complete improvement system with minimal human intervention
**Addresses:** Error categorization, field-level diagnostics from features (competitive tier)
**Avoids:** Pitfall #5 (semantic drift) with baseline prompt preservation, rollback automation
**Research flag:** SKIP — Standard automation patterns with established frameworks

### Phase Ordering Rationale

- **Evaluation first (Phase 1):** All subsequent phases depend on measurement capability. Building this first prevents overfitting and metric gaming.
- **Document processing second (Phase 2):** Extraction quality ceiling determined by document quality. Chunking prevents context overflow failures.
- **Single-agent before multi-agent (Phase 3 → Phase 4):** Validates extraction pattern with minimal complexity before scaling. Avoids 79% failure rate from premature multi-agent orchestration.
- **Baseline extraction before optimization (Phase 4 → Phase 5):** Need something to optimize before optimizing. Separates concerns clearly.
- **Manual optimization before automation (Phase 5 → Phase 6):** Proves optimization loop effective before investing in automation infrastructure.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (Document Processing):** Chunking strategy for Title 24 plans — Need to research optimal chunk size, page selection heuristics, cross-reference handling. Building plans have unique structure (schedules span pages, diagrams reference codes).
- **Phase 4 (Multi-Domain Extraction):** LangGraph implementation patterns — Need research on state structure for extraction workflows, optimal supervisor routing logic, checkpoint granularity.
- **Phase 5 (Prompt Optimization):** DSPy with small datasets — Need research on which optimizer works best with 5 cases, minimum example counts for BootstrapFewShot vs. MIPROv2, GEPA applicability.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Evaluation):** Standard eval infrastructure — Well-documented patterns for F1 computation, train/val/test splits, metric tracking.
- **Phase 3 (Single-Domain):** Standard extraction — Instructor + Claude structured outputs is proven pattern with extensive documentation.
- **Phase 6 (Automation):** Standard automation — Error categorization, proposal pipelines, auto-apply are well-established patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended technologies have official documentation, active maintenance, proven track record. DSPy (16K GitHub stars), Instructor (3M downloads), Claude API (official). |
| Features | MEDIUM-HIGH | Feature prioritization based on multiple credible sources (DSPy optimizers, PromptWizard pattern, self-correcting extraction research). Small eval set constraint well-understood from overfitting research. |
| Architecture | MEDIUM | Supervisor-worker pattern well-documented (LangGraph official docs), DSPy optimization loop proven. Some domain-specific adaptation needed for Title 24 building plans. |
| Pitfalls | HIGH | Multi-agent failures (peer-reviewed arXiv paper with 79% statistic), overfitting patterns (verified across multiple sources), PDF context limits (official Anthropic docs), VLM hallucinations (multiple research sources). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

Research was thorough but several areas need validation during implementation:

- **Optimal chunking strategy for Title 24 plans:** Research confirms chunking is critical (Oracle experiments show 0.94 F1 with perfect chunking), but optimal strategy for building plans with cross-page schedules and diagrams needs experimentation. Address in Phase 2 planning with research-phase.

- **DSPy optimizer selection with 5 eval cases:** DSPy documentation suggests 10+ examples for BootstrapFewShot, 200+ for MIPROv2. Need to validate which optimizer works with only 5 cases, or whether manual prompt iteration is more appropriate until dataset expands. Address in Phase 5 planning with research-phase.

- **Field-level validation rules for Title 24:** Research confirms validation prevents VLM hallucinations, but specific value ranges and formats for ~50 fields need domain expertise. Address during Phase 3-4 with SME consultation.

- **LangGraph state structure for extraction:** Research confirms explicit state management is critical, but optimal state structure (what to checkpoint, when to validate) needs design iteration. Address in Phase 4 planning with research-phase.

- **Prompt version explosion management:** Research confirms prompt versioning is essential, but at scale (50 extractors × versions) needs pruning strategy. Address in Phase 5-6 with lifecycle policies.

## Sources

### PRIMARY (HIGH confidence)
- [DSPy Official Site](https://dspy.ai/) — Optimizers, modules, version 3.1.2
- [DSPy GitHub](https://github.com/stanfordnlp/dspy) — Installation, releases, 16K stars
- [DSPy Optimizers Documentation](https://dspy.ai/learn/optimization/optimizers/) — MIPROv2, GEPA, BootstrapFewShot
- [Claude Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — Constrained decoding, JSON schema
- [Claude PDF Support](https://platform.claude.com/docs/en/docs/build-with-claude/pdf-support) — Vision processing, limits, pricing
- [Instructor Library](https://python.useinstructor.com/) — Pydantic integration, provider support
- [Promptfoo GitHub](https://github.com/promptfoo/promptfoo) — Version 0.120+, features
- [PydanticAI Documentation](https://ai.pydantic.dev/) — Agent framework, evals
- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/memory) — Memory, state management
- [Anthropic Context Windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) — Token limits

### SECONDARY (MEDIUM confidence)
- [Why Do Multi-Agent LLM Systems Fail? (arXiv:2503.13657)](https://arxiv.org/html/2503.13657v1) — MAST taxonomy, 79% failure from specification/alignment
- [How Overfitting Affects Prompt Optimization (HackerNoon)](https://hackernoon.com/how-overfitting-affects-prompt-optimization) — Train/test gap analysis
- [OpenAI: Measuring Goodhart's Law](https://openai.com/index/measuring-goodharts-law/) — Reward hacking patterns
- [Problem Solved? IE Design Space for Layout-Rich Documents (arXiv)](https://arxiv.org/html/2502.18179v1) — 0.94 F1 with perfect chunking
- [TextGrad GitHub](https://github.com/zou-group/textgrad) — Published in Nature, textual gradients
- [Braintrust AutoEvals](https://github.com/braintrustdata/autoevals) — LLM-as-judge metrics
- [PyMuPDF Benchmarks](https://github.com/py-pdf/benchmarks) — F1 scores, performance comparison
- [GEPA Paper](https://arxiv.org/abs/2507.19457) — Reflective prompt evolution
- [LangGraph vs AutoGen Architecture](https://www.zenml.io/blog/langgraph-vs-autogen) — Architecture comparison
- [Microsoft PromptWizard](https://www.microsoft.com/en-us/research/blog/promptwizard-the-future-of-prompt-optimization-through-feedback-driven-self-evolving-prompts/) — Feedback-driven refinement

### TERTIARY (LOW confidence, verify independently)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) — Subagent patterns
- [AWS Construction Document Analysis](https://aws.amazon.com/blogs/spatial/ai-powered-construction-document-analysis-by-leveraging-computer-vision-and-large-language-models/) — Building plan processing
- [Self-Improving Agents Overview](https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/) — Architecture patterns
- [Medium: LLM Failure Modes Field Guide](https://medium.com/@adnanmasood/a-field-guide-to-llm-failure-modes-5ffaeeb08e80)
- [Self-Corrective Extraction with RL (arXiv)](https://arxiv.org/html/2505.13504v1) — Multi-agent framework with RL

---
*Research completed: 2026-02-03*
*Ready for roadmap: yes*
