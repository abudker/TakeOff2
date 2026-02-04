# Phase 4: Multi-Domain Extraction - Research

**Researched:** 2026-02-03
**Domain:** Multi-agent parallel extraction, domain-specific extractors, orchestration and merge patterns
**Confidence:** HIGH

## Summary

Phase 4 extends the single-domain extraction from Phase 3 to cover all extraction domains: Zones, Windows, HVAC, and DHW (water heaters). The phase implements parallel extraction followed by sequential reconciliation, as decided in CONTEXT.md. The orchestrator coordinates four domain extractors that run in parallel, then performs a reconciliation pass to deduplicate arrays and flag conflicts.

The standard approach for this domain follows established multi-agent orchestration patterns: (1) parallel execution using Python's asyncio.gather for concurrent Claude Code subprocess invocations, (2) semaphore-based concurrency control to avoid overwhelming Claude's rate limits, (3) name-based array deduplication for zones/windows/systems, and (4) conflict flagging rather than auto-resolution for field-level disagreements.

Key insight: The project already uses Claude Code agent invocation via subprocess (established in Phase 3). Phase 4 extends this by invoking multiple agents in parallel using asyncio, then merging their outputs into a unified BuildingSpec with a conflicts section.

**Primary recommendation:** Use asyncio.gather with semaphore (3 concurrent max) for parallel extractor invocation, implement name-matching deduplication for array elements, and add a reconciliation agent that reviews conflicts and produces final merged output.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess | stdlib | Invoke Claude Code agents | Established pattern from Phase 3 |
| asyncio | stdlib | Parallel agent invocation | Built-in, no dependencies, supports gather() |
| pydantic | 2.10+ | Schema validation | Already used for BuildingSpec and submodels |
| json | stdlib | Parse agent responses | Existing extract_json_from_response() utility |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging | stdlib | Extraction diagnostics | Already configured in orchestrator |
| pathlib | stdlib | File path handling | Already used throughout |
| typing | stdlib | Type hints | Already used for TypedDict |

### No New Dependencies Required

Phase 4 requires no new dependencies. The existing stack (subprocess, asyncio, pydantic, json) provides everything needed for parallel extraction and merge.

**Note:** asyncio is used only for parallel subprocess orchestration, NOT for async API calls. The Claude Code agents are still invoked via subprocess.run(), but wrapped in asyncio.to_thread() for concurrent execution.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.gather | concurrent.futures.ThreadPoolExecutor | asyncio.gather is cleaner for 4 concurrent tasks, ThreadPoolExecutor better for CPU-bound |
| Name-matching dedup | Cosine similarity | Name-matching is simpler and sufficient for zone/window/system names |
| Conflict flagging | Auto-resolution | Flagging is safer and aligns with user decision (CONTEXT.md) |

## Architecture Patterns

### Recommended Project Structure

```
src/
  agents/
    extractors/
      zones.py          # Stub pointing to .claude/agents/zones-extractor.md
      windows.py        # Stub pointing to .claude/agents/windows-extractor.md
      hvac.py           # Stub pointing to .claude/agents/hvac-extractor.md
      dhw.py            # Stub pointing to .claude/agents/dhw-extractor.md
      project.py        # Existing (Phase 3)
      base.py           # Existing (Phase 3)
    orchestrator.py     # Extended with parallel extraction + reconciliation
    cli.py              # Extended with verbose diagnostics flag
.claude/
  agents/
    zones-extractor.md       # Zone + wall extraction
    windows-extractor.md     # Fenestration extraction
    hvac-extractor.md        # HVAC systems extraction
    dhw-extractor.md         # Water heater extraction
    reconciler.md            # Optional: Conflict resolution
  instructions/
    zones-extractor/
      instructions.md
      field-guide.md
    windows-extractor/
      instructions.md
      field-guide.md
    hvac-extractor/
      instructions.md
      field-guide.md
    dhw-extractor/
      instructions.md
      field-guide.md
```

### Pattern 1: Parallel Extractor Invocation

**What:** Run multiple Claude Code extractors concurrently using asyncio
**When to use:** Independent extraction tasks that don't depend on each other's output
**Example:**

```python
# Source: Adapted from Phase 3 orchestrator pattern + asyncio best practices
import asyncio
from typing import Dict, Any

async def invoke_claude_agent_async(agent_name: str, prompt: str, timeout: int = 300) -> str:
    """Async wrapper for Claude Code agent invocation."""
    return await asyncio.to_thread(
        invoke_claude_agent,  # Existing sync function
        agent_name,
        prompt,
        timeout
    )

async def run_parallel_extraction(
    page_images: List[Path],
    document_map: DocumentMap
) -> Dict[str, Any]:
    """Run all domain extractors in parallel."""
    # Create extraction tasks
    tasks = [
        invoke_claude_agent_async("zones-extractor", zones_prompt),
        invoke_claude_agent_async("windows-extractor", windows_prompt),
        invoke_claude_agent_async("hvac-extractor", hvac_prompt),
        invoke_claude_agent_async("dhw-extractor", dhw_prompt),
    ]

    # Gather results (all 4 run concurrently)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "zones": parse_or_error(results[0], "zones"),
        "windows": parse_or_error(results[1], "windows"),
        "hvac": parse_or_error(results[2], "hvac"),
        "dhw": parse_or_error(results[3], "dhw"),
    }
```

### Pattern 2: Semaphore-Based Rate Limit Protection

**What:** Limit concurrent Claude API calls to avoid rate limiting
**When to use:** When running parallel extractions that could exceed rate limits
**Example:**

```python
# Source: https://medium.com/@mr.sourav.raj/mastering-asyncio-semaphores-in-python
EXTRACTION_SEMAPHORE = asyncio.Semaphore(3)  # Max 3 concurrent extractors

async def invoke_with_semaphore(agent_name: str, prompt: str, timeout: int = 300) -> str:
    """Invoke agent with semaphore protection."""
    async with EXTRACTION_SEMAPHORE:
        return await invoke_claude_agent_async(agent_name, prompt, timeout)

async def run_parallel_extraction_protected(...):
    """Run extractors with rate limit protection."""
    tasks = [
        invoke_with_semaphore("zones-extractor", zones_prompt),
        invoke_with_semaphore("windows-extractor", windows_prompt),
        invoke_with_semaphore("hvac-extractor", hvac_prompt),
        invoke_with_semaphore("dhw-extractor", dhw_prompt),
    ]
    # Even with 4 tasks, only 3 run concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Pattern 3: Name-Based Array Deduplication

**What:** Deduplicate array elements by matching on name field
**When to use:** Merging zones, windows, walls, HVAC systems from multiple extractors
**Example:**

```python
# Source: Domain-specific pattern for building spec merging
from typing import List, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def deduplicate_by_name(items: List[T]) -> tuple[List[T], List[dict]]:
    """
    Deduplicate list of Pydantic models by name field.

    Returns:
        (deduplicated_items, conflicts)
    """
    seen: Dict[str, T] = {}
    conflicts = []

    for item in items:
        name = item.name
        if name in seen:
            # Conflict detected - same name, potentially different values
            existing = seen[name]
            if item.model_dump() != existing.model_dump():
                conflicts.append({
                    "field": name,
                    "existing": existing.model_dump(),
                    "new": item.model_dump(),
                    "resolution": "kept_first"
                })
        else:
            seen[name] = item

    return list(seen.values()), conflicts
```

### Pattern 4: Conflict Flagging in BuildingSpec

**What:** Add conflicts section to BuildingSpec for review
**When to use:** When extractors report different values for the same field
**Example:**

```python
# Source: CONTEXT.md decision on conflict handling
class ExtractionConflict(BaseModel):
    """A conflict between extractor outputs."""
    field: str
    source_extractor: str
    reported_value: Any
    conflicting_extractor: str
    conflicting_value: Any
    resolution: str  # "flagged_for_review" | "kept_first" | "reconciled"

class ExtractionStatus(BaseModel):
    """Per-domain extraction status."""
    domain: str  # zones, windows, hvac, dhw
    status: str  # "success" | "partial" | "failed"
    error: Optional[str] = None
    retry_count: int = 0

class BuildingSpecExtended(BaseModel):
    """BuildingSpec with extraction metadata."""
    # Core fields (existing)
    project: ProjectInfo
    envelope: EnvelopeInfo
    zones: List[ZoneInfo]
    walls: List[WallComponent]
    windows: List[WindowComponent]
    hvac_systems: List[HVACSystem]
    water_heating_systems: List[WaterHeatingSystem]
    # ... other existing fields

    # Extraction metadata (new)
    extraction_status: Dict[str, ExtractionStatus] = Field(default_factory=dict)
    conflicts: List[ExtractionConflict] = Field(default_factory=list)
```

### Pattern 5: Extractor Retry with Continuation

**What:** Retry failed extractors once, then continue with partial results
**When to use:** When one extractor fails but others succeed
**Example:**

```python
# Source: CONTEXT.md decision on error handling
async def extract_with_retry(
    agent_name: str,
    prompt: str,
    timeout: int = 600
) -> tuple[dict | None, ExtractionStatus]:
    """
    Extract with one retry on failure.

    Returns:
        (extraction_result, status)
    """
    for attempt in range(2):  # Max 2 attempts
        try:
            response = await invoke_with_semaphore(agent_name, prompt, timeout)
            data = extract_json_from_response(response)
            return data, ExtractionStatus(
                domain=agent_name.replace("-extractor", ""),
                status="success",
                retry_count=attempt
            )
        except Exception as e:
            if attempt == 0:
                logger.warning(f"{agent_name} failed, retrying: {e}")
                continue
            else:
                logger.error(f"{agent_name} failed after retry: {e}")
                return None, ExtractionStatus(
                    domain=agent_name.replace("-extractor", ""),
                    status="failed",
                    error=str(e),
                    retry_count=1
                )

    # Should not reach here, but handle just in case
    return None, ExtractionStatus(
        domain=agent_name.replace("-extractor", ""),
        status="failed",
        error="Unknown error",
        retry_count=1
    )
```

### Anti-Patterns to Avoid

- **Auto-resolving conflicts:** Don't automatically choose between conflicting values. Flag for review per CONTEXT.md decision.
- **Sequential extraction when parallel is possible:** Zones, windows, HVAC, DHW are independent - extract in parallel.
- **Ignoring rate limits:** Use semaphore (max 3 concurrent) to avoid HTTP 429 errors.
- **Failing entire extraction on one domain failure:** Continue with partial results, mark failed domains in extraction_status.
- **Complex deduplication logic:** Name-matching is sufficient for zone/window/system names. Don't over-engineer with embeddings or fuzzy matching.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel subprocess execution | Manual threading | asyncio.gather + asyncio.to_thread | Clean async wrapper, handles exceptions, built-in timeout |
| Rate limit handling | Custom token bucket | asyncio.Semaphore | Built into asyncio, simple configuration |
| JSON extraction from agent responses | New parser | Existing extract_json_from_response() | Already handles markdown blocks, fallbacks |
| Schema validation | Manual dict checking | Pydantic model_validate() | Already used throughout, comprehensive error messages |
| Retry logic | Custom retry loop | Simple for loop with attempt count | 2 attempts is sufficient per CONTEXT.md |

**Key insight:** The Phase 3 foundation provides most utilities needed. Phase 4 adds parallelism and merge logic, not fundamentally new patterns.

## Common Pitfalls

### Pitfall 1: Rate Limit Exhaustion with Parallel Requests

**What goes wrong:** Running 4 extractors simultaneously exceeds Claude's RPM or ITPM limits, causing 429 errors
**Why it happens:** Each extractor sends large image payloads; 4x concurrent can hit limits
**How to avoid:**
- Use semaphore to limit concurrent requests (3 is safe for most tiers)
- Monitor rate limit headers in responses
- For Tier 1 (50 RPM, 30K ITPM), sequential may be safer
- For Tier 2+ (1000+ RPM, 450K+ ITPM), 4 parallel is fine
**Warning signs:** HTTP 429 errors with "retry-after" header

### Pitfall 2: Lost Context in Domain-Specific Prompts

**What goes wrong:** Extractor misses data because prompt doesn't include full document context
**Why it happens:** Each extractor only sees its assigned pages, missing cross-references
**How to avoid:**
- Include document_map summary in all extractor prompts
- Include page numbers from other domains that might reference this domain
- Cross-reference: windows often appear on floor plans (drawings), not just schedules
**Warning signs:** Extractors returning empty arrays when data exists

### Pitfall 3: Duplicate Items from Multiple Sources

**What goes wrong:** Same window/zone/system appears multiple times from different pages
**Why it happens:** Item mentioned on multiple pages, each occurrence extracted separately
**How to avoid:**
- Implement name-based deduplication as post-processing step
- Instruct extractors to use consistent naming (e.g., "N Wall" not "North Wall" vs "NorthWall")
- Merge step deduplicates before adding to BuildingSpec
**Warning signs:** BuildingSpec has duplicate entries with same name

### Pitfall 4: Silent Field Conflicts

**What goes wrong:** Extractors report different values for same field, but conflict goes unnoticed
**Why it happens:** Simple merge just overwrites without comparison
**How to avoid:**
- Compare all fields when deduplicating, not just name
- Flag any field-level differences as conflicts
- Include conflicts section in output for human review
**Warning signs:** Verification shows wrong values that existed correctly in another extractor's output

### Pitfall 5: Timeout Cascade in Parallel Execution

**What goes wrong:** One slow extractor causes entire asyncio.gather to hang
**Why it happens:** gather waits for all tasks, one slow task blocks completion
**How to avoid:**
- Use asyncio.wait_for() with per-task timeout instead of global timeout
- Or use asyncio.gather with return_exceptions=True to continue on failure
- Set reasonable per-extractor timeouts (10 min for complex pages)
**Warning signs:** Extraction hangs, other extractors already finished but waiting

### Pitfall 6: Missing Field Representation Inconsistency

**What goes wrong:** Some extractors return null, others omit field, others return empty string
**Why it happens:** No standardized representation for missing data
**How to avoid:**
- Standardize in all extractor instructions: use null for missing values, never omit
- Post-processing normalizes: empty string -> null, missing -> null
- Pydantic models have Optional fields with default None
**Warning signs:** Pydantic validation errors, inconsistent null handling

## Code Examples

Verified patterns from official sources:

### Complete Parallel Extraction Orchestration

```python
# Source: Adapted from Phase 3 orchestrator + asyncio best practices
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Rate limit protection
EXTRACTION_SEMAPHORE = asyncio.Semaphore(3)

async def invoke_extractor(
    agent_name: str,
    prompt: str,
    timeout: int = 600
) -> tuple[Optional[Dict[str, Any]], str]:
    """
    Invoke extractor with semaphore protection and retry.

    Returns:
        (parsed_json_or_none, status)
    """
    async with EXTRACTION_SEMAPHORE:
        for attempt in range(2):
            try:
                response = await asyncio.to_thread(
                    invoke_claude_agent,
                    agent_name,
                    prompt,
                    timeout
                )
                data = extract_json_from_response(response)
                return data, "success"
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"{agent_name} attempt 1 failed: {e}")
                    await asyncio.sleep(2)  # Brief pause before retry
                else:
                    logger.error(f"{agent_name} failed after retry: {e}")
                    return None, f"failed: {str(e)}"
    return None, "failed: unknown"


async def run_multi_domain_extraction(
    page_images: List[Path],
    document_map: DocumentMap
) -> Dict[str, Any]:
    """
    Run all domain extractors in parallel and merge results.
    """
    # Build prompts for each domain
    prompts = build_extraction_prompts(page_images, document_map)

    # Create extraction tasks
    tasks = [
        invoke_extractor("zones-extractor", prompts["zones"]),
        invoke_extractor("windows-extractor", prompts["windows"]),
        invoke_extractor("hvac-extractor", prompts["hvac"]),
        invoke_extractor("dhw-extractor", prompts["dhw"]),
    ]

    # Run in parallel
    results = await asyncio.gather(*tasks)

    # Parse results
    extractions = {
        "zones": results[0],
        "windows": results[1],
        "hvac": results[2],
        "dhw": results[3],
    }

    return extractions


def build_extraction_prompts(
    page_images: List[Path],
    document_map: DocumentMap
) -> Dict[str, str]:
    """Build domain-specific prompts with relevant pages."""
    # Filter pages by type
    schedule_pages = document_map.schedule_pages
    cbecc_pages = document_map.cbecc_pages
    drawing_pages = document_map.drawing_pages

    # All domains need schedule + CBECC pages
    relevant_pages = sorted(set(schedule_pages + cbecc_pages))

    # Windows also need drawing pages for floor plan references
    window_pages = sorted(set(relevant_pages + drawing_pages[:5]))  # Limit drawings

    return {
        "zones": build_zones_prompt(page_images, relevant_pages, document_map),
        "windows": build_windows_prompt(page_images, window_pages, document_map),
        "hvac": build_hvac_prompt(page_images, relevant_pages, document_map),
        "dhw": build_dhw_prompt(page_images, relevant_pages, document_map),
    }
```

### Merge and Reconciliation

```python
# Source: CONTEXT.md merge strategy decisions
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel

def merge_extractions(
    project_data: Dict[str, Any],
    domain_extractions: Dict[str, tuple[Optional[Dict], str]]
) -> Tuple[BuildingSpec, List[Dict], Dict[str, str]]:
    """
    Merge all extractions into BuildingSpec.

    Returns:
        (building_spec, conflicts, extraction_status)
    """
    conflicts = []
    extraction_status = {}

    # Start with project extraction (Phase 3)
    spec = BuildingSpec(
        project=ProjectInfo.model_validate(project_data["project"]),
        envelope=EnvelopeInfo.model_validate(project_data["envelope"]),
    )

    # Merge zones
    zones_result, zones_status = domain_extractions["zones"]
    extraction_status["zones"] = zones_status
    if zones_result:
        zones, zone_conflicts = parse_and_deduplicate_zones(zones_result)
        spec.zones = zones
        spec.walls = parse_walls(zones_result)
        conflicts.extend(zone_conflicts)

    # Merge windows
    windows_result, windows_status = domain_extractions["windows"]
    extraction_status["windows"] = windows_status
    if windows_result:
        windows, window_conflicts = parse_and_deduplicate_windows(windows_result)
        spec.windows = windows
        conflicts.extend(window_conflicts)

    # Merge HVAC
    hvac_result, hvac_status = domain_extractions["hvac"]
    extraction_status["hvac"] = hvac_status
    if hvac_result:
        systems, hvac_conflicts = parse_and_deduplicate_hvac(hvac_result)
        spec.hvac_systems = systems
        conflicts.extend(hvac_conflicts)

    # Merge DHW
    dhw_result, dhw_status = domain_extractions["dhw"]
    extraction_status["dhw"] = dhw_status
    if dhw_result:
        water_heating, dhw_conflicts = parse_and_deduplicate_dhw(dhw_result)
        spec.water_heating_systems = water_heating
        conflicts.extend(dhw_conflicts)

    return spec, conflicts, extraction_status


def parse_and_deduplicate_zones(data: Dict) -> Tuple[List[ZoneInfo], List[Dict]]:
    """Parse zones and deduplicate by name."""
    zones = [ZoneInfo.model_validate(z) for z in data.get("zones", [])]
    return deduplicate_by_name(zones)
```

### CLI Extension for Verbose Diagnostics

```python
# Source: CONTEXT.md decision on --verbose flag
@cli.command("extract-one")
@click.argument("eval_id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed diagnostics")
@click.pass_context
def extract_one(ctx, eval_id: str, verbose: bool):
    """Extract from a single evaluation case."""
    # ... existing setup ...

    result = run_extraction(eval_id, eval_dir)

    if verbose:
        # Show diagnostics
        click.echo("\n--- Extraction Diagnostics ---")
        for domain, status in result.get("extraction_status", {}).items():
            click.echo(f"  {domain}: {status}")

        conflicts = result.get("conflicts", [])
        if conflicts:
            click.echo(f"\n  Conflicts: {len(conflicts)}")
            for c in conflicts[:5]:  # Show first 5
                click.echo(f"    - {c['field']}: {c['resolution']}")

        # Token usage would require API-level tracking (out of scope)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sequential extraction | Parallel extraction with asyncio | 2025-2026 | 36%+ faster per multi-agent benchmarks |
| Direct API calls | Claude Code subprocess invocation | Phase 3 (2026-02) | Simpler agent management, no API keys |
| Auto-resolve conflicts | Flag for review | User decision | Safer, supports human-in-loop |
| LangGraph StateGraph | Simple asyncio.gather | Phase 3 (2026-02) | Reduced complexity for linear workflow |

**Deprecated/outdated:**
- **LangGraph for simple workflows:** Removed in Phase 3, sequential/parallel asyncio is sufficient
- **Direct Anthropic API:** Project uses Claude Code agent invocation pattern
- **Complex deduplication (embeddings/cosine):** Name-matching sufficient for structured data

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal Semaphore Limit**
   - What we know: Claude API has tier-based rate limits (50-4000 RPM)
   - What's unclear: Actual usage tier for this project
   - Recommendation: Default to 3 concurrent, make configurable via env var or CLI flag

2. **Drawing Pages for Window Extraction**
   - What we know: Windows appear on both schedules and floor plans
   - What's unclear: How many drawing pages to include without overwhelming context
   - Recommendation: Include first 5 drawing pages for windows, schedule+CBECC for other domains

3. **Sparse Output Detection Heuristics**
   - What we know: CONTEXT.md mentions detecting "suspiciously sparse" output
   - What's unclear: What thresholds define "sparse" (0 items? <3 items?)
   - Recommendation: Flag warning if zones=0 or windows=0 (should always exist), leave exact heuristics to Claude's discretion

4. **Confidence Scores for Improvement Loop**
   - What we know: CONTEXT.md leaves this to Claude's discretion
   - What's unclear: Whether Phase 5 improvement loop needs extraction confidence
   - Recommendation: Start without confidence scores, add if Phase 5 needs them

## Sources

### Primary (HIGH confidence)
- [Claude API Rate Limits](https://platform.claude.com/docs/en/api/rate-limits) - Tier-based limits: 50-4000 RPM, 30K-2M ITPM
- [Claude Batch Processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing) - 50% discount for async processing (future optimization)
- [Pydantic Models Documentation](https://docs.pydantic.dev/latest/concepts/models/) - Validation, Optional fields, model_validate()
- Phase 3 codebase (03-04-SUMMARY.md, orchestrator.py) - Claude Code agent invocation pattern

### Secondary (MEDIUM confidence)
- [Multi-Agent Orchestration 2026](https://dev.to/eira-wexford/how-to-build-multi-agent-systems-complete-2026-guide-1io6) - Parallel execution patterns, 36% speedup benchmark
- [Running Claude Instances in Parallel](https://dev.to/bredmond1019/multi-agent-orchestration-running-10-claude-instances-in-parallel-part-3-29da) - Subprocess parallelization patterns
- [Asyncio Semaphores Guide](https://medium.com/@mr.sourav.raj/mastering-asyncio-semaphores-in-python-a-complete-guide-to-concurrency-control-6b4dd940e10e) - Rate limit protection patterns
- [Pydantic Partial Validation](https://pypi.org/project/pydantic-partial/) - Handling missing fields

### Tertiary (LOW confidence)
- [LLM Building Energy Models](https://www.osti.gov/servlets/purl/2480816) - Academic research on LLM building spec extraction
- [Document Data Extraction 2026](https://www.vellum.ai/blog/document-data-extraction-llms-vs-ocrs) - LLM vs OCR comparison

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries (asyncio, subprocess, pydantic), no new dependencies
- Architecture patterns: HIGH - Parallel asyncio patterns well-documented, extend Phase 3 foundation
- Merge/deduplication: MEDIUM - Name-matching is straightforward, but edge cases may emerge
- Rate limit handling: MEDIUM - Semaphore limit is a reasonable default, may need tuning
- Pitfalls: HIGH - Based on API documentation and Phase 3 experience

**Research date:** 2026-02-03
**Valid until:** 2026-03-05 (30 days - stable domain, building on Phase 3 patterns)

**Key uncertainties requiring validation:**
1. Semaphore limit (3) may need adjustment based on actual rate limit tier
2. Drawing page inclusion for window extraction needs testing
3. Sparse output heuristics left to implementation discretion
4. Confidence scores deferred unless Phase 5 requires them
