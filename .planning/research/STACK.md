# Stack Research: Self-Improving Agentic Extraction System

**Domain:** Self-improving LLM agents for document extraction (California Title 24 building plans to EnergyPlus)
**Researched:** 2026-02-03
**Confidence:** MEDIUM-HIGH

## Executive Summary

Building a self-improving extraction system that can iterate from 0.43 F1 to 0.90 F1 requires four integrated capabilities: (1) prompt optimization that learns from failures, (2) eval-driven development with fast feedback loops, (3) vision-first PDF processing for building plans, and (4) lightweight agent orchestration. The stack below prioritizes proven tools with active maintenance over cutting-edge research frameworks.

**Key insight from research:** Your previous multi-agent orchestration approach likely failed because complex agent choreography adds failure modes without adding extraction capability. The winning pattern for extraction is: **simple agents + sophisticated prompt optimization + tight eval loops**.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **DSPy** | 3.1.2+ | Prompt optimization & self-improvement | Industry standard for automated prompt optimization. MIPROv2 optimizer raised ReAct agent performance from 24% to 51% by teaching specifics. GEPA (new in 2025) adds reflective evolution with text feedback. 160K monthly downloads, 16K GitHub stars. | HIGH |
| **Claude API** | claude-sonnet-4-5 | LLM backbone | Native structured outputs (Nov 2025), native PDF vision (Feb 2025). Constrained decoding guarantees schema compliance. Building plans need vision - Claude processes each PDF page as image + text. | HIGH |
| **Instructor** | 1.7+ | Structured output extraction | 3M+ monthly downloads. Pydantic-based validation with automatic retries. Lighter than LangChain for pure extraction. Works directly with Anthropic SDK. | HIGH |
| **Promptfoo** | 0.120+ | Eval-driven development | Red teaming + performance testing. YAML-based test configs. CI/CD integration via GitHub Actions. 100% local (prompt privacy). Best for systematic prompt iteration. | HIGH |

### PDF & Vision Processing

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Claude Native PDF** | API | Primary document processing | Vision-first processing critical for building plans (floor plans, diagrams, schedules). Claude sees pages as images + extracts text. 100 pages/request, 32MB limit. | HIGH |
| **PyMuPDF4LLM** | 0.0.17+ | Fallback text extraction | F1 score 0.973 on technical documents. 0.12s processing vs 11.3s for marker-pdf. Sweet spot of speed + quality when vision not needed. | MEDIUM |
| **Marker** | 0.3+ | High-fidelity conversion | Perfect structure preservation for complex layouts. Use only when PyMuPDF4LLM fails on specific document types. 11.3s processing time. | LOW (specialized) |

### Prompt Optimization & Self-Improvement

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **DSPy MIPROv2** | (in DSPy) | Primary optimizer | Bayesian optimization over prompt space. Generates instructions + few-shot examples simultaneously. Best for 50+ training examples. | HIGH |
| **DSPy GEPA** | (in DSPy) | Reflective optimization | New July 2025. Uses text feedback to guide optimization - perfect for extraction errors where you can describe WHY extraction failed. | MEDIUM |
| **DSPy BootstrapFewShot** | (in DSPy) | Quick iteration | Start here with ~10 labeled examples. Generates demonstrations using teacher module. Fast feedback for early development. | HIGH |
| **TextGrad** | 0.1+ | Alternative optimizer | Published in Nature. Backpropagates textual gradients. Consider if DSPy underperforms. Improved GPT-4o from 51% to 55% on QA tasks. | MEDIUM |

### Evaluation & Metrics

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Promptfoo** | 0.120+ | Primary eval framework | YAML config, CLI-first, CI/CD native. Red teaming for edge cases. Compare across model versions. | HIGH |
| **Braintrust AutoEvals** | latest | LLM-as-judge metrics | RAG metrics (precision, relevancy, faithfulness). Factuality scoring. Use for semantic correctness beyond exact match. | MEDIUM |
| **Pydantic Evals** | (in PydanticAI) | Span-based evaluation | Evaluates internal agent behavior via OpenTelemetry traces. Essential for debugging multi-step extraction. | MEDIUM |

### Agent Orchestration (Lightweight)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Claude Code Subagents** | native | Task isolation | Built-in to your runtime. Specialized agents in `.claude/agents/`. Own context, own tools. No external framework needed. | HIGH |
| **PydanticAI** | 0.1+ | Type-safe agent runtime | From Pydantic team. Model-agnostic, MCP support, built-in evals. Use if you outgrow Claude Code subagents. | MEDIUM |

---

## Installation

```bash
# Core - prompt optimization
pip install dspy>=3.1.2

# Core - structured extraction
pip install instructor>=1.7.0
pip install anthropic>=0.40.0

# Evaluation
npm install -g promptfoo  # or: pip install promptfoo
pip install braintrust autoevals

# PDF processing (fallback)
pip install pymupdf4llm>=0.0.17

# Optional - agent framework if needed
pip install pydantic-ai>=0.1.0

# Optional - alternative optimizer
pip install textgrad>=0.1.0
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| DSPy | TextGrad | If DSPy optimizers plateau. TextGrad's gradient-based approach may find different optima. |
| DSPy | Manual prompt engineering | If you have <10 examples. Manual iteration faster than optimizer setup. |
| Promptfoo | Braintrust | If you need full observability platform, not just testing. Braintrust adds production monitoring. |
| Claude Native PDF | Docling | If you need pre-processing pipeline for massive document volumes. Docling has LangChain/LlamaIndex integrations. |
| Claude Code Subagents | LangGraph | If you need complex stateful workflows with explicit control flow graphs. Adds significant complexity. |
| Instructor | Native Claude Structured Outputs | If you want zero dependencies. Native API works but Instructor adds retries + validation. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **LangChain for extraction** | Over-abstraction for simple extraction tasks. Adds layers without adding extraction capability. Debug difficulty. | Instructor + Anthropic SDK directly |
| **CrewAI / AutoGen** | Multi-agent choreography adds failure modes. Your 0.43 F1 likely suffered from orchestration complexity, not extraction capability. | Single-agent + DSPy optimization |
| **Custom prompt optimization** | DSPy has years of research. Rolling your own wastes time reinventing MIPROv2. | DSPy optimizers |
| **Text-only PDF extraction** | Building plans have diagrams, schedules, floor plans. Text extraction loses critical visual information. | Claude native PDF (vision) |
| **Fine-tuning (initially)** | Expensive, slow iteration. Prompt optimization achieves similar gains faster. Fine-tune only after prompts plateau. | DSPy BootstrapFinetune (later) |
| **OpenAI Evals** | Limited to OpenAI APIs. You're using Claude. | Promptfoo (model-agnostic) |

---

## Stack Patterns by Project Phase

### Phase 1: Baseline + Eval Infrastructure
```
Claude API (sonnet-4-5) + Instructor + Promptfoo
```
- Establish extraction pipeline with Pydantic models
- Build eval dataset from labeled building plans
- Measure baseline F1 on each extraction field

### Phase 2: Prompt Optimization Loop
```
+ DSPy (BootstrapFewShot -> MIPROv2)
```
- Wrap extraction in DSPy signatures
- Run BootstrapFewShot with 10-20 examples
- Graduate to MIPROv2 with 50+ examples
- Use GEPA when you have text feedback on errors

### Phase 3: Self-Improvement Automation
```
+ Promptfoo CI/CD + Braintrust metrics
```
- Automated eval on every prompt change
- LLM-as-judge for semantic correctness
- Regression detection before deployment

### Phase 4: Scale (if needed)
```
+ PydanticAI + Claude Code subagents
```
- Only if single-agent extraction hits ceiling
- Use subagents for: pre-processing, validation, error recovery
- Avoid complex multi-agent choreography

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| dspy 3.1.x | anthropic 0.40+ | DSPy has native Anthropic adapter |
| instructor 1.7+ | anthropic 0.40+ | Full structured output support |
| promptfoo 0.120+ | Any LLM | Model-agnostic by design |
| pydantic-ai 0.1+ | anthropic 0.40+ | Native Anthropic support |

---

## Claude-Specific Configuration

### Structured Outputs Setup
```python
import anthropic

client = anthropic.Anthropic()

# Enable structured outputs (beta)
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
    messages=[...],
    # Define your JSON schema
    output_format={
        "type": "json_schema",
        "json_schema": {
            "name": "extraction_result",
            "strict": True,
            "schema": {...}  # Your Pydantic model exported as JSON schema
        }
    }
)
```

### PDF Processing Setup
```python
# Option 1: URL-based (preferred for remote files)
message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {"type": "url", "url": "https://..."}
            },
            {"type": "text", "text": "Extract building specifications..."}
        ]
    }]
)

# Option 2: Base64 (for local files)
import base64
with open("building_plan.pdf", "rb") as f:
    pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                }
            },
            {"type": "text", "text": "Extract building specifications..."}
        ]
    }]
)
```

### DSPy with Claude Setup
```python
import dspy

# Configure DSPy to use Claude
lm = dspy.LM('anthropic/claude-sonnet-4-5', max_tokens=4096)
dspy.configure(lm=lm)

# Define extraction signature
class ExtractBuildingSpecs(dspy.Signature):
    """Extract building specifications from Title 24 documents."""
    document: str = dspy.InputField(desc="Building plan document text")
    specs: dict = dspy.OutputField(desc="Extracted specifications as structured data")

# Create module
extractor = dspy.ChainOfThought(ExtractBuildingSpecs)

# Optimize with MIPROv2
from dspy.teleprompt import MIPROv2
optimizer = MIPROv2(metric=f1_score_metric, num_candidates=10, num_trials=20)
optimized_extractor = optimizer.compile(extractor, trainset=training_examples)
```

---

## Self-Improvement Loop Architecture

The core loop for hitting 0.90 F1:

```
1. EXTRACT: Run extraction on building plan
   |
2. EVAL: Compare to ground truth, compute field-level F1
   |
3. ANALYZE: Identify failing fields + error patterns
   |
4. FEEDBACK: Generate text feedback on why extraction failed
   |
5. OPTIMIZE: Feed feedback to DSPy GEPA optimizer
   |
6. ITERATE: New prompts -> back to step 1
```

**Key insight:** The feedback loop quality matters more than optimizer sophistication. Invest in:
- High-quality labeled examples (start with 50-100 documents)
- Field-level error analysis (which fields fail most?)
- Text feedback generation (WHY did it fail, not just WHAT failed)

---

## Cost Estimation

For 100 building plans (50 pages average):

| Operation | Per-Document | 100 Documents |
|-----------|--------------|---------------|
| PDF processing (vision) | ~$0.38 | ~$38 |
| Extraction (structured output) | ~$0.15 | ~$15 |
| Optimization run (20 trials) | - | ~$50 |
| **Total per iteration** | - | **~$103** |

Budget ~$500-1000 for optimization to 0.90 F1 (5-10 optimization cycles).

---

## Sources

### HIGH Confidence (Official Documentation)
- [DSPy Official Site](https://dspy.ai/) - Optimizers, modules, version 3.1.2
- [DSPy GitHub](https://github.com/stanfordnlp/dspy) - Installation, releases
- [DSPy Optimizers Documentation](https://dspy.ai/learn/optimization/optimizers/) - MIPROv2, GEPA, BootstrapFewShot
- [Claude Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Constrained decoding, JSON schema
- [Claude PDF Support](https://platform.claude.com/docs/en/docs/build-with-claude/pdf-support) - Vision processing, limits, pricing
- [Instructor Library](https://python.useinstructor.com/) - Pydantic integration, provider support
- [Promptfoo GitHub](https://github.com/promptfoo/promptfoo) - Version 0.120+, features
- [PydanticAI Documentation](https://ai.pydantic.dev/) - Agent framework, evals

### MEDIUM Confidence (Verified Research)
- [TextGrad GitHub](https://github.com/zou-group/textgrad) - Published in Nature, textual gradients
- [Braintrust AutoEvals](https://github.com/braintrustdata/autoevals) - LLM-as-judge metrics
- [PyMuPDF Benchmarks](https://github.com/py-pdf/benchmarks) - F1 scores, performance comparison
- [Self-Improving Coding Agent (SICA)](https://arxiv.org/abs/2504.15228) - 17-53% improvements via self-edit
- [GEPA Paper](https://arxiv.org/abs/2507.19457) - Reflective prompt evolution

### LOW Confidence (Community/Single Source - Verify Before Using)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) - Subagent patterns
- [AWS Construction Document Analysis](https://aws.amazon.com/blogs/spatial/ai-powered-construction-document-analysis-by-leveraging-computer-vision-and-large-language-models/) - Building plan processing patterns
- [Self-Improving Agents Overview](https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/) - Architecture patterns

---

*Stack research for: Self-improving agentic extraction (Title 24 -> EnergyPlus)*
*Researched: 2026-02-03*
