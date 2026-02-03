# Phase 3: Single-Domain Extraction - Research

**Researched:** 2026-02-03
**Domain:** Multi-agent extraction with Claude vision, document structure mapping, agentic orchestration
**Confidence:** MEDIUM

## Summary

This phase requires building a multi-agent extraction pipeline with three components: (1) discovery agent that maps PDF structure (schedules, CBECC pages, drawings), (2) project extractor that extracts metadata and envelope data, and (3) orchestrator that coordinates the workflow and merges results into BuildingSpec JSON.

The standard approach in 2026 for agentic document extraction combines Claude vision API for image-based extraction, LangGraph for multi-agent orchestration (fastest framework with lowest latency), and Pydantic with structured outputs for schema-guaranteed responses. The architecture should use orchestrator-worker pattern where the orchestrator delegates to specialized extractors and synthesizes results.

Key insight: Structured outputs (output_config.format) guarantee schema-valid JSON without retries, eliminating the primary source of extraction pipeline failures. Combined with strict tool use for inter-agent coordination, this creates production-grade reliability.

**Primary recommendation:** Use Claude Sonnet 4.5 with structured outputs + Pydantic schemas, LangGraph orchestrator-worker pattern, and vision API best practices (image-before-text, 1568px max dimension, PNG format already implemented).

## Standard Stack

The established libraries/tools for multi-agent extraction in 2026:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.45+ | Claude API client | Official SDK, supports structured outputs (GA as of 2026), Pydantic integration via transform_schema() |
| pydantic | 2.10+ | Schema definition & validation | De facto standard (466k+ repos), Rust core for performance, used by FastAPI/LangChain/OpenAI |
| langgraph | 0.2.75+ | Multi-agent orchestration | Fastest framework (lowest latency), graph-based with stateful workflows, official LangChain project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema | 4.26.0+ | Runtime validation | When you need to validate against original Pydantic constraints after SDK transforms them |
| pyyaml | 6.0.2+ | Config/mapping files | Already in use for field_mapping.yaml (Phase 1) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph | AutoGen | AutoGen has multi-agent support but LangGraph is faster (lowest latency 2026), better state management |
| LangGraph | CrewAI | CrewAI focuses on role-based agents, LangGraph provides more flexible graph-based control flow |
| Pydantic | dataclasses | Pydantic has validation, JSON schema generation, Claude SDK integration; dataclasses don't |
| Claude vision | GPT-4o vision | Claude excels at document understanding, preferred for technical drawings per 2026 benchmarks |

**Installation:**
```bash
pip install anthropic>=0.45 pydantic>=2.10 langgraph>=0.2.75
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── agents/
│   ├── __init__.py
│   ├── discovery.py       # Document structure mapping agent
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── project.py     # Project metadata & envelope extractor
│   │   └── base.py        # Shared extractor utilities
│   └── orchestrator.py    # Coordinates extraction flow
├── schemas/
│   ├── building_spec.py   # Pydantic models (already exists)
│   └── discovery.py       # Document map schema for discovery agent
└── .claude/
    ├── agents/
    │   ├── discovery.md
    │   ├── project-extractor.md
    │   └── orchestrator.md
    └── instructions/
        ├── discovery/
        │   └── instructions.md
        ├── project-extractor/
        │   └── instructions.md
        └── orchestrator/
            └── instructions.md
```

### Pattern 1: Orchestrator-Worker (LangGraph)
**What:** Central orchestrator breaks down tasks, delegates to workers, synthesizes outputs
**When to use:** Multi-step extraction with specialized agents (discovery → extraction → merge)
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/workflows-agents
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from operator import add

class ExtractionState(TypedDict):
    pdf_path: str
    document_map: dict  # From discovery agent
    project_data: dict  # From project extractor
    final_spec: dict    # Merged BuildingSpec

def discovery_node(state: ExtractionState) -> ExtractionState:
    """Discovery agent maps document structure."""
    # Call Claude vision to identify schedules, CBECC pages, drawings
    document_map = run_discovery_agent(state["pdf_path"])
    return {"document_map": document_map}

def project_extraction_node(state: ExtractionState) -> ExtractionState:
    """Extract project metadata and envelope data."""
    project_data = run_project_extractor(
        state["pdf_path"],
        state["document_map"]
    )
    return {"project_data": project_data}

def merge_node(state: ExtractionState) -> ExtractionState:
    """Orchestrator merges results into BuildingSpec."""
    final_spec = merge_to_building_spec(state["project_data"])
    return {"final_spec": final_spec}

# Build graph
workflow = StateGraph(ExtractionState)
workflow.add_node("discovery", discovery_node)
workflow.add_node("extract_project", project_extraction_node)
workflow.add_node("merge", merge_node)

workflow.set_entry_point("discovery")
workflow.add_edge("discovery", "extract_project")
workflow.add_edge("extract_project", "merge")
workflow.add_edge("merge", END)

app = workflow.compile()
```

### Pattern 2: Structured Output Extraction
**What:** Use Claude's structured outputs to guarantee schema-valid JSON without retries
**When to use:** Any extraction where downstream code expects specific schema (all extractors)
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from anthropic import Anthropic
from pydantic import BaseModel

class DocumentMap(BaseModel):
    """Discovery agent output schema."""
    schedules_pages: list[int]
    cbecc_pages: list[int]
    drawing_pages: list[int]

client = Anthropic()

# Using .parse() for automatic Pydantic integration
response = client.messages.parse(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "file", "file_id": file_id}},
            {"type": "text", "text": "Map document structure..."}
        ]
    }],
    output_format=DocumentMap,  # Pydantic model directly
)

# Response is guaranteed valid DocumentMap
document_map = response.parsed_output
assert isinstance(document_map, DocumentMap)
```

### Pattern 3: Vision API Multi-Page Handling
**What:** Process multiple PDF pages efficiently with Claude vision
**When to use:** Discovery agent scanning full PDF, extractors analyzing specific pages
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/vision
import anthropic

client = anthropic.Anthropic()

# Upload all pages as files (reusable, avoids base64 overhead)
file_ids = []
for page_path in page_images:
    with open(page_path, "rb") as f:
        file_upload = client.beta.files.upload(
            file=(page_path.name, f, "image/png")
        )
        file_ids.append(file_upload.id)

# Send up to 100 images in one request (API limit)
content = []
for i, file_id in enumerate(file_ids):
    content.extend([
        {"type": "text", "text": f"Page {i+1}:"},
        {"type": "image", "source": {"type": "file", "file_id": file_id}}
    ])
content.append({"type": "text", "text": "Identify all pages with schedules..."})

response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["files-api-2025-04-14"],
    messages=[{"role": "user", "content": content}]
)
```

### Pattern 4: Error Handling with Retries
**What:** Exponential backoff for transient API failures, circuit breaker for systemic issues
**When to use:** Production extraction pipeline (Phase 3 onward)
**Example:**
```python
# Source: https://sparkco.ai/blog/mastering-retry-logic-agents-a-deep-dive-into-2025-best-practices
import time
import random
from anthropic import Anthropic, APIError

def exponential_backoff_with_jitter(attempt: int, base_delay: float = 1.0) -> float:
    """Calculate delay with exponential backoff and jitter."""
    delay = base_delay * (2 ** attempt)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return min(delay + jitter, 60.0)  # Cap at 60 seconds

def call_with_retry(func, max_attempts: int = 3):
    """Retry function with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return func()
        except APIError as e:
            if e.status_code in [429, 500, 502, 503, 504]:  # Retryable errors
                if attempt < max_attempts - 1:
                    delay = exponential_backoff_with_jitter(attempt)
                    time.sleep(delay)
                    continue
            raise  # Non-retryable or max attempts reached
```

### Anti-Patterns to Avoid
- **Prompt-based JSON without structured outputs:** Claude can generate malformed JSON; always use `output_config.format` for guaranteed validity
- **Base64 encoding for reused images:** Use Files API to upload once, reference by file_id multiple times (reduces latency, costs)
- **Sequential agent calls without LangGraph:** Hand-rolling orchestration loses state management, debugging, and retry capabilities
- **Validating extracted JSON manually:** Pydantic + structured outputs handles this; manual validation is redundant and error-prone
- **Large images without preprocessing:** Phase 2 already handles this (1568px max), but don't skip it for new pipelines

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-agent orchestration | Custom task queue + state dict | LangGraph StateGraph | State management, debugging, cyclical workflows, persistence built-in; fastest framework 2026 |
| JSON schema validation | try/except + manual checks | Pydantic + structured outputs | Automatic validation, type safety, constraint checking; SDK handles unsupported features |
| Retry logic for API calls | Custom retry loop | exponential_backoff_with_jitter + circuit breaker | Prevents thundering herd, handles systemic failures, production-tested patterns |
| Image preprocessing | Custom resize logic | Already done in Phase 2 | PyMuPDF rasterization to 1568px PNG is optimal for Claude vision |
| Document structure detection | Regex + layout heuristics | Claude vision multi-page scan | Vision models understand document semantics (schedules vs drawings vs CBECC tables) better than heuristics |

**Key insight:** 2026 agent frameworks have matured to production-grade. Custom orchestration was necessary in 2024, but LangGraph now provides everything needed (state, retries, debugging) with better performance than hand-rolled solutions.

## Common Pitfalls

### Pitfall 1: Ignoring Structured Output Grammar Caching
**What goes wrong:** First request to new schema has high latency; developers assume all requests will be slow
**Why it happens:** Structured outputs compile grammar artifacts on first use, then cache for 24 hours
**How to avoid:**
- Keep schemas stable during iteration (don't change structure between runs)
- Only `name` and `description` changes preserve cache; changing properties invalidates it
- Pre-warm cache with test request if latency matters for first real request
**Warning signs:** First extraction takes 5+ seconds, subsequent ones take 2 seconds

### Pitfall 2: Missing Image-Before-Text Ordering
**What goes wrong:** Degraded extraction quality, Claude misses details in images
**Why it happens:** Claude performs best when images come before text in content blocks
**How to avoid:** Always structure content as `[images...] [text prompt]`, not interleaved
**Warning signs:** Claude extracts less data when same prompt works better with image-first ordering

### Pitfall 3: Not Using Files API for Multi-Page PDFs
**What goes wrong:** High latency, base64 encoding overhead, inflated request size
**Why it happens:** Base64 encoding adds ~33% size overhead and prevents caching
**How to avoid:**
- Upload each page once via Files API (beta.files.upload)
- Reference by file_id in multiple requests
- Files are reusable for 24 hours
**Warning signs:** Requests timing out, hitting 32MB limit with fewer images than expected

### Pitfall 4: Assuming Structured Outputs Handle All Constraints
**What goes wrong:** Pydantic model has `minimum=100` but Claude returns `50`
**Why it happens:** Structured outputs don't support numeric/string constraints; SDK transforms them away
**How to avoid:**
- SDK adds constraints to descriptions ("Must be at least 100")
- Use `.parse()` method which validates response against original Pydantic constraints
- Don't rely on structured outputs for business logic validation
**Warning signs:** Pydantic validation errors after extraction even with structured outputs

### Pitfall 5: Over-Chunking Document Processing
**What goes wrong:** Lost context between pages, multiple API calls increase cost
**Why it happens:** Developers fear hitting token limits, chunk unnecessarily
**How to avoid:**
- Claude supports up to 100 images per request (API limit)
- Vision tokens: ~1600 per 1568px image (~$4.80/1K images Sonnet 4.5)
- For Title 24 PDFs (10-30 pages), send all pages in one request for discovery
- Only chunk if document exceeds 100 pages
**Warning signs:** Discovery agent making 10 separate calls for 10-page PDF

### Pitfall 6: Not Setting additionalProperties: false
**What goes wrong:** Schema allows extra fields, Claude adds unexpected properties
**Why it happens:** JSON Schema defaults to allowing additional properties
**How to avoid:** Always set `"additionalProperties": false` in schemas (SDK does this automatically for Pydantic)
**Warning signs:** Extracted JSON has fields not in Pydantic model

## Code Examples

Verified patterns from official sources:

### Discovery Agent with Structured Output
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from anthropic import Anthropic
from pydantic import BaseModel, Field
from typing import List

class PageInfo(BaseModel):
    """Single page classification."""
    page_number: int
    page_type: str = Field(description="schedule|cbecc|drawing|other")
    confidence: str = Field(description="high|medium|low")

class DocumentMap(BaseModel):
    """Complete document structure map."""
    total_pages: int
    pages: List[PageInfo]

    @property
    def schedule_pages(self) -> List[int]:
        return [p.page_number for p in self.pages if p.page_type == "schedule"]

    @property
    def cbecc_pages(self) -> List[int]:
        return [p.page_number for p in self.pages if p.page_type == "cbecc"]

    @property
    def drawing_pages(self) -> List[int]:
        return [p.page_number for p in self.pages if p.page_type == "drawing"]

def run_discovery_agent(pdf_path: str, page_images: List[str]) -> DocumentMap:
    """
    Discovery agent: maps document structure.

    Args:
        pdf_path: Path to original PDF
        page_images: List of PNG page paths (from Phase 2 preprocessing)

    Returns:
        DocumentMap with page classifications
    """
    client = Anthropic()

    # Upload all pages
    file_ids = []
    for page_path in page_images:
        with open(page_path, "rb") as f:
            file_upload = client.beta.files.upload(
                file=(page_path, f, "image/png")
            )
            file_ids.append(file_upload.id)

    # Build content with image-before-text pattern
    content = []
    for i, file_id in enumerate(file_ids):
        content.extend([
            {"type": "text", "text": f"Page {i+1}:"},
            {"type": "image", "source": {"type": "file", "file_id": file_id}}
        ])

    content.append({
        "type": "text",
        "text": """Analyze each page and classify as:
- schedule: Equipment schedules, door/window schedules, finish schedules
- cbecc: CBECC compliance forms, energy calculations, CF1R/CF2R pages
- drawing: Floor plans, elevations, sections, details
- other: Cover pages, notes, specifications

Provide page_type and confidence for each page."""
    })

    # Use structured outputs for guaranteed schema
    response = client.beta.messages.parse(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=["files-api-2025-04-14"],
        messages=[{"role": "user", "content": content}],
        output_format=DocumentMap,
    )

    return response.parsed_output
```

### Project Extractor with Vision + Structured Output
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from schemas.building_spec import ProjectInfo, EnvelopeInfo
from pydantic import BaseModel

class ProjectExtraction(BaseModel):
    """Combined project + envelope extraction."""
    project: ProjectInfo
    envelope: EnvelopeInfo

def run_project_extractor(
    page_images: List[str],
    document_map: DocumentMap
) -> ProjectExtraction:
    """
    Extract project metadata and envelope data.

    Args:
        page_images: All page images (indexed by page_number - 1)
        document_map: Document structure from discovery agent

    Returns:
        ProjectExtraction with project + envelope data
    """
    client = Anthropic()

    # Focus on schedule and CBECC pages for project data
    relevant_pages = (
        document_map.schedule_pages +
        document_map.cbecc_pages
    )

    # Upload relevant pages
    content = []
    for page_num in relevant_pages[:20]:  # Limit to first 20 relevant
        page_path = page_images[page_num - 1]
        with open(page_path, "rb") as f:
            file_upload = client.beta.files.upload(
                file=(page_path, f, "image/png")
            )
            content.extend([
                {"type": "text", "text": f"Page {page_num}:"},
                {"type": "image", "source": {"type": "file", "file_id": file_upload.id}}
            ])

    content.append({
        "type": "text",
        "text": """Extract project metadata and envelope data:

PROJECT INFO:
- run_title: Project name/address
- address, city: From cover page or title block
- climate_zone: California climate zone (1-16)
- fuel_type: All Electric | Natural Gas | Mixed
- house_type: Single Family | Multi Family
- dwelling_units, stories, bedrooms: From schedules

ENVELOPE INFO:
- conditioned_floor_area: Total CFA in sq ft
- window_area: Total fenestration area in sq ft
- window_to_floor_ratio: WWR (calculate from above)
- exterior_wall_area: Total exterior wall area in sq ft
- fenestration_u_factor: Area-weighted U-factor if available

Look in:
- CBECC forms for climate zone, fuel type, CFA
- Window schedules for fenestration data
- Title blocks for project info"""
    })

    response = client.beta.messages.parse(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=["files-api-2025-04-14"],
        messages=[{"role": "user", "content": content}],
        output_format=ProjectExtraction,
    )

    return response.parsed_output
```

### Orchestrator Pattern
```python
# Source: https://docs.langchain.com/oss/python/langgraph/workflows-agents
from langgraph.graph import StateGraph, END
from typing import TypedDict
from pathlib import Path

class ExtractionState(TypedDict):
    """Shared state across extraction workflow."""
    eval_name: str
    pdf_path: str
    page_images: List[str]
    document_map: DocumentMap | None
    project_extraction: ProjectExtraction | None
    building_spec: dict | None
    error: str | None

def discovery_node(state: ExtractionState) -> dict:
    """Discovery agent node."""
    try:
        document_map = run_discovery_agent(
            state["pdf_path"],
            state["page_images"]
        )
        return {"document_map": document_map}
    except Exception as e:
        return {"error": f"Discovery failed: {str(e)}"}

def project_extraction_node(state: ExtractionState) -> dict:
    """Project extractor node."""
    if state.get("error"):
        return {}  # Skip if prior error

    try:
        project_extraction = run_project_extractor(
            state["page_images"],
            state["document_map"]
        )
        return {"project_extraction": project_extraction}
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}

def merge_node(state: ExtractionState) -> dict:
    """Merge results into BuildingSpec."""
    if state.get("error"):
        return {}

    # Create BuildingSpec from extraction
    from schemas.building_spec import BuildingSpec

    building_spec = BuildingSpec(
        project=state["project_extraction"].project,
        envelope=state["project_extraction"].envelope,
        zones=[],  # Phase 4
        walls=[],  # Phase 4
        windows=[],  # Phase 4
        hvac_systems=[],  # Phase 4
        water_heaters=[],  # Phase 4
    )

    return {"building_spec": building_spec.model_dump()}

# Build orchestration graph
workflow = StateGraph(ExtractionState)

workflow.add_node("discovery", discovery_node)
workflow.add_node("extract_project", project_extraction_node)
workflow.add_node("merge", merge_node)

workflow.set_entry_point("discovery")
workflow.add_edge("discovery", "extract_project")
workflow.add_edge("extract_project", "merge")
workflow.add_edge("merge", END)

app = workflow.compile()

# Run extraction
result = app.invoke({
    "eval_name": "chamberlin-circle",
    "pdf_path": "evals/chamberlin-circle/plans.pdf",
    "page_images": ["evals/chamberlin-circle/preprocessed/page_001.png", ...],
    "document_map": None,
    "project_extraction": None,
    "building_spec": None,
    "error": None,
})

if result["error"]:
    print(f"Extraction failed: {result['error']}")
else:
    print(f"Extracted: {result['building_spec']}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt engineering for JSON | Structured outputs (output_config.format) | GA Jan 2026 | Eliminates JSON parsing errors, no retries needed for schema compliance |
| Base64 image encoding | Files API (file_id references) | Beta April 2025 | Reduces request size 33%, enables image reuse, faster uploads |
| Manual Pydantic validation | .parse() method with transform_schema() | SDK 0.45+ (2025) | Automatic schema transformation, validates against original constraints |
| Custom agent frameworks | LangGraph production patterns | 2025-2026 | Fastest framework (lowest latency), graph-based state, built-in debugging |
| Sequential API calls | Batch processing with 50% discount | Available 2025 | Not applicable for interactive extraction, but good for eval runs |
| GPT-4V for documents | Claude Sonnet 4.5 vision | Sonnet 4.5 release 2025 | Superior document understanding, better at technical drawings per benchmarks |

**Deprecated/outdated:**
- **Instructor library for structured outputs**: Anthropic SDK now has native support via output_config.format and .parse()
- **LangChain Agents (legacy)**: Replaced by LangGraph for production multi-agent systems (same org, newer architecture)
- **Manual JSON schema writing**: Use Pydantic models + transform_schema(); SDK handles unsupported features automatically
- **Single-image-per-request**: Claude supports up to 100 images per request (April 2025 API update)

## Open Questions

Things that couldn't be fully resolved:

1. **Discovery Agent Accuracy**
   - What we know: Claude vision can classify page types (schedules vs drawings vs CBECC forms)
   - What's unclear: How well it performs on Title 24 documents specifically (no benchmarks found)
   - Recommendation: Build discovery agent with confidence scores, manually verify on 5 evals, iterate on prompts if accuracy < 90%

2. **Optimal Document Map Granularity**
   - What we know: Discovery agent should identify schedules, CBECC pages, drawings
   - What's unclear: Should it also map specific schedule types (window schedule vs door schedule vs equipment schedule)?
   - Recommendation: Start with high-level categories (schedule/cbecc/drawing), add granularity in Phase 4 if extractors need it

3. **Token Cost for Multi-Page Processing**
   - What we know: ~1600 tokens per 1568px image, ~$4.80/1K images Sonnet 4.5
   - What's unclear: Actual cost for 5 evals with 10-30 pages each (150 pages total)
   - Recommendation: Budget $0.72 per full extraction (150 pages × $4.80/1000), track actual costs in Phase 3

4. **Error Recovery Strategy**
   - What we know: Retry with exponential backoff for transient errors (429, 500, 503)
   - What's unclear: What to do when Claude refuses request (refusal stop_reason) or extraction quality is low
   - Recommendation: Log refusals, fail extraction with clear error; quality issues handled by improvement loop (Phase 5)

5. **State Persistence for Long Extractions**
   - What we know: LangGraph supports persistence, streaming, checkpointing
   - What's unclear: Whether Phase 3 needs persistence (single-domain extraction likely < 1 minute)
   - Recommendation: Skip persistence in Phase 3, add in Phase 4 when extraction expands to all domains (longer runtime)

## Sources

### Primary (HIGH confidence)
- [Claude Vision API Documentation](https://platform.claude.com/docs/en/build-with-claude/vision) - Image handling, best practices, multi-page patterns
- [Claude Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - output_config.format, Pydantic integration, guarantees
- [LangGraph Workflows Documentation](https://docs.langchain.com/oss/python/langgraph/workflows-agents) - Orchestrator-worker pattern, state management
- [Pydantic JSON Schema Documentation](https://docs.pydantic.dev/latest/concepts/json_schema/) - Schema generation, validation

### Secondary (MEDIUM confidence)
- [Multi-Agent Orchestration Patterns 2026](https://kanerika.com/blogs/ai-agent-orchestration/) - Industry momentum, ROI data
- [LangGraph Multi-Agent Framework Guide](https://research.aimultiple.com/agentic-frameworks/) - Performance comparisons, fastest framework claim
- [Retry Logic Best Practices 2025](https://sparkco.ai/blog/mastering-retry-logic-agents-a-deep-dive-into-2025-best-practices) - Exponential backoff, jitter patterns
- [Agent Error Handling Strategies](https://portkey.ai/blog/retries-fallbacks-and-circuit-breakers-in-llm-apps/) - Circuit breakers, fallback chains
- [Self-Improving Agents Research](https://arxiv.org/abs/2510.07841) - Test-time self-improvement, relevant for Phase 5
- [Pydantic Validation Guide](https://superjson.ai/blog/2025-08-24-json-schema-validation-python-pydantic-guide/) - Production best practices
- [Claude Document Extraction Guide](https://getstream.io/blog/anthropic-claude-visual-reasoning/) - Developer's guide to vision API
- [Vision Model Structured Outputs](https://docs.nvidia.com/nim/vision-language-models/1.2.0/structured-generation.html) - VLM structured generation patterns

### Tertiary (LOW confidence - flagged for validation)
- [Title 24 2026 Compliance Guide](https://envigilance.com/energy-monitoring/title-24/) - CBECC software role (need to verify document structure claims with actual Title 24 PDFs)
- [Building Plan AI Extraction](https://www.businesswaretech.com/blog/architectural-floor-plan-analysis) - Schedule detection capabilities (vendor claims, not verified)
- [Document Structure Detection Research](https://www.researchgate.net/publication/265487498_Machine_Learning_for_Document_Structure_Recognition) - Academic research (older, pre-2026 VLMs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation, SDK features verified
- Architecture patterns: MEDIUM - LangGraph is fastest per 2026 reports, orchestrator-worker pattern well-documented, but no Title 24-specific benchmarks
- Structured outputs: HIGH - Official Anthropic docs, GA release confirmed Jan 2026
- Vision API best practices: HIGH - Official Anthropic documentation, clear guidelines
- Discovery agent approach: MEDIUM - Claude vision can classify pages (verified), but Title 24-specific accuracy unknown
- Pitfalls: MEDIUM - Based on official docs (caching, image ordering) and 2026 best practices articles (retry logic)

**Research date:** 2026-02-03
**Valid until:** 2026-03-05 (30 days - stable domain, but agent frameworks evolving quickly)

**Key uncertainties requiring validation:**
1. Discovery agent accuracy on Title 24 documents (build and test in Phase 3)
2. Actual token costs for 5-eval corpus (track during development)
3. Whether extraction quality meets F1 targets without improvement loop (Phase 5 may be needed)
4. Optimal prompt patterns for Title 24 schedule extraction (iterate based on eval results)
