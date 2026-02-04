"""Orchestrator - Sequential extraction pipeline using Claude Code agents.

Claude Code Agent Invocation Pattern:
    When running outside Claude Code context (from CLI), invoke agents via:
    claude --agent <name> --print --no-interactive "<prompt>"

    This delegates execution to Claude Code's agent runtime instead of
    making direct Anthropic API calls.
"""
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from schemas.discovery import DocumentMap
from schemas.building_spec import BuildingSpec, ProjectInfo, EnvelopeInfo

logger = logging.getLogger(__name__)


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
        "--print",  # Output response to stdout
        "--no-interactive",
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


def run_extraction(eval_name: str, eval_dir: Path) -> dict:
    """
    Run extraction workflow on an evaluation case.

    Workflow:
        1. Find preprocessed page images
        2. Invoke discovery agent -> DocumentMap
        3. Filter to relevant pages (schedule + CBECC)
        4. Invoke project-extractor agent -> ProjectInfo + EnvelopeInfo
        5. Merge into BuildingSpec
        6. Return final state

    Args:
        eval_name: Evaluation case identifier (e.g., "chamberlin-circle")
        eval_dir: Path to evaluation directory

    Returns:
        Final state dict with building_spec or error

    Raises:
        FileNotFoundError: If preprocessed images or PDF not found
        RuntimeError: If workflow execution fails
    """
    logger.info(f"Starting extraction for {eval_name}")

    try:
        # Find PDF in eval directory
        pdf_files = list(eval_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF found in {eval_dir}")
        pdf_path = pdf_files[0]

        # Find preprocessed images
        pdf_stem = pdf_path.stem
        preprocessed_dir = eval_dir / "preprocessed" / pdf_stem

        if not preprocessed_dir.exists():
            raise FileNotFoundError(f"Preprocessed directory not found: {preprocessed_dir}")

        # Get all page images
        page_images = sorted(preprocessed_dir.glob("page-*.png"))
        if not page_images:
            raise FileNotFoundError(f"No preprocessed images found in {preprocessed_dir}")

        logger.info(f"Found {len(page_images)} preprocessed pages")

        # Step 1: Discovery phase
        document_map = run_discovery(page_images)

        # Step 2: Project extraction phase
        extraction = run_project_extraction(page_images, document_map)

        # Step 3: Merge into BuildingSpec
        building_spec = BuildingSpec(
            project=ProjectInfo.model_validate(extraction["project"]),
            envelope=EnvelopeInfo.model_validate(extraction["envelope"])
        )

        logger.info(f"Extraction complete for {eval_name}")

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
