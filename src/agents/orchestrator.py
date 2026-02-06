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
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from schemas.discovery import DocumentMap, PDFSource, CACHE_VERSION
from cv_sensors import detect_north_arrow_angle, measure_wall_edge_angles
from cv_sensors.wall_detection import estimate_building_rotation
import numpy as np
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
EXTRACTION_SEMAPHORE = asyncio.Semaphore(4)

# Claude Read tool limit for PDF pages
MAX_PDF_PAGES_PER_READ = 20


def discover_source_pdfs(eval_dir: Path) -> Dict[str, PDFSource]:
    """
    Find all PDFs in eval directory and get page counts.

    Args:
        eval_dir: Path to evaluation directory

    Returns:
        Dict mapping PDF name (without extension) to PDFSource metadata
    """
    import fitz  # PyMuPDF

    source_pdfs = {}
    for pdf_path in sorted(eval_dir.glob("*.pdf")):
        # Skip original copies
        if "_original" in pdf_path.name:
            continue

        try:
            doc = fitz.open(pdf_path)
            pdf_name = pdf_path.stem  # filename without extension
            page_count = len(doc)
            source_pdfs[pdf_name] = PDFSource(
                filename=pdf_path.name,
                total_pages=page_count
            )
            doc.close()
            logger.debug(f"Found PDF: {pdf_path.name} ({page_count} pages)")
        except Exception as e:
            logger.warning(f"Failed to read PDF {pdf_path}: {e}")

    return source_pdfs


def _convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy types to native Python types for JSON serialization.

    Args:
        obj: Object potentially containing numpy types

    Returns:
        Object with all numpy types converted to Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_numpy_types(val) for key, val in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj


def run_cv_sensors(eval_dir: Path, document_map: DocumentMap) -> Dict[str, Any]:
    """
    Run CV sensors on site plan page to extract deterministic angle measurements.

    Args:
        eval_dir: Path to evaluation directory containing PDFs
        document_map: Document structure from discovery phase

    Returns:
        Dict with CV sensor results:
        {
            "north_arrow": {"angle": float, "confidence": str, "method": str},
            "wall_edges": [{"angle_from_horizontal": float, "length": float, ...}, ...],
            "building_rotation": {"rotation_from_horizontal": float, "confidence": str},
            "site_plan_page": int
        }
    """
    # Find best candidate site plan page
    relevant_pages = get_relevant_pages_for_domain("orientation", document_map)
    if not relevant_pages:
        relevant_pages = list(range(1, min(8, document_map.total_pages + 1)))

    # Prefer site plan pages
    site_plan_pages = [p for p in relevant_pages if p in document_map.site_plan_pages]
    if site_plan_pages:
        target_page = site_plan_pages[0]
    else:
        target_page = relevant_pages[0]

    # Find PDF path and local page number
    page_info = next(
        (p for p in document_map.pages if p.page_number == target_page),
        None
    )
    if not page_info:
        logger.warning(f"Page {target_page} not found in document map")
        return {
            "north_arrow": {"angle": None, "confidence": "none", "method": "none"},
            "wall_edges": [],
            "building_rotation": {"rotation_from_horizontal": None, "confidence": "none"},
            "site_plan_page": target_page
        }

    pdf_name = page_info.pdf_name
    local_page_num = page_info.pdf_page_number
    pdf_path = eval_dir / f"{pdf_name}.pdf"

    logger.info(f"Running CV sensors on {pdf_path} page {local_page_num} (global page {target_page})")

    # Run north arrow detection
    north_arrow = {"angle": None, "confidence": "none", "method": "none"}
    try:
        north_result = detect_north_arrow_angle(pdf_path, local_page_num)
        if north_result:
            north_arrow = _convert_numpy_types(north_result)
            logger.info(f"CV: North arrow detected at {north_arrow['angle']}° (confidence: {north_arrow['confidence']})")
    except Exception as e:
        logger.warning(f"CV: North arrow detection failed: {e}")

    # Run wall edge measurement
    wall_edges = []
    try:
        wall_result = measure_wall_edge_angles(pdf_path, local_page_num)
        if wall_result:
            wall_edges = _convert_numpy_types(wall_result)
            logger.info(f"CV: Detected {len(wall_edges)} wall edges")
    except Exception as e:
        logger.warning(f"CV: Wall edge measurement failed: {e}")

    # Run building rotation estimation
    building_rotation = {"rotation_from_horizontal": None, "confidence": "none"}
    try:
        rotation_result = estimate_building_rotation(pdf_path, local_page_num)
        if rotation_result:
            building_rotation = _convert_numpy_types(rotation_result)
            logger.info(f"CV: Building rotation {rotation_result['rotation_from_horizontal']}° (confidence: {rotation_result['confidence']})")
    except Exception as e:
        logger.warning(f"CV: Building rotation estimation failed: {e}")

    cv_hints = {
        "north_arrow": north_arrow,
        "wall_edges": wall_edges,
        "building_rotation": building_rotation,
        "site_plan_page": target_page
    }

    return cv_hints


def build_pdf_read_instructions(
    eval_dir: Path,
    page_numbers: List[int],
    document_map: DocumentMap
) -> str:
    """
    Build instructions for reading specific PDF pages.

    Groups pages by source PDF and formats Read tool instructions.
    Converts global page numbers to per-PDF page numbers for the Read tool.

    Args:
        eval_dir: Path to evaluation directory
        page_numbers: List of global 1-indexed page numbers to read
        document_map: Document map with pdf_name and pdf_page_number per page

    Returns:
        Formatted string with Read tool instructions
    """
    # Group pages by PDF, using pdf_page_number for the actual Read call
    pages_by_pdf: Dict[str, List[int]] = {}
    for page_num in page_numbers:
        # Find the page info to get pdf_name and pdf_page_number
        page_info = next(
            (p for p in document_map.pages if p.page_number == page_num),
            None
        )
        if page_info:
            pdf_name = page_info.pdf_name
            # Use pdf_page_number for the Read tool (local page within PDF)
            local_page = page_info.pdf_page_number
        else:
            # Fallback for legacy cache without pdf_page_number
            pdf_name = "plans"
            local_page = page_num

        if pdf_name not in pages_by_pdf:
            pages_by_pdf[pdf_name] = []
        pages_by_pdf[pdf_name].append(local_page)

    # Build instructions
    lines = ["Read these PDF pages using the Read tool:"]
    for pdf_name, pages in sorted(pages_by_pdf.items()):
        pdf_path = eval_dir / f"{pdf_name}.pdf"
        pages_str = ", ".join(str(p) for p in sorted(pages))
        lines.append(f"- {pdf_path} pages {pages_str}")

    # Add example
    first_pdf = list(pages_by_pdf.keys())[0]
    first_pages = pages_by_pdf[first_pdf]
    example_path = eval_dir / f"{first_pdf}.pdf"
    example_pages = ",".join(str(p) for p in sorted(first_pages)[:3])
    lines.append("")
    lines.append(f'Example: Read(file_path="{example_path}", pages="{example_pages}")')

    return "\n".join(lines)


def get_relevant_pages_for_domain(domain: str, document_map: DocumentMap) -> List[int]:
    """
    Select relevant pages for a specific extraction domain using intelligent routing.

    Uses subtypes and content tags when available, with fallback to coarse page types
    for backwards compatibility with older discovery cache formats.

    Args:
        domain: Domain name (orientation, zones, windows, hvac, dhw, project)
        document_map: Document structure from discovery phase

    Returns:
        Sorted list of relevant page numbers
    """
    relevant = set()

    if domain == "orientation":
        # Priority: site plans with north arrow, then floor plans/elevations
        relevant.update(document_map.site_plan_pages)
        relevant.update(document_map.floor_plan_pages)
        relevant.update(document_map.elevation_pages)
        relevant.update(document_map.pages_with_tag("north_arrow"))

    elif domain == "zones":
        # Need floor plans for room layout, sections for heights, energy summary
        relevant.update(document_map.floor_plan_pages)
        relevant.update(document_map.section_pages)
        relevant.update(document_map.detail_pages)  # Wall assemblies
        relevant.update(document_map.energy_summary_pages)
        relevant.update(document_map.room_schedule_pages)
        relevant.update(document_map.wall_schedule_pages)
        relevant.update(document_map.pages_with_any_tag([
            "room_labels", "area_callouts", "ceiling_heights",
            "wall_assembly", "insulation_values"
        ]))

    elif domain == "windows":
        # Window schedules are primary, elevations show placement
        relevant.update(document_map.window_schedule_pages)
        relevant.update(document_map.elevation_pages)
        relevant.update(document_map.floor_plan_pages)
        relevant.update(document_map.energy_summary_pages)
        relevant.update(document_map.pages_with_any_tag([
            "glazing_performance", "window_callouts"
        ]))

    elif domain == "hvac":
        # Equipment schedules are primary, mechanical plans show layout
        relevant.update(document_map.equipment_schedule_pages)
        relevant.update(document_map.mechanical_plan_pages)
        relevant.update(document_map.energy_summary_pages)
        relevant.update(document_map.pages_with_any_tag([
            "hvac_equipment", "hvac_specs"
        ]))

    elif domain == "dhw":
        # Equipment schedules and plumbing plans
        relevant.update(document_map.equipment_schedule_pages)
        relevant.update(document_map.plumbing_plan_pages)
        relevant.update(document_map.energy_summary_pages)
        relevant.update(document_map.pages_with_any_tag([
            "water_heater", "dhw_specs"
        ]))

    elif domain == "project":
        # Project info comes from schedules, CBECC, and first few drawings
        relevant.update(document_map.schedule_pages)
        relevant.update(document_map.cbecc_pages)
        relevant.update(document_map.energy_summary_pages)
        # Include site plan and floor plan for project context
        relevant.update(document_map.site_plan_pages)
        relevant.update(document_map.floor_plan_pages[:3] if document_map.floor_plan_pages else [])

    # Fallback for old cache format (no subtypes/tags populated)
    if not relevant:
        logger.debug(f"No subtype/tag matches for {domain}, using fallback routing")
        # Legacy routing based on coarse page types
        if domain in ("hvac", "dhw"):
            # Original behavior: schedules + CBECC only
            relevant.update(document_map.schedule_pages)
            relevant.update(document_map.cbecc_pages)
        elif domain in ("windows", "zones"):
            # Original behavior: schedules + CBECC + all drawings
            relevant.update(document_map.schedule_pages)
            relevant.update(document_map.cbecc_pages)
            relevant.update(document_map.drawing_pages)
        elif domain == "orientation":
            # Original behavior: first 7 drawing pages
            relevant.update(document_map.drawing_pages[:7] if document_map.drawing_pages else [])
        elif domain == "project":
            # Original behavior: schedules + CBECC + first 5 drawings
            relevant.update(document_map.schedule_pages)
            relevant.update(document_map.cbecc_pages)
            relevant.update(document_map.drawing_pages[:5] if document_map.drawing_pages else [])

    return sorted(relevant)


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


def run_discovery(eval_dir: Path, source_pdfs: Optional[Dict[str, PDFSource]] = None) -> DocumentMap:
    """
    Run discovery agent to classify document pages from PDFs.

    Args:
        eval_dir: Path to evaluation directory containing PDFs
        source_pdfs: Optional pre-discovered PDF metadata

    Returns:
        DocumentMap with classified pages

    Raises:
        RuntimeError: If discovery agent fails
    """
    # Discover PDFs if not provided
    if source_pdfs is None:
        source_pdfs = discover_source_pdfs(eval_dir)

    if not source_pdfs:
        raise RuntimeError(f"No PDFs found in {eval_dir}")

    # Calculate total pages
    total_pages = sum(pdf.total_pages for pdf in source_pdfs.values())
    logger.info(f"Running discovery on {total_pages} pages from {len(source_pdfs)} PDFs")

    # Build prompt with PDF paths and page ranges
    pdf_list_lines = []
    for pdf_name, pdf_info in sorted(source_pdfs.items()):
        pdf_path = eval_dir / pdf_info.filename
        pdf_list_lines.append(f"- {pdf_path} ({pdf_info.total_pages} pages)")

    pdf_list = "\n".join(pdf_list_lines)

    # Build page reading instructions (for each PDF)
    read_instructions = []
    for pdf_name, pdf_info in sorted(source_pdfs.items()):
        pdf_path = eval_dir / pdf_info.filename
        if pdf_info.total_pages <= MAX_PDF_PAGES_PER_READ:
            pages_range = f"1-{pdf_info.total_pages}"
            read_instructions.append(f'Read(file_path="{pdf_path}", pages="{pages_range}")')
        else:
            # Batch into multiple reads
            for start in range(1, pdf_info.total_pages + 1, MAX_PDF_PAGES_PER_READ):
                end = min(start + MAX_PDF_PAGES_PER_READ - 1, pdf_info.total_pages)
                read_instructions.append(f'Read(file_path="{pdf_path}", pages="{start}-{end}")')

    read_example = read_instructions[0] if read_instructions else ""

    # Calculate global page number offsets for each PDF
    pdf_offsets = {}
    offset = 0
    for pdf_name in sorted(source_pdfs.keys()):
        pdf_offsets[pdf_name] = offset
        offset += source_pdfs[pdf_name].total_pages

    offset_info = "\n".join([
        f"  - {name}: pages {pdf_offsets[name]+1}-{pdf_offsets[name]+source_pdfs[name].total_pages} (global), 1-{source_pdfs[name].total_pages} (local)"
        for name in sorted(source_pdfs.keys())
    ])

    prompt = f"""Classify the pages in this Title 24 document.

Source PDFs:
{pdf_list}

Global page numbering (for routing):
{offset_info}

Read each PDF using the Read tool with the pages parameter. Example:
{read_example}

Read your instructions from .claude/instructions/discovery/instructions.md, then analyze each page and return a DocumentMap JSON with the structure:

{{
  "total_pages": {total_pages},
  "source_pdfs": {{
    "plans": {{"filename": "plans.pdf", "total_pages": 10}},
    ...
  }},
  "pages": [
    {{
      "page_number": 1,
      "pdf_name": "plans",
      "pdf_page_number": 1,
      "page_type": "schedule|cbecc|drawing|other",
      "confidence": "high|medium|low",
      "description": "brief description"
    }},
    ...
  ]
}}

IMPORTANT - PAGE NUMBERING:
- `page_number`: GLOBAL unique number across all PDFs (plans pages 1-10, then spec_sheet pages 11-12, etc.)
- `pdf_name`: Which PDF this page is from (e.g., "plans", "spec_sheet")
- `pdf_page_number`: LOCAL page number within that PDF (for the Read tool)
- Example: If plans.pdf has 10 pages and spec_sheet.pdf has 2 pages:
  - plans.pdf page 1 → page_number=1, pdf_page_number=1
  - plans.pdf page 10 → page_number=10, pdf_page_number=10
  - spec_sheet.pdf page 1 → page_number=11, pdf_page_number=1
  - spec_sheet.pdf page 2 → page_number=12, pdf_page_number=2
- Ensure all pages from all PDFs are classified
"""

    # Invoke discovery agent
    response = invoke_claude_agent("discovery", prompt, timeout=600)

    # Parse response
    try:
        json_data = extract_json_from_response(response)

        # Ensure source_pdfs is included
        if "source_pdfs" not in json_data:
            json_data["source_pdfs"] = {
                name: {"filename": info.filename, "total_pages": info.total_pages}
                for name, info in source_pdfs.items()
            }

        # Ensure cache_version is set
        json_data["cache_version"] = CACHE_VERSION

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


def run_orientation_extraction(
    eval_dir: Path,
    document_map: DocumentMap
) -> Dict[str, Any]:
    """
    Run orientation-extractor agent to extract building front orientation.

    Uses intelligent routing to select site plans, floor plans, and elevations
    (pages with north arrows).

    Args:
        eval_dir: Path to evaluation directory containing PDFs
        document_map: Document structure from discovery phase

    Returns:
        Dict with orientation data including front_orientation, confidence, etc.

    Raises:
        RuntimeError: If extraction agent fails
    """
    # Use intelligent routing for orientation-relevant pages
    relevant_page_numbers = get_relevant_pages_for_domain("orientation", document_map)

    # If no pages found via routing, fall back to first few pages
    if not relevant_page_numbers:
        relevant_page_numbers = list(range(1, min(6, document_map.total_pages + 1)))

    logger.info(f"Running orientation extraction on pages: {relevant_page_numbers}")

    # Run CV sensors first
    cv_hints = None
    try:
        cv_hints = run_cv_sensors(eval_dir, document_map)
    except Exception as e:
        logger.warning(f"CV sensors failed, proceeding without hints: {e}")

    # Build PDF read instructions
    pdf_instructions = build_pdf_read_instructions(eval_dir, relevant_page_numbers, document_map)

    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    # Inject CV hints if available
    cv_section = ""
    if cv_hints:
        cv_section = f"""
CV SENSOR MEASUREMENTS (deterministic, from computer vision):
{json.dumps(cv_hints, indent=2)}

These measurements are precise and repeatable. Use them as described in your instructions.

"""

    prompt = f"""Extract building orientation from this Title 24 document.

{cv_section}Document structure (from discovery):
{document_map_json}

{pdf_instructions}

Read your instructions from:
- .claude/instructions/orientation-extractor/instructions.md

Then analyze the provided pages and return JSON with this structure:

{{
  "front_orientation": 0.0,
  "north_arrow_found": true,
  "north_arrow_page": null,
  "front_direction": "N",
  "confidence": "high",
  "reasoning": "Explanation of how orientation was determined",
  "notes": "Additional context"
}}

Focus on:
1. Finding the north arrow on site plan or floor plan
2. Determining which side of the building is the "front" (faces street)
3. Calculating the angle from true north to the front direction
"""

    # Invoke orientation-extractor agent
    try:
        response = invoke_claude_agent("orientation-extractor", prompt, timeout=300)
        json_data = extract_json_from_response(response)

        front_orientation = json_data.get("front_orientation", 0.0)
        confidence = json_data.get("confidence", "low")

        logger.info(f"Orientation extraction complete:")
        logger.info(f"  Front orientation: {front_orientation} degrees")
        logger.info(f"  North arrow found: {json_data.get('north_arrow_found', False)}")
        logger.info(f"  Confidence: {confidence}")

        return json_data

    except Exception as e:
        logger.warning(f"Orientation extraction failed: {e}, using default orientation")
        return {
            "front_orientation": 0.0,
            "north_arrow_found": False,
            "north_arrow_page": None,
            "front_direction": "N",
            "confidence": "low",
            "reasoning": f"Orientation extraction failed: {e}. Using default north-facing orientation.",
            "notes": "Default orientation used due to extraction failure."
        }


def angular_distance(a: float, b: float) -> float:
    """Calculate minimum angular distance between two angles."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


async def run_orientation_pass_async(
    eval_dir: Path,
    document_map: DocumentMap,
    pass_num: int,
    cv_hints: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Run a single orientation extraction pass asynchronously.

    Args:
        eval_dir: Path to evaluation directory
        document_map: Document structure from discovery
        pass_num: 1 for north-arrow pass, 2 for elevation-matching pass
        cv_hints: Optional CV sensor measurements to inject into prompt

    Returns:
        Dict with pass results including orientation and confidence
    """
    relevant_pages = get_relevant_pages_for_domain("orientation", document_map)
    if not relevant_pages:
        relevant_pages = list(range(1, min(8, document_map.total_pages + 1)))

    pdf_instructions = build_pdf_read_instructions(eval_dir, relevant_pages, document_map)
    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    instruction_file = (
        ".claude/instructions/orientation-extractor/pass1-north-arrow.md"
        if pass_num == 1
        else ".claude/instructions/orientation-extractor/pass2-elevation-matching.md"
    )

    # Inject CV hints if provided
    cv_section = ""
    if cv_hints:
        cv_section = f"""
CV SENSOR MEASUREMENTS (deterministic, from computer vision):
{json.dumps(cv_hints, indent=2)}

These measurements are precise and repeatable. Use them as described in your instructions.

"""

    prompt = f"""Extract building orientation using the Pass {pass_num} method.

{cv_section}Document structure:
{document_map_json}

{pdf_instructions}

Read your instructions from: {instruction_file}

Then analyze the pages and return JSON matching the schema in the instructions.
Focus on outputting the structured intermediate values, not just the final answer.
"""

    try:
        response = await invoke_claude_agent_async("orientation-extractor", prompt, timeout=300)
        json_data = extract_json_from_response(response)

        return {
            "pass": pass_num,
            "status": "success",
            "orientation": json_data.get("front_orientation", 0),
            "confidence": json_data.get("confidence", "unknown"),
            "north_arrow_angle": json_data.get("north_arrow", {}).get("angle"),
            "full_response": json_data,
        }
    except Exception as e:
        logger.warning(f"Orientation pass {pass_num} failed: {e}")
        return {
            "pass": pass_num,
            "status": "error",
            "error": str(e)
        }


def verify_orientation_passes(pass1: Dict, pass2: Dict) -> Dict[str, Any]:
    """
    Compare two orientation pass results and determine final orientation.

    Returns dict with:
        - final_orientation: The determined orientation (or None if both failed)
        - confidence: high/medium/low based on agreement
        - verification: Type of verification result
        - notes: Explanation of the verification
    """
    if pass1["status"] != "success" and pass2["status"] != "success":
        return {
            "final_orientation": 0.0,
            "confidence": "low",
            "verification": "both_failed",
            "notes": "Both passes failed, using default orientation"
        }

    if pass1["status"] != "success":
        return {
            "final_orientation": pass2["orientation"],
            "confidence": pass2["confidence"],
            "verification": "pass1_failed",
            "notes": "Only Pass 2 succeeded"
        }

    if pass2["status"] != "success":
        return {
            "final_orientation": pass1["orientation"],
            "confidence": pass1["confidence"],
            "verification": "pass2_failed",
            "notes": "Only Pass 1 succeeded"
        }

    # Both succeeded - compare results
    o1 = pass1["orientation"]
    o2 = pass2["orientation"]
    diff = angular_distance(o1, o2)

    if diff <= 20:
        # Agreement - average them
        avg = (o1 + o2) / 2
        if abs(o1 - o2) > 180:
            avg = (avg + 180) % 360
        return {
            "final_orientation": round(avg, 1),
            "confidence": "high",
            "verification": "agreement",
            "notes": f"Passes agree within {diff:.1f}°",
            "pass1_orientation": o1,
            "pass2_orientation": o2,
        }

    # Use confidence to decide which pass to trust
    conf_rank = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    c1 = conf_rank.get(pass1.get("confidence", "unknown"), 0)
    c2 = conf_rank.get(pass2.get("confidence", "unknown"), 0)
    chosen = o1 if c1 >= c2 else o2
    chosen_pass = "Pass 1" if c1 >= c2 else "Pass 2"

    if 70 <= diff <= 110:
        return {
            "final_orientation": chosen,
            "confidence": "low",
            "verification": "side_front_confusion",
            "notes": f"90° difference ({diff:.1f}°) - trusting {chosen_pass} (higher confidence)",
            "pass1_orientation": o1,
            "pass2_orientation": o2,
        }

    if 160 <= diff <= 200:
        return {
            "final_orientation": chosen,
            "confidence": "low",
            "verification": "front_back_confusion",
            "notes": f"180° difference ({diff:.1f}°) - trusting {chosen_pass} (higher confidence)",
            "pass1_orientation": o1,
            "pass2_orientation": o2,
        }

    return {
        "final_orientation": chosen,
        "confidence": "low",
        "verification": "disagreement",
        "notes": f"Passes disagree by {diff:.1f}° - trusting {chosen_pass} (higher confidence)",
        "pass1_orientation": o1,
        "pass2_orientation": o2,
    }


async def run_orientation_twopass_async(
    eval_dir: Path,
    document_map: DocumentMap
) -> Dict[str, Any]:
    """
    Run two-pass orientation extraction with verification.

    Runs both passes in parallel, then compares results to catch
    systematic errors (90° side/front, 180° front/back confusion).

    Args:
        eval_dir: Path to evaluation directory
        document_map: Document structure from discovery

    Returns:
        Dict with orientation data including verification metadata
    """
    logger.info("Running two-pass orientation extraction...")

    # Run CV sensors first
    cv_hints = None
    try:
        cv_hints = run_cv_sensors(eval_dir, document_map)
    except Exception as e:
        logger.warning(f"CV sensors failed, proceeding without hints: {e}")

    # Run both passes in parallel with CV hints
    pass1_task = run_orientation_pass_async(eval_dir, document_map, 1, cv_hints)
    pass2_task = run_orientation_pass_async(eval_dir, document_map, 2, cv_hints)
    pass1, pass2 = await asyncio.gather(pass1_task, pass2_task)

    # Verify and combine results
    verification = verify_orientation_passes(pass1, pass2)

    logger.info(f"Orientation two-pass complete:")
    logger.info(f"  Pass 1: {pass1.get('orientation', 'failed')}°")
    logger.info(f"  Pass 2: {pass2.get('orientation', 'failed')}°")
    logger.info(f"  Final: {verification['final_orientation']}° ({verification['verification']})")
    logger.info(f"  Confidence: {verification['confidence']}")

    return {
        "front_orientation": verification["final_orientation"],
        "confidence": verification["confidence"],
        "verification": verification["verification"],
        "reasoning": verification["notes"],
        "north_arrow_found": pass1.get("full_response", {}).get("north_arrow", {}).get("found", False),
        "north_arrow_page": pass1.get("full_response", {}).get("north_arrow", {}).get("page"),
        "front_direction": _azimuth_to_direction(verification["final_orientation"]),
        "pass1": pass1,
        "pass2": pass2,
        "cv_hints": cv_hints,
        "notes": verification["notes"]
    }


def _azimuth_to_direction(azimuth: float) -> str:
    """Convert azimuth to compass direction string."""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((azimuth + 11.25) / 22.5) % 16
    return directions[idx]


def run_orientation_twopass(
    eval_dir: Path,
    document_map: DocumentMap
) -> Dict[str, Any]:
    """
    Synchronous wrapper for two-pass orientation extraction.

    Args:
        eval_dir: Path to evaluation directory
        document_map: Document structure from discovery

    Returns:
        Dict with orientation data including verification metadata
    """
    return asyncio.run(run_orientation_twopass_async(eval_dir, document_map))


def run_project_extraction(
    eval_dir: Path,
    document_map: DocumentMap,
    orientation_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run project-extractor agent to extract building specifications.

    Uses intelligent routing to select relevant pages based on subtypes and tags.

    Args:
        eval_dir: Path to evaluation directory containing PDFs
        document_map: Document structure from discovery phase
        orientation_data: Optional orientation data from orientation-extractor

    Returns:
        Dict with 'project' and 'envelope' keys containing extracted data

    Raises:
        RuntimeError: If extraction agent fails
        ValueError: If no relevant pages found
    """
    # Use intelligent routing for project-relevant pages
    relevant_page_numbers = get_relevant_pages_for_domain("project", document_map)

    if not relevant_page_numbers:
        raise ValueError("No relevant pages found for project extraction")

    logger.info(f"Project extraction using {len(relevant_page_numbers)} relevant pages: {relevant_page_numbers}")

    # Build PDF read instructions
    pdf_instructions = build_pdf_read_instructions(eval_dir, relevant_page_numbers, document_map)

    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    prompt = f"""Extract building specifications from this Title 24 document.

Document structure (from discovery):
{document_map_json}

{pdf_instructions}

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
        wwr = f"{envelope.window_to_floor_ratio:.2%}" if envelope.window_to_floor_ratio else "N/A"
        logger.info(f"  WWR: {wwr}")

        result = {
            "project": project.model_dump(),
            "envelope": envelope.model_dump(),
            "notes": json_data.get("notes", "")
        }

        # Include orientation data if provided
        if orientation_data:
            result["project"]["front_orientation"] = orientation_data.get("front_orientation")
            result["project"]["orientation_confidence"] = orientation_data.get("confidence")
            result["project"]["orientation_verification"] = orientation_data.get("verification")
            result["orientation_data"] = orientation_data

        return result

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
    eval_dir: Path,
    document_map: DocumentMap,
    orientation_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build extraction prompt for a specific domain.

    Uses intelligent page routing based on subtypes and content tags
    when available, with automatic fallback for older cache formats.

    Args:
        domain: Domain name (zones, windows, hvac, dhw)
        eval_dir: Path to evaluation directory containing PDFs
        document_map: Document structure from discovery
        orientation_data: Optional orientation data from orientation-extractor

    Returns:
        Formatted prompt string for the extractor agent
    """
    # Use intelligent routing to select relevant pages
    relevant_pages = get_relevant_pages_for_domain(domain, document_map)

    logger.info(f"Routing {domain}: {len(relevant_pages)} pages selected: {relevant_pages}")

    # Build PDF read instructions
    pdf_instructions = build_pdf_read_instructions(eval_dir, relevant_pages, document_map)

    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    # Build orientation context for zones and windows extractors
    orientation_context = ""
    if orientation_data and domain in ("zones", "windows"):
        front_orientation = orientation_data.get("front_orientation", 0.0)
        confidence = orientation_data.get("confidence", "low")
        reasoning = orientation_data.get("reasoning", "")

        # Calculate wall azimuths from front orientation
        # Convention based on CBECC output format:
        # - "east" key (E Wall) = front of building
        # - "west" key (W Wall) = back of building
        # - "north" key (N Wall) = left side (90 CCW from front)
        # - "south" key (S Wall) = right side (90 CW from front)
        east_azimuth = front_orientation  # Front faces this direction
        west_azimuth = (front_orientation + 180) % 360
        north_azimuth = (front_orientation - 90 + 360) % 360
        south_azimuth = (front_orientation + 90) % 360

        orientation_context = f"""
BUILDING ORIENTATION (from orientation-extractor, confidence: {confidence}):
- Front orientation: {front_orientation} degrees from true north
- Reasoning: {reasoning}

CRITICAL - USE THESE EXACT AZIMUTHS FOR EACH WALL:
- "north" key (N Wall): azimuth = {north_azimuth} degrees
- "east" key (E Wall): azimuth = {east_azimuth} degrees (this is the FRONT)
- "south" key (S Wall): azimuth = {south_azimuth} degrees
- "west" key (W Wall): azimuth = {west_azimuth} degrees (this is the BACK)

DO NOT use cardinal azimuths (0, 90, 180, 270). The building is rotated.
Copy the exact azimuth values above into your JSON output.
"""

    return f"""Extract {domain} data from this Title 24 document.

Document structure (from discovery):
{document_map_json}
{orientation_context}
{pdf_instructions}

Read your instructions from:
- .claude/instructions/{domain}-extractor/instructions.md
- .claude/instructions/{domain}-extractor/field-guide.md

Return JSON matching the schema for {domain} extraction.
Focus on accuracy and completeness.
"""


async def run_parallel_extraction(
    eval_dir: Path,
    document_map: DocumentMap,
    orientation_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Tuple[Optional[Dict[str, Any]], ExtractionStatus]]:
    """
    Run all domain extractors in parallel using asyncio.

    Args:
        eval_dir: Path to evaluation directory containing PDFs
        document_map: Document structure from discovery
        orientation_data: Optional orientation data from orientation-extractor

    Returns:
        Dict mapping domain name to (data, status) tuple
    """
    logger.info("Starting parallel extraction for zones, windows, hvac, dhw")

    # Build prompts for each domain (zones and windows get orientation context)
    zones_prompt = build_domain_prompt("zones", eval_dir, document_map, orientation_data)
    windows_prompt = build_domain_prompt("windows", eval_dir, document_map, orientation_data)
    hvac_prompt = build_domain_prompt("hvac", eval_dir, document_map)
    dhw_prompt = build_domain_prompt("dhw", eval_dir, document_map)

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
        orientation_confidence=proj_dict.get("orientation_confidence"),
        orientation_verification=proj_dict.get("orientation_verification"),
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
        1. Discover source PDFs in eval directory
        2. Invoke discovery agent -> DocumentMap
        3. Invoke orientation-extractor agent -> front_orientation
        4. Invoke project-extractor agent -> ProjectInfo + EnvelopeInfo
        5. If parallel=True: Invoke domain extractors in parallel (zones, windows, hvac, dhw)
        6. Merge into TakeoffSpec (orientation-based), then transform to BuildingSpec
        7. Return final state with both specs

    Args:
        eval_name: Evaluation case identifier (e.g., "chamberlin-circle")
        eval_dir: Path to evaluation directory
        parallel: If True, run multi-domain extraction in parallel (default: True)
        output_takeoff: If True, include TakeoffSpec in output (default: False)

    Returns:
        Final state dict with building_spec (and optionally takeoff_spec) or error

    Raises:
        FileNotFoundError: If no PDFs found in eval directory
        RuntimeError: If workflow execution fails
    """
    logger.info(f"Starting extraction for {eval_name} (parallel={parallel})")
    pipeline_start = time.monotonic()
    timing = {}

    try:
        # Step 0: Discover source PDFs
        t0 = time.monotonic()
        source_pdfs = discover_source_pdfs(eval_dir)
        timing["discover_pdfs"] = round(time.monotonic() - t0, 3)
        if not source_pdfs:
            raise FileNotFoundError(f"No PDFs found in {eval_dir}")

        total_pages = sum(pdf.total_pages for pdf in source_pdfs.values())
        logger.info(f"Found {len(source_pdfs)} PDFs with {total_pages} total pages")
        for name, info in source_pdfs.items():
            logger.info(f"  {info.filename}: {info.total_pages} pages")

        # Use plans.pdf as primary if available
        pdf_path = eval_dir / "plans.pdf"
        if not pdf_path.exists():
            # Fall back to first PDF
            first_pdf = list(source_pdfs.values())[0]
            pdf_path = eval_dir / first_pdf.filename

        # Step 1: Discovery phase (with caching)
        t0 = time.monotonic()
        cache_dir = eval_dir.parent / ".cache"
        cache_file = cache_dir / f"{eval_name}_discovery.json"
        if cache_file.exists():
            try:
                with open(cache_file) as cf:
                    cache_data = json.load(cf)
                if cache_data.get("cache_version", 1) >= CACHE_VERSION:
                    document_map = DocumentMap.model_validate(cache_data)
                    logger.info(f"Using cached discovery for {eval_name}")
                else:
                    document_map = run_discovery(eval_dir, source_pdfs)
            except Exception:
                document_map = run_discovery(eval_dir, source_pdfs)
        else:
            document_map = run_discovery(eval_dir, source_pdfs)
        # Save cache
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as cf:
            json.dump(document_map.model_dump(), cf, indent=2)
        timing["discovery"] = round(time.monotonic() - t0, 1)

        # Step 2: Orientation + Project extraction in parallel
        # These are independent — project doesn't need orientation data
        t0 = time.monotonic()

        async def _run_orientation_and_project():
            t_orient = time.monotonic()
            t_project = time.monotonic()

            async def _orientation():
                nonlocal t_orient
                result = await run_orientation_twopass_async(eval_dir, document_map)
                timing["orientation"] = round(time.monotonic() - t_orient, 1)
                return result

            async def _project():
                nonlocal t_project
                result = await asyncio.to_thread(
                    run_project_extraction, eval_dir, document_map
                )
                timing["project"] = round(time.monotonic() - t_project, 1)
                return result

            return await asyncio.gather(_orientation(), _project())

        orientation_data, project_extraction = asyncio.run(
            _run_orientation_and_project()
        )

        takeoff_spec = None

        if parallel:
            # Step 4: Parallel multi-domain extraction (with orientation context)
            logger.info("Starting parallel multi-domain extraction")
            t0 = time.monotonic()
            domain_extractions = asyncio.run(
                run_parallel_extraction(eval_dir, document_map, orientation_data)
            )
            timing["parallel_extraction"] = round(time.monotonic() - t0, 1)

            # Step 5: Merge into TakeoffSpec (orientation-based)
            t0 = time.monotonic()
            takeoff_spec, uncertainty_flags = merge_to_takeoff_spec(
                project_extraction,
                domain_extractions
            )

            # Step 6: Transform to BuildingSpec for verification
            building_spec = transform_takeoff_to_building_spec(takeoff_spec)

            # Also run legacy merge for conflict detection and extraction status
            _, conflicts, extraction_status = merge_extractions(
                project_extraction,
                domain_extractions
            )
            timing["merge_transform"] = round(time.monotonic() - t0, 3)

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
            if orientation_data:
                logger.info(f"  Front orientation: {orientation_data.get('front_orientation')} degrees")
        else:
            # Legacy mode: project extraction only
            building_spec = BuildingSpec(
                project=ProjectInfo.model_validate(project_extraction["project"]),
                envelope=EnvelopeInfo.model_validate(project_extraction["envelope"])
            )
            logger.info(f"Project-only extraction complete for {eval_name}")

        timing["total"] = round(time.monotonic() - pipeline_start, 1)

        # Log timing summary
        logger.info(f"Pipeline timing for {eval_name}:")
        for stage, duration in timing.items():
            logger.info(f"  {stage}: {duration}s")

        result = {
            "eval_name": eval_name,
            "pdf_path": str(pdf_path),
            "source_pdfs": {name: info.model_dump() for name, info in source_pdfs.items()},
            "document_map": document_map.model_dump(),
            "building_spec": building_spec.model_dump(),
            "timing": timing,
            "error": None
        }

        # Optionally include TakeoffSpec in output
        if output_takeoff and takeoff_spec:
            result["takeoff_spec"] = takeoff_spec.model_dump()

        return result

    except Exception as e:
        timing["total"] = round(time.monotonic() - pipeline_start, 1)
        logger.error(f"Extraction failed for {eval_name}: {e}")
        return {
            "eval_name": eval_name,
            "error": str(e),
            "building_spec": None,
            "timing": timing
        }
