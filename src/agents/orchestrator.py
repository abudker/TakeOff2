"""Orchestrator - Parallel multi-domain extraction pipeline using Claude Code agents.

Claude Code Agent Invocation Pattern:
    When running outside Claude Code context (from CLI), invoke agents via:
    claude --agent <name> --print "<prompt>"

    This delegates execution to Claude Code's agent runtime instead of
    making direct Anthropic API calls.

Multi-Domain Extraction:
    The orchestrator runs 4 domain extractors in parallel using asyncio:
    - zones-extractor: Thermal zones and walls
    - windows-extractor: Windows and fenestration
    - hvac-extractor: HVAC systems and distribution
    - dhw-extractor: Domestic hot water systems

    Results are merged into a single BuildingSpec with conflict detection.
"""
import asyncio
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from schemas.discovery import DocumentMap
from schemas.building_spec import (
    BuildingSpec, ProjectInfo, EnvelopeInfo, ZoneInfo, WallComponent,
    WindowComponent, HVACSystem, WaterHeatingSystem,
    ExtractionConflict, ExtractionStatus
)

logger = logging.getLogger(__name__)

# Limit concurrent extractor invocations to avoid overwhelming the system
EXTRACTION_SEMAPHORE = asyncio.Semaphore(3)


def invoke_claude_agent(agent_name: str, prompt: str, timeout: int = 300) -> str:
    """
    Invoke a Claude Code agent via subprocess.

    Args:
        agent_name: Name of agent (e.g., "discovery", "project-extractor")
        prompt: Prompt to send to the agent
        timeout: Max seconds to wait (default: 5 minutes)

    Returns:
        Agent's response text

    Raises:
        RuntimeError: If agent execution fails
        FileNotFoundError: If claude CLI not found
    """
    cmd = [
        "claude",
        "--agent", agent_name,
        "--print",  # Output response to stdout, non-interactive mode
        prompt
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path.cwd())  # Ensure we're in project root
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            raise RuntimeError(f"Agent {agent_name} failed (exit {result.returncode}): {error_msg}")

        return result.stdout

    except FileNotFoundError:
        raise FileNotFoundError(
            "Claude CLI not found. Please install Claude Code: https://claude.ai/download"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Agent {agent_name} timed out after {timeout}s")


async def invoke_claude_agent_async(agent_name: str, prompt: str, timeout: int = 600) -> str:
    """
    Async wrapper for Claude Code agent invocation.

    Uses asyncio.to_thread to run blocking subprocess call in thread pool.
    Semaphore limits concurrent invocations.

    Args:
        agent_name: Name of agent to invoke
        prompt: Prompt to send to the agent
        timeout: Max seconds to wait (default: 10 minutes)

    Returns:
        Agent's response text
    """
    async with EXTRACTION_SEMAPHORE:
        return await asyncio.to_thread(
            invoke_claude_agent,
            agent_name,
            prompt,
            timeout
        )


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """
    Extract JSON from agent response, handling markdown code blocks.

    Args:
        response: Agent response text

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If no valid JSON found
    """
    # Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code blocks
    lines = response.split('\n')
    in_code_block = False
    json_lines = []

    for line in lines:
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block - try to parse accumulated JSON
                json_str = '\n'.join(json_lines)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    json_lines = []
            in_code_block = not in_code_block
        elif in_code_block:
            json_lines.append(line)

    # Last resort: look for {...} pattern
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass

    raise ValueError("No valid JSON found in agent response")


def run_discovery(page_images: List[Path]) -> DocumentMap:
    """
    Run discovery agent to classify document pages.

    Args:
        page_images: List of preprocessed page image paths

    Returns:
        DocumentMap with classified pages

    Raises:
        RuntimeError: If discovery agent fails
    """
    logger.info(f"Running discovery on {len(page_images)} pages")

    # Build prompt with page paths
    page_list = "\n".join([f"- Page {i+1}: {p}" for i, p in enumerate(page_images)])

    prompt = f"""Classify the pages in this Title 24 document.

Page image paths:
{page_list}

Read your instructions from .claude/instructions/discovery/instructions.md, then analyze each page image and return a DocumentMap JSON with the structure:

{{
  "total_pages": {len(page_images)},
  "pages": [
    {{
      "page_number": 1,
      "page_type": "schedule|cbecc|drawing|other",
      "confidence": "high|medium|low",
      "description": "brief description"
    }},
    ...
  ]
}}

Ensure all {len(page_images)} pages are classified.
"""

    # Invoke discovery agent
    response = invoke_claude_agent("discovery", prompt)

    # Parse response
    try:
        json_data = extract_json_from_response(response)
        document_map = DocumentMap.model_validate(json_data)

        logger.info(f"Discovery complete: {document_map.total_pages} pages classified")
        logger.info(f"  Schedule pages: {len(document_map.schedule_pages)}")
        logger.info(f"  CBECC pages: {len(document_map.cbecc_pages)}")
        logger.info(f"  Drawing pages: {len(document_map.drawing_pages)}")

        return document_map

    except Exception as e:
        logger.error(f"Failed to parse discovery response: {e}")
        logger.debug(f"Response was: {response[:500]}")
        raise RuntimeError(f"Discovery agent returned invalid response: {e}")


def run_project_extraction(
    page_images: List[Path],
    document_map: DocumentMap
) -> Dict[str, Any]:
    """
    Run project-extractor agent to extract building specifications.

    Args:
        page_images: List of all page image paths
        document_map: Document structure from discovery phase

    Returns:
        Dict with 'project' and 'envelope' keys containing extracted data

    Raises:
        RuntimeError: If extraction agent fails
        ValueError: If no relevant pages found
    """
    # Filter to relevant pages (schedule + cbecc pages)
    relevant_page_numbers = set(document_map.schedule_pages + document_map.cbecc_pages)

    if not relevant_page_numbers:
        raise ValueError("No schedule or CBECC pages found for extraction")

    # Filter page images to relevant ones (page_images are 0-indexed)
    relevant_images = [
        page_images[page_num - 1]
        for page_num in sorted(relevant_page_numbers)
        if page_num <= len(page_images)
    ]

    logger.info(f"Extracting from {len(relevant_images)} relevant pages: {sorted(relevant_page_numbers)}")

    # Build prompt with document map and relevant page paths
    page_list = "\n".join([
        f"- Page {sorted(relevant_page_numbers)[i]}: {p}"
        for i, p in enumerate(relevant_images)
    ])

    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    prompt = f"""Extract building specifications from this Title 24 document.

Document structure (from discovery):
{document_map_json}

Relevant page image paths (schedule + CBECC pages):
{page_list}

Read your instructions from:
- .claude/instructions/project-extractor/instructions.md
- .claude/instructions/project-extractor/field-guide.md

Then analyze the provided pages and return JSON with this structure:

{{
  "project": {{
    "run_title": "...",
    "address": "...",
    "city": "...",
    "climate_zone": 1-16,
    "fuel_type": "All Electric|Natural Gas|Mixed",
    "house_type": "Single Family|Multi Family",
    "dwelling_units": 1,
    "stories": 1,
    "bedrooms": 0
  }},
  "envelope": {{
    "conditioned_floor_area": 0.0,
    "window_area": 0.0,
    "window_to_floor_ratio": 0.0,
    "exterior_wall_area": 0.0,
    "fenestration_u_factor": null
  }},
  "notes": "Confidence and extraction observations"
}}

Focus on accuracy. Use the field guide to find the correct values.
"""

    # Invoke project-extractor agent
    response = invoke_claude_agent("project-extractor", prompt, timeout=600)  # 10 min for extraction

    # Parse response
    try:
        json_data = extract_json_from_response(response)

        # Validate that we got the expected structure
        if "project" not in json_data or "envelope" not in json_data:
            raise ValueError("Response missing 'project' or 'envelope' keys")

        # Validate against schemas
        project = ProjectInfo.model_validate(json_data["project"])
        envelope = EnvelopeInfo.model_validate(json_data["envelope"])

        logger.info(f"Extraction complete:")
        logger.info(f"  Project: {project.run_title}")
        logger.info(f"  Address: {project.address}, {project.city}")
        logger.info(f"  Climate zone: {project.climate_zone}")
        logger.info(f"  CFA: {envelope.conditioned_floor_area} sq ft")
        logger.info(f"  WWR: {envelope.window_to_floor_ratio:.2%}")

        return {
            "project": project.model_dump(),
            "envelope": envelope.model_dump(),
            "notes": json_data.get("notes", "")
        }

    except Exception as e:
        logger.error(f"Failed to parse extraction response: {e}")
        logger.debug(f"Response was: {response[:500]}")
        raise RuntimeError(f"Project extractor returned invalid response: {e}")


# ============================================================================
# Parallel Multi-Domain Extraction
# ============================================================================

async def extract_with_retry(
    agent_name: str,
    prompt: str,
    timeout: int = 600
) -> Tuple[Optional[Dict[str, Any]], ExtractionStatus]:
    """
    Extract with one retry on failure.

    Args:
        agent_name: Name of extractor agent (e.g., "zones-extractor")
        prompt: Extraction prompt
        timeout: Max seconds to wait

    Returns:
        Tuple of (extracted data dict or None, ExtractionStatus)
    """
    domain = agent_name.replace("-extractor", "")

    for attempt in range(2):
        try:
            response = await invoke_claude_agent_async(agent_name, prompt, timeout)
            data = extract_json_from_response(response)

            # Count items extracted
            items = 0
            for key, val in data.items():
                if isinstance(val, list):
                    items += len(val)

            logger.info(f"{agent_name} extracted {items} items")

            return data, ExtractionStatus(
                domain=domain,
                status="success",
                retry_count=attempt,
                items_extracted=items
            )
        except Exception as e:
            if attempt == 0:
                logger.warning(f"{agent_name} attempt 1 failed: {e}, retrying...")
                await asyncio.sleep(2)
            else:
                logger.error(f"{agent_name} failed after retry: {e}")
                return None, ExtractionStatus(
                    domain=domain,
                    status="failed",
                    error=str(e),
                    retry_count=1
                )

    # Should not reach here, but handle gracefully
    return None, ExtractionStatus(domain=domain, status="failed", error="Unknown error")


def build_domain_prompt(
    domain: str,
    page_images: List[Path],
    document_map: DocumentMap
) -> str:
    """
    Build extraction prompt for a specific domain.

    Args:
        domain: Domain name (zones, windows, hvac, dhw)
        page_images: List of all page image paths
        document_map: Document structure from discovery

    Returns:
        Formatted prompt string for the extractor agent
    """
    # Filter to relevant pages (schedule + CBECC for all domains)
    relevant_pages = sorted(set(document_map.schedule_pages + document_map.cbecc_pages))

    # Windows also benefit from drawing pages (floor plans show window locations)
    if domain == "windows":
        drawing_subset = document_map.drawing_pages[:5] if document_map.drawing_pages else []
        relevant_pages = sorted(set(relevant_pages + drawing_subset))

    # Build page list with paths
    page_list = "\n".join([
        f"- Page {p}: {page_images[p-1]}"
        for p in relevant_pages
        if p <= len(page_images)
    ])

    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    return f"""Extract {domain} data from this Title 24 document.

Document structure (from discovery):
{document_map_json}

Relevant page image paths:
{page_list}

Read your instructions from:
- .claude/instructions/{domain}-extractor/instructions.md
- .claude/instructions/{domain}-extractor/field-guide.md

Return JSON matching the schema for {domain} extraction.
Focus on accuracy and completeness.
"""


async def run_parallel_extraction(
    page_images: List[Path],
    document_map: DocumentMap
) -> Dict[str, Tuple[Optional[Dict[str, Any]], ExtractionStatus]]:
    """
    Run all domain extractors in parallel using asyncio.

    Args:
        page_images: List of preprocessed page image paths
        document_map: Document structure from discovery

    Returns:
        Dict mapping domain name to (data, status) tuple
    """
    logger.info("Starting parallel extraction for zones, windows, hvac, dhw")

    # Build prompts for each domain
    zones_prompt = build_domain_prompt("zones", page_images, document_map)
    windows_prompt = build_domain_prompt("windows", page_images, document_map)
    hvac_prompt = build_domain_prompt("hvac", page_images, document_map)
    dhw_prompt = build_domain_prompt("dhw", page_images, document_map)

    # Create extraction tasks
    tasks = [
        extract_with_retry("zones-extractor", zones_prompt),
        extract_with_retry("windows-extractor", windows_prompt),
        extract_with_retry("hvac-extractor", hvac_prompt),
        extract_with_retry("dhw-extractor", dhw_prompt),
    ]

    # Run in parallel
    results = await asyncio.gather(*tasks)

    logger.info("Parallel extraction complete")

    return {
        "zones": results[0],
        "windows": results[1],
        "hvac": results[2],
        "dhw": results[3],
    }


def deduplicate_by_name(
    items: List[BaseModel],
    source: str
) -> Tuple[List[BaseModel], List[ExtractionConflict]]:
    """
    Deduplicate items by name, tracking conflicts.

    Items with the same name are deduplicated, keeping the first occurrence.
    If duplicate items have different values, a conflict is recorded.

    Args:
        items: List of Pydantic models with 'name' attribute
        source: Name of the extractor for conflict tracking

    Returns:
        Tuple of (deduplicated list, list of conflicts)
    """
    seen: Dict[str, BaseModel] = {}
    conflicts: List[ExtractionConflict] = []

    for item in items:
        name = getattr(item, 'name', None)
        if name is None:
            continue

        if name in seen:
            existing = seen[name]
            # Check if values differ
            if item.model_dump() != existing.model_dump():
                conflicts.append(ExtractionConflict(
                    field="array_item",
                    item_name=name,
                    source_extractor=source,
                    reported_value=existing.model_dump(),
                    conflicting_extractor=source,
                    conflicting_value=item.model_dump(),
                    resolution="kept_first"
                ))
        else:
            seen[name] = item

    return list(seen.values()), conflicts


def merge_extractions(
    project_data: Dict[str, Any],
    domain_extractions: Dict[str, Tuple[Optional[Dict[str, Any]], ExtractionStatus]]
) -> Tuple[BuildingSpec, List[ExtractionConflict], Dict[str, ExtractionStatus]]:
    """
    Merge all extractions into a complete BuildingSpec.

    Handles partial failures gracefully - if one extractor fails, the others'
    results are still included.

    Args:
        project_data: Dict with 'project' and 'envelope' from project-extractor
        domain_extractions: Dict mapping domain to (data, status) tuples

    Returns:
        Tuple of (BuildingSpec, conflicts list, extraction_status dict)
    """
    conflicts: List[ExtractionConflict] = []
    extraction_status: Dict[str, ExtractionStatus] = {
        "project": ExtractionStatus(domain="project", status="success", items_extracted=2)
    }

    # Start with project extraction
    spec = BuildingSpec(
        project=ProjectInfo.model_validate(project_data["project"]),
        envelope=EnvelopeInfo.model_validate(project_data["envelope"])
    )

    # Merge zones
    zones_data, zones_status = domain_extractions["zones"]
    extraction_status["zones"] = zones_status
    if zones_data:
        if "zones" in zones_data:
            zones = [ZoneInfo.model_validate(z) for z in zones_data["zones"]]
            spec.zones, zone_conflicts = deduplicate_by_name(zones, "zones")
            conflicts.extend(zone_conflicts)
            logger.info(f"Merged {len(spec.zones)} zones")
        if "walls" in zones_data:
            walls = [WallComponent.model_validate(w) for w in zones_data["walls"]]
            spec.walls, wall_conflicts = deduplicate_by_name(walls, "zones")
            conflicts.extend(wall_conflicts)
            logger.info(f"Merged {len(spec.walls)} walls")

    # Merge windows
    windows_data, windows_status = domain_extractions["windows"]
    extraction_status["windows"] = windows_status
    if windows_data and "windows" in windows_data:
        windows = [WindowComponent.model_validate(w) for w in windows_data["windows"]]
        spec.windows, window_conflicts = deduplicate_by_name(windows, "windows")
        conflicts.extend(window_conflicts)
        logger.info(f"Merged {len(spec.windows)} windows")

    # Merge HVAC
    hvac_data, hvac_status = domain_extractions["hvac"]
    extraction_status["hvac"] = hvac_status
    if hvac_data and "hvac_systems" in hvac_data:
        systems = [HVACSystem.model_validate(s) for s in hvac_data["hvac_systems"]]
        spec.hvac_systems, hvac_conflicts = deduplicate_by_name(systems, "hvac")
        conflicts.extend(hvac_conflicts)
        logger.info(f"Merged {len(spec.hvac_systems)} HVAC systems")

    # Merge DHW
    dhw_data, dhw_status = domain_extractions["dhw"]
    extraction_status["dhw"] = dhw_status
    if dhw_data and "water_heating_systems" in dhw_data:
        wh_systems = [WaterHeatingSystem.model_validate(s) for s in dhw_data["water_heating_systems"]]
        spec.water_heating_systems, dhw_conflicts = deduplicate_by_name(wh_systems, "dhw")
        conflicts.extend(dhw_conflicts)
        logger.info(f"Merged {len(spec.water_heating_systems)} water heating systems")

    if conflicts:
        logger.warning(f"Found {len(conflicts)} conflicts during merge")

    return spec, conflicts, extraction_status


def run_extraction(eval_name: str, eval_dir: Path, parallel: bool = True) -> dict:
    """
    Run extraction workflow on an evaluation case.

    Workflow:
        1. Find preprocessed page images
        2. Invoke discovery agent -> DocumentMap
        3. Invoke project-extractor agent -> ProjectInfo + EnvelopeInfo
        4. If parallel=True: Invoke domain extractors in parallel (zones, windows, hvac, dhw)
        5. Merge all extractions into BuildingSpec with conflict detection
        6. Return final state

    Args:
        eval_name: Evaluation case identifier (e.g., "chamberlin-circle")
        eval_dir: Path to evaluation directory
        parallel: If True, run multi-domain extraction in parallel (default: True)

    Returns:
        Final state dict with building_spec or error

    Raises:
        FileNotFoundError: If preprocessed images or PDF not found
        RuntimeError: If workflow execution fails
    """
    logger.info(f"Starting extraction for {eval_name} (parallel={parallel})")

    try:
        # Find preprocessed images - look for any preprocessed subdirectory with page images
        preprocessed_base = eval_dir / "preprocessed"
        if not preprocessed_base.exists():
            raise FileNotFoundError(f"Preprocessed directory not found: {preprocessed_base}")

        # Find first subdirectory with page images
        preprocessed_dir = None
        pdf_path = None
        for subdir in preprocessed_base.iterdir():
            if subdir.is_dir() and list(subdir.glob("page-*.png")):
                preprocessed_dir = subdir
                # Find matching PDF
                pdf_path = eval_dir / f"{subdir.name}.pdf"
                if not pdf_path.exists():
                    # Try to find any PDF
                    pdf_files = list(eval_dir.glob("*.pdf"))
                    pdf_path = pdf_files[0] if pdf_files else None
                break

        if not preprocessed_dir:
            raise FileNotFoundError(f"No preprocessed images found in {preprocessed_base}")

        # Get all page images
        page_images = sorted(preprocessed_dir.glob("page-*.png"))
        if not page_images:
            raise FileNotFoundError(f"No preprocessed images found in {preprocessed_dir}")

        logger.info(f"Found {len(page_images)} preprocessed pages")

        # Step 1: Discovery phase
        document_map = run_discovery(page_images)

        # Step 2: Project extraction phase (always runs first)
        project_extraction = run_project_extraction(page_images, document_map)

        if parallel:
            # Step 3: Parallel multi-domain extraction
            logger.info("Starting parallel multi-domain extraction")
            domain_extractions = asyncio.run(
                run_parallel_extraction(page_images, document_map)
            )

            # Step 4: Merge all extractions
            building_spec, conflicts, extraction_status = merge_extractions(
                project_extraction,
                domain_extractions
            )

            # Add metadata to spec
            building_spec.extraction_status = extraction_status
            building_spec.conflicts = conflicts

            logger.info(f"Extraction complete for {eval_name}")
            logger.info(f"  Zones: {len(building_spec.zones)}")
            logger.info(f"  Walls: {len(building_spec.walls)}")
            logger.info(f"  Windows: {len(building_spec.windows)}")
            logger.info(f"  HVAC systems: {len(building_spec.hvac_systems)}")
            logger.info(f"  Water heating systems: {len(building_spec.water_heating_systems)}")
            logger.info(f"  Conflicts: {len(conflicts)}")
        else:
            # Legacy mode: project extraction only
            building_spec = BuildingSpec(
                project=ProjectInfo.model_validate(project_extraction["project"]),
                envelope=EnvelopeInfo.model_validate(project_extraction["envelope"])
            )
            logger.info(f"Project-only extraction complete for {eval_name}")

        return {
            "eval_name": eval_name,
            "pdf_path": str(pdf_path),
            "page_images": [str(p) for p in page_images],
            "document_map": document_map.model_dump(),
            "building_spec": building_spec.model_dump(),
            "error": None
        }

    except Exception as e:
        logger.error(f"Extraction failed for {eval_name}: {e}")
        return {
            "eval_name": eval_name,
            "error": str(e),
            "building_spec": None
        }
