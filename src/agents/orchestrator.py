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
from schemas.takeoff_spec import (
    TakeoffSpec, TakeoffProjectInfo, HouseWalls, OrientationWall,
    FenestrationEntry, ThermalBoundary, ConditionedZone,
    CeilingEntry, SlabEntry, HVACSystemEntry, DHWSystem,
    UncertaintyFlag, AssumptionEntry
)
from schemas.transform import transform_takeoff_to_building_spec

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


def merge_to_takeoff_spec(
    project_data: Dict[str, Any],
    domain_extractions: Dict[str, Tuple[Optional[Dict[str, Any]], ExtractionStatus]]
) -> Tuple[TakeoffSpec, List[UncertaintyFlag]]:
    """
    Merge domain extractions into an orientation-based TakeoffSpec.

    This function handles the new orientation-based output from extractors:
    - zones-extractor outputs house_walls and thermal_boundary
    - windows-extractor outputs fenestration nested under wall orientations
    - hvac/dhw extractors output system entries

    Args:
        project_data: Dict with 'project' and 'envelope' from project-extractor
        domain_extractions: Dict mapping domain to (data, status) tuples

    Returns:
        Tuple of (TakeoffSpec, flags list)
    """
    flags: List[UncertaintyFlag] = []

    # Build project info
    proj_dict = project_data.get("project", {})
    env_dict = project_data.get("envelope", {})

    project = TakeoffProjectInfo(
        run_id=proj_dict.get("run_id"),
        run_title=proj_dict.get("run_title"),
        run_number=proj_dict.get("run_number"),
        run_scope=proj_dict.get("run_scope"),
        address=proj_dict.get("address"),
        city=proj_dict.get("city"),
        climate_zone=proj_dict.get("climate_zone"),
        standards_version=proj_dict.get("standards_version"),
        fuel_type=proj_dict.get("fuel_type"),
        house_type=proj_dict.get("house_type"),
        dwelling_units=proj_dict.get("dwelling_units"),
        stories=proj_dict.get("stories"),
        bedrooms=proj_dict.get("bedrooms"),
        front_orientation=proj_dict.get("front_orientation"),
        all_orientations=proj_dict.get("all_orientations", False),
        conditioned_floor_area=env_dict.get("conditioned_floor_area"),
        window_area=env_dict.get("window_area"),
        window_to_floor_ratio=env_dict.get("window_to_floor_ratio"),
        exterior_wall_area=env_dict.get("exterior_wall_area"),
        attached_garage=proj_dict.get("attached_garage", False),
    )

    # Initialize TakeoffSpec components
    house_walls = HouseWalls()
    thermal_boundary = ThermalBoundary()
    ceilings: List[CeilingEntry] = []
    slab_floors: List[SlabEntry] = []
    hvac_systems: List[HVACSystemEntry] = []
    dhw_systems: List[DHWSystem] = []

    # Merge zones data (house_walls and thermal_boundary)
    zones_data, _ = domain_extractions.get("zones", (None, None))
    if zones_data:
        # Handle orientation-based house_walls output
        if "house_walls" in zones_data:
            hw = zones_data["house_walls"]
            if "north" in hw and hw["north"]:
                house_walls.north = OrientationWall.model_validate(hw["north"])
            if "east" in hw and hw["east"]:
                house_walls.east = OrientationWall.model_validate(hw["east"])
            if "south" in hw and hw["south"]:
                house_walls.south = OrientationWall.model_validate(hw["south"])
            if "west" in hw and hw["west"]:
                house_walls.west = OrientationWall.model_validate(hw["west"])
            logger.info("Merged house_walls from zones-extractor")

        # Handle thermal_boundary output
        if "thermal_boundary" in zones_data:
            tb = zones_data["thermal_boundary"]
            if "conditioned_zones" in tb:
                thermal_boundary.conditioned_zones = [
                    ConditionedZone.model_validate(z) for z in tb["conditioned_zones"]
                ]
            if "unconditioned_zones" in tb:
                from schemas.takeoff_spec import UnconditionedZone
                thermal_boundary.unconditioned_zones = [
                    UnconditionedZone.model_validate(z) for z in tb["unconditioned_zones"]
                ]
            if "total_conditioned_floor_area" in tb:
                thermal_boundary.total_conditioned_floor_area = tb["total_conditioned_floor_area"]
            logger.info(f"Merged thermal_boundary: {len(thermal_boundary.conditioned_zones)} conditioned zones")

        # Handle ceilings if present
        if "ceilings" in zones_data:
            ceilings = [CeilingEntry.model_validate(c) for c in zones_data["ceilings"]]
            logger.info(f"Merged {len(ceilings)} ceilings")

        # Handle slab_floors if present
        if "slab_floors" in zones_data:
            slab_floors = [SlabEntry.model_validate(s) for s in zones_data["slab_floors"]]
            logger.info(f"Merged {len(slab_floors)} slab floors")

        # Collect flags from zones extraction
        if "flags" in zones_data:
            flags.extend([UncertaintyFlag.model_validate(f) for f in zones_data["flags"]])

    # Merge windows data (fenestration nested under house_walls)
    windows_data, _ = domain_extractions.get("windows", (None, None))
    if windows_data:
        # Handle nested fenestration by wall orientation
        if "house_walls" in windows_data:
            hw = windows_data["house_walls"]
            # Merge fenestration into existing walls
            for orientation in ["north", "east", "south", "west"]:
                if orientation in hw and hw[orientation]:
                    wall_data = hw[orientation]
                    existing_wall = getattr(house_walls, orientation)
                    if existing_wall is None:
                        # Create wall if it doesn't exist
                        setattr(house_walls, orientation, OrientationWall.model_validate(wall_data))
                    elif "fenestration" in wall_data:
                        # Add fenestration to existing wall
                        existing_wall.fenestration = [
                            FenestrationEntry.model_validate(f) for f in wall_data["fenestration"]
                        ]
            logger.info("Merged fenestration from windows-extractor")

        # Legacy format: flat windows list (convert to orientation-based)
        elif "windows" in windows_data:
            # Group windows by wall/azimuth
            for w in windows_data["windows"]:
                window = FenestrationEntry.model_validate(w)
                # Determine orientation from azimuth or wall name
                wall_name = w.get("wall", "").lower()
                azimuth = w.get("azimuth", 0)

                if "north" in wall_name or (azimuth >= 315 or azimuth < 45):
                    if house_walls.north is None:
                        house_walls.north = OrientationWall()
                    house_walls.north.fenestration.append(window)
                elif "east" in wall_name or (45 <= azimuth < 135):
                    if house_walls.east is None:
                        house_walls.east = OrientationWall()
                    house_walls.east.fenestration.append(window)
                elif "south" in wall_name or (135 <= azimuth < 225):
                    if house_walls.south is None:
                        house_walls.south = OrientationWall()
                    house_walls.south.fenestration.append(window)
                elif "west" in wall_name or (225 <= azimuth < 315):
                    if house_walls.west is None:
                        house_walls.west = OrientationWall()
                    house_walls.west.fenestration.append(window)
            logger.info("Converted legacy windows to orientation-based")

        # Collect flags from windows extraction
        if "flags" in windows_data:
            flags.extend([UncertaintyFlag.model_validate(f) for f in windows_data["flags"]])

    # Merge HVAC systems
    hvac_data, _ = domain_extractions.get("hvac", (None, None))
    if hvac_data and "hvac_systems" in hvac_data:
        hvac_systems = [HVACSystemEntry.model_validate(s) for s in hvac_data["hvac_systems"]]
        logger.info(f"Merged {len(hvac_systems)} HVAC systems")
        if "flags" in hvac_data:
            flags.extend([UncertaintyFlag.model_validate(f) for f in hvac_data["flags"]])

    # Merge DHW systems
    dhw_data, _ = domain_extractions.get("dhw", (None, None))
    if dhw_data and "dhw_systems" in dhw_data:
        dhw_systems = [DHWSystem.model_validate(s) for s in dhw_data["dhw_systems"]]
        logger.info(f"Merged {len(dhw_systems)} DHW systems")
        if "flags" in dhw_data:
            flags.extend([UncertaintyFlag.model_validate(f) for f in dhw_data["flags"]])

    # Build TakeoffSpec
    takeoff_spec = TakeoffSpec(
        project=project,
        house_walls=house_walls,
        thermal_boundary=thermal_boundary,
        ceilings=ceilings,
        slab_floors=slab_floors,
        hvac_systems=hvac_systems,
        dhw_systems=dhw_systems,
        flags=flags,
        extraction_notes=project_data.get("notes", ""),
    )

    logger.info(f"Built TakeoffSpec with {len(flags)} uncertainty flags")
    return takeoff_spec, flags


def run_extraction(eval_name: str, eval_dir: Path, parallel: bool = True, output_takeoff: bool = False) -> dict:
    """
    Run extraction workflow on an evaluation case.

    Workflow:
        1. Find preprocessed page images
        2. Invoke discovery agent -> DocumentMap
        3. Invoke project-extractor agent -> ProjectInfo + EnvelopeInfo
        4. If parallel=True: Invoke domain extractors in parallel (zones, windows, hvac, dhw)
        5. Merge into TakeoffSpec (orientation-based), then transform to BuildingSpec
        6. Return final state with both specs

    Args:
        eval_name: Evaluation case identifier (e.g., "chamberlin-circle")
        eval_dir: Path to evaluation directory
        parallel: If True, run multi-domain extraction in parallel (default: True)
        output_takeoff: If True, include TakeoffSpec in output (default: False)

    Returns:
        Final state dict with building_spec (and optionally takeoff_spec) or error

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

        # Find ALL subdirectories with page images and combine them
        all_page_images = []
        pdf_paths = []
        for subdir in sorted(preprocessed_base.iterdir()):
            if subdir.is_dir():
                subdir_pages = sorted(subdir.glob("page-*.png"))
                if subdir_pages:
                    all_page_images.extend(subdir_pages)
                    # Track matching PDF
                    pdf_path = eval_dir / f"{subdir.name}.pdf"
                    if pdf_path.exists():
                        pdf_paths.append(pdf_path)
                    logger.info(f"  Loaded {len(subdir_pages)} pages from {subdir.name}/")

        if not all_page_images:
            raise FileNotFoundError(f"No preprocessed images found in {preprocessed_base}")

        # Use first PDF for metadata (or find plans.pdf)
        pdf_path = None
        for p in pdf_paths:
            if p.name == "plans.pdf":
                pdf_path = p
                break
        if not pdf_path and pdf_paths:
            pdf_path = pdf_paths[0]

        # Renumber pages sequentially for consistent indexing
        page_images = all_page_images

        logger.info(f"Found {len(page_images)} preprocessed pages")

        # Step 1: Discovery phase
        document_map = run_discovery(page_images)

        # Step 2: Project extraction phase (always runs first)
        project_extraction = run_project_extraction(page_images, document_map)

        takeoff_spec = None

        if parallel:
            # Step 3: Parallel multi-domain extraction
            logger.info("Starting parallel multi-domain extraction")
            domain_extractions = asyncio.run(
                run_parallel_extraction(page_images, document_map)
            )

            # Step 4: Merge into TakeoffSpec (orientation-based)
            takeoff_spec, uncertainty_flags = merge_to_takeoff_spec(
                project_extraction,
                domain_extractions
            )

            # Step 5: Transform to BuildingSpec for verification
            building_spec = transform_takeoff_to_building_spec(takeoff_spec)

            # Also run legacy merge for conflict detection and extraction status
            _, conflicts, extraction_status = merge_extractions(
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
            logger.info(f"  Uncertainty flags: {len(uncertainty_flags)}")
        else:
            # Legacy mode: project extraction only
            building_spec = BuildingSpec(
                project=ProjectInfo.model_validate(project_extraction["project"]),
                envelope=EnvelopeInfo.model_validate(project_extraction["envelope"])
            )
            logger.info(f"Project-only extraction complete for {eval_name}")

        result = {
            "eval_name": eval_name,
            "pdf_path": str(pdf_path),
            "page_images": [str(p) for p in page_images],
            "document_map": document_map.model_dump(),
            "building_spec": building_spec.model_dump(),
            "error": None
        }

        # Optionally include TakeoffSpec in output
        if output_takeoff and takeoff_spec:
            result["takeoff_spec"] = takeoff_spec.model_dump()

        return result

    except Exception as e:
        logger.error(f"Extraction failed for {eval_name}: {e}")
        return {
            "eval_name": eval_name,
            "error": str(e),
            "building_spec": None
        }
