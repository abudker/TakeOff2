# Pitfalls Research: Self-Improving Agentic Extraction Systems

**Domain:** Self-improving LLM agent for California Title 24 building plan extraction
**Researched:** 2026-02-03
**Confidence:** MEDIUM-HIGH (verified against multiple authoritative sources)

## Critical Pitfalls

### Pitfall 1: Prompt Optimization Overfitting

**What goes wrong:**
Optimized prompts achieve 5-20% higher training accuracy than test accuracy. The system performs well on examples used for optimization but fails to generalize to new documents. Your previous 0.43 F1 plateau may reflect this: prompts over-optimized to your training set.

**Why it happens:**
- BootstrapFewShot and similar optimizers find K examples that work together but may not represent the full distribution
- Self-improvement loops reinforce patterns that match training data
- DSPy's default approach deliberately skips validation sets, relying on consistent overfitting across candidates
- Longer, more specific prompts overfit more than shorter ones

**How to avoid:**
1. Use BootstrapFewShotWithRandomSearch or MIPROv2 instead of basic BootstrapFewShot - they search for optimal K from a larger candidate pool
2. Maintain strict train/validation/test splits with stratified sampling by document type
3. Apply early stopping - monitor when validation accuracy plateaus or declines
4. Use Context-Augmented Learning (template and content augmentation) for OOD robustness
5. Track train vs. validation gap explicitly in your optimization loop

**Warning signs:**
- Training accuracy >10% higher than validation
- Performance degrades on new document formats
- Prompts become increasingly specific/long without test improvement
- System works great on familiar documents but fails on edge cases

**Phase to address:**
Phase 1 (Evaluation Infrastructure) - Build the train/val/test split infrastructure before any optimization begins

---

### Pitfall 2: Multi-Agent Coordination Failures

**What goes wrong:**
Research shows multi-agent LLM systems fail 41-86.7% of the time in production. Your previous "multi-agent orchestration never fully worked" matches the literature: 79% of failures stem from specification problems (41.77%) and inter-agent misalignment (36.94%), not infrastructure issues.

**Why it happens:**
- Agents "talk past each other" - optimizing for subgoals that don't align with the overall mission
- Agent A shortens output to save tokens while Agent B expects exhaustive detail
- Unstructured text communication creates ambiguity
- No explicit verification that agents share the same understanding
- Using multi-agent when single-agent would outperform (architectural over-engineering)

**How to avoid:**
1. **Treat specifications like API contracts** - Use JSON schemas for inter-agent communication, not prose
2. Start with single-agent architecture and add agents only when proven necessary
3. Implement explicit role-aware message schemas with declared intent, inputs, and expected outputs
4. Add formal speech acts ("propose", "critique", "refine") as machine-readable hooks
5. Use explicit verifier agents (MetaGPT/ChatDev patterns show fewer failures)
6. Implement structured handoff protocols, not natural language descriptions

**Warning signs:**
- Agents repeat each other's work
- Output quality varies wildly between runs
- "Works sometimes" behavior patterns
- Agents make contradictory decisions
- Conversation traces show agents ignoring each other's output

**Phase to address:**
Phase 2 (Architecture) - Design with single-agent first; if multi-agent, define contracts upfront

---

### Pitfall 3: PDF Processing Scale Limits Causing Structured Output Failures

**What goes wrong:**
Large PDFs converted to images consume massive context (images are converted to latent tokens). When combined with structured output requirements, the model either truncates (stop_reason: "max_tokens") returning invalid JSON, or refuses entirely (stop_reason: "refusal"). Your "PDF size limits caused structured output failures" is a known pattern.

**Why it happens:**
- Claude's image tokens count against the 200K context limit
- Structured outputs require the model to generate the COMPLETE schema-valid response
- Large/complex schemas are harder to satisfy within token limits
- No graceful degradation - partial JSON is invalid JSON
- Bedrock limits: 20 images per request vs. 100 on direct API

**How to avoid:**
1. Chunk documents aggressively - Oracle experiments show perfect chunking achieves 0.94 F1
2. Use smaller schemas per extraction call; aggregate results afterward
3. Make schema fields optional where possible (required fields are harder to satisfy)
4. Set generous max_tokens buffers (monitor stop_reason patterns)
5. Pre-filter pages to extract only relevant sections
6. Use rasterization at appropriate DPI - balance quality vs. token cost

**Warning signs:**
- stop_reason: "max_tokens" in API responses
- stop_reason: "refusal" when processing certain documents
- JSON parse errors on larger documents
- Inconsistent extraction success rates by document size

**Phase to address:**
Phase 1 (Document Processing Pipeline) - Build chunking and page selection before extraction

---

### Pitfall 4: Eval Metric Gaming (Goodhart's Law)

**What goes wrong:**
"When a measure becomes a target, it ceases to be a good measure." Your F1 optimization may have hit a local maximum where the system learned to game your specific eval set rather than genuinely improving extraction quality. Research shows benchmark-specific optimization leads to "lack of real-world generalization."

**Why it happens:**
- Optimizing directly on F1 without understanding error modes
- Single metric hides important tradeoffs (precision vs. recall vs. completeness)
- LLMs can learn patterns in test data distribution without true understanding
- No out-of-distribution testing to detect overfitting

**How to avoid:**
1. Use multi-faceted evaluation: F1 + precision + recall + field-level accuracy + structural correctness
2. Include adversarial/edge case test sets separate from main eval
3. Implement periodic blind testing with held-out documents
4. Track error category distribution, not just aggregate scores
5. Test on documents from different sources/formats/qualities
6. Human evaluation sample for sanity checking

**Warning signs:**
- Score improves but error patterns don't change
- High F1 but users report quality issues
- Performance drops on new document types
- System confidently extracts wrong values (hallucination)

**Phase to address:**
Phase 1 (Evaluation Infrastructure) - Design comprehensive eval suite before optimization begins

---

### Pitfall 5: Self-Improvement Reward Hacking and Semantic Drift

**What goes wrong:**
Self-improving systems can discover unexpected ways to maximize reward signals without achieving the intended goal. Additionally, iterative optimization may preserve syntactic clarity while subtly losing original intent (semantic drift).

**Why it happens:**
- Prompt optimization creates distinct attack surface - small corruptions propagate across optimization steps
- No prior work has systematically investigated safety implications of LLM-based prompt optimization
- Self-referential improvement can amplify subtle biases
- Reward signals may not capture full task semantics

**How to avoid:**
1. Implement human-in-the-loop checkpoints for prompt changes
2. Version control all prompts with semantic diff reviews
3. Maintain baseline "golden" prompts that must be explicitly deprecated
4. Test each optimization step against diverse validation sets
5. Use gradient regularization / meta-learning techniques to stabilize optimization
6. Log optimization trajectories for forensic analysis

**Warning signs:**
- Dramatic prompt changes between iterations
- Optimization finds "tricks" that don't generalize
- Prompts become nonsensical to humans but score well
- Performance suddenly degrades after many successful iterations

**Phase to address:**
Phase 3 (Self-Improvement Loop) - Build with explicit stability constraints

---

### Pitfall 6: VLM Hallucination on Technical Documents

**What goes wrong:**
Vision Language Models frequently hallucinate numbers, misread technical symbols, and fail on layout-heavy documents. For building plans with precise measurements and codes, even small errors cascade (e.g., extracting "12" instead of "121" for a code reference).

**Why it happens:**
- VLMs use language reasoning as primary driver; visual input is secondary
- Complex multi-panel figures and tables cause frequent errors
- OCR-like tasks on technical fonts/symbols are unreliable
- Models struggle with "layout reasoning" - understanding spatial relationships
- Low-resource scripts and technical notation underperform

**How to avoid:**
1. Post-processing validation against known value ranges
2. Use defined data types with automatic value cleaning (achieves highest F1 across all models)
3. Cross-reference extracted values against document structure (e.g., code must match Title 24 format)
4. Implement confidence scoring and flag low-confidence extractions for review
5. Consider hybrid approaches: traditional CV for symbols, LLM for semantic interpretation
6. Multiple extraction passes with consistency checking

**Warning signs:**
- Extracted values outside valid ranges
- Number transposition errors
- Missing extracted fields that are clearly present in document
- Inconsistent extraction of the same value in different contexts

**Phase to address:**
Phase 2 (Extraction Core) - Build validation into extraction, not as afterthought

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded document layouts | Quick MVP extraction | Fails on any layout variation | Never - use learned/flexible layouts |
| Single model for all extraction | Simpler architecture | Can't specialize for subtasks | Only in initial prototyping |
| String matching for validation | Fast implementation | Brittle, high false negative rate | Only for exact-match fields |
| Skipping train/val/test splits | Faster iteration | Cannot detect overfitting | Never |
| Ignoring stop_reason in API responses | Faster development | Silent failures on large documents | Never |
| Processing full documents | Simpler pipeline | Token costs explode, context pollution | Only for small documents |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude Structured Outputs | Using with Claude Opus 4.5 | Use Sonnet 4.5 or Opus 4.1 (Opus 4.5 not officially supported for structured outputs) |
| Claude Vision | Sending 20+ images per request | Stay under 20 images on Bedrock (100 on direct API) |
| DSPy BootstrapFewShot | Using boolean metrics with nuanced quality | Use metrics that capture quality gradients |
| PDF Processing | Treating all pages equally | Pre-filter to relevant pages only |
| JSON Outputs | Using with message prefilling | Prefilling is incompatible with JSON outputs |
| Citations | Using with structured outputs | Citations are incompatible with structured outputs |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Context window overflow | Truncated responses, invalid JSON | Chunk documents, use 1M context Sonnet 4/4.5 | >200K tokens (standard) or >1M (extended) |
| Grammar compilation latency | First requests slow, subsequent fast | Cache schemas, warm up on startup | Every schema change invalidates cache |
| Cascading agent errors | Single error propagates through pipeline | Checkpoint intermediate results, add recovery | Any complex multi-step workflow |
| Token cost explosion | Bills spike unexpectedly | Monitor per-document costs, set budgets | Large documents + retries |
| Uncoordinated agent resource contention | Rapid token burnthrough | Selective agent activation (MoE pattern) | Concurrent multi-agent execution |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Optimizing prompts on untrusted feedback | Poisoned prompts propagate across iterations | Validate feedback sources, sanitize inputs |
| No prompt versioning | Can't rollback from corrupted optimization | Git-based prompt management with approval gates |
| Trusting extracted values without validation | Injection via document content | Sanitize all extracted values, type checking |
| Logging sensitive document content | Data exposure | Redact PII before logging, structured logging |

## "Looks Done But Isn't" Checklist

- [ ] **Extraction accuracy:** F1 looks good on eval set - verify on held-out documents from different sources
- [ ] **Structured outputs:** JSON parses successfully - verify stop_reason is not "max_tokens"
- [ ] **Multi-agent orchestration:** Agents complete tasks - verify they're not duplicating work or ignoring each other
- [ ] **Self-improvement:** Metrics improve - verify train/val gap isn't growing
- [ ] **PDF processing:** Text extracts - verify layout/table structure is preserved
- [ ] **Error handling:** Retries work - verify exponential backoff and max attempts
- [ ] **Document coverage:** Most documents process - verify edge cases (rotated text, poor scan quality)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Overfitted prompts | LOW | Revert to last validated checkpoint, expand training data, re-optimize with early stopping |
| Multi-agent breakdown | MEDIUM | Simplify to single-agent, add explicit contracts, rebuild incrementally |
| Structured output failures | LOW | Reduce schema complexity, increase max_tokens, add chunking |
| Metric gaming | MEDIUM | Redesign eval suite, add diverse test sets, implement human eval |
| Semantic drift | HIGH | Rollback to golden prompts, audit optimization history, add stability constraints |
| VLM hallucinations | LOW | Add post-processing validation, implement confidence thresholds |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Prompt overfitting | Phase 1: Eval Infrastructure | Train/val/test gap monitoring |
| Multi-agent failures | Phase 2: Architecture | Inter-agent contract tests |
| PDF scale limits | Phase 1: Document Pipeline | Success rate by document size |
| Eval metric gaming | Phase 1: Eval Infrastructure | Multi-metric dashboards |
| Self-improvement instability | Phase 3: Self-Improvement | Optimization trajectory analysis |
| VLM hallucinations | Phase 2: Extraction Core | Value range validation coverage |

## Your Previous Issues - Specific Remediations

Based on your context (multi-agent issues, PDF size failures, 0.43 F1 plateau):

| Previous Issue | Root Cause (Likely) | Remediation |
|----------------|---------------------|-------------|
| Multi-agent orchestration never fully worked | Inter-agent misalignment (79% of MAS failures) | Start single-agent; if multi-agent needed, use JSON contracts |
| PDF size limits caused structured output failures | Context overflow + max_tokens truncation | Chunk aggressively, use smaller schemas, monitor stop_reason |
| Reached 0.43 F1 then stalled | Overfitting to eval set + single metric optimization | Expand eval with diverse documents, track multiple metrics |
| Rasterizing PDFs helped but wasn't enough | Image tokens still overflow context | Pre-filter pages, adaptive DPI, use extended context models |

## Sources

**HIGH Confidence (Official documentation):**
- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - JSON schema limitations, failure cases
- [DSPy Optimizers Documentation](https://dspy.ai/learn/optimization/optimizers/) - BootstrapFewShot behavior, overfitting mitigation
- [Anthropic Context Windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) - Token limits, vision processing

**MEDIUM Confidence (Peer-reviewed/credible sources):**
- [Why Do Multi-Agent LLM Systems Fail? (arXiv:2503.13657)](https://arxiv.org/html/2503.13657v1) - MAST taxonomy, failure percentages
- [How Overfitting Affects Prompt Optimization (HackerNoon)](https://hackernoon.com/how-overfitting-affects-prompt-optimization) - Train/test gap analysis
- [OpenAI: Measuring Goodhart's Law](https://openai.com/index/measuring-goodharts-law/) - Reward hacking patterns
- [Problem Solved? IE Design Space for Layout-Rich Documents (arXiv)](https://arxiv.org/html/2502.18179v1) - Pipeline optimization for document extraction

**LOW Confidence (Community sources, verify independently):**
- [Medium: LLM Failure Modes Field Guide](https://medium.com/@adnanmasood/a-field-guide-to-llm-failure-modes-5ffaeeb08e80)
- [Claude Task Master JSON Truncation Issue](https://github.com/eyaltoledano/claude-task-master/issues/913)

---
*Pitfalls research for: Self-improving agentic extraction (California Title 24)*
*Researched: 2026-02-03*
