"""Project extractor agent - Extract ProjectInfo and EnvelopeInfo."""
import logging
from pathlib import Path
from typing import List
from pydantic import BaseModel
from anthropic import Anthropic
from schemas.building_spec import ProjectInfo, EnvelopeInfo
from schemas.discovery import DocumentMap
from agents.extractors.base import retry_with_backoff, load_instructions

logger = logging.getLogger(__name__)


class ProjectExtraction(BaseModel):
    """Combined schema for project and envelope extraction."""
    project: ProjectInfo
    envelope: EnvelopeInfo
    notes: str = ""


@retry_with_backoff(max_retries=3)
def run_project_extractor(
    page_images: List[Path],
    document_map: DocumentMap,
    instructions_dir: Path
) -> ProjectExtraction:
    """
    Extract project metadata and envelope characteristics from Title 24 document.

    Args:
        page_images: List of all page image paths (preprocessed)
        document_map: Document structure from discovery phase
        instructions_dir: Path to project-extractor instructions directory

    Returns:
        ProjectExtraction with project and envelope data

    Raises:
        ValueError: If no relevant pages found for extraction
        RuntimeError: If API call fails after retries
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

    # Load instructions and field guide
    instructions = load_instructions(
        instructions_dir,
        "instructions.md",
        "field-guide.md"
    )

    # Create Anthropic client
    client = Anthropic()

    # Build content array: images + extraction prompt
    content = []

    # Add page images
    for i, page_path in enumerate(relevant_images, start=1):
        with open(page_path, "rb") as f:
            file = client.files.create(file=f, purpose="vision")

        # Add page label
        page_num = sorted(relevant_page_numbers)[i - 1]
        content.append({
            "type": "text",
            "text": f"--- Page {page_num} ---"
        })

        # Add image
        content.append({
            "type": "file",
            "file_id": file.id
        })

    # Add extraction prompt
    content.append({
        "type": "text",
        "text": f"{instructions}\n\nExtract ProjectInfo and EnvelopeInfo from the provided pages. Return complete JSON with both 'project' and 'envelope' objects, plus 'notes' field describing confidence and sources."
    })

    # Call API with structured output
    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "project_extraction",
                "schema": ProjectExtraction.model_json_schema()
            }
        }
    )

    # Parse response
    extraction = ProjectExtraction.model_validate_json(response.content[0].text)

    # Log extraction summary
    logger.info(f"Extracted project: {extraction.project.run_title}")
    logger.info(f"  Address: {extraction.project.address}, {extraction.project.city}")
    logger.info(f"  Climate zone: {extraction.project.climate_zone}")
    logger.info(f"  CFA: {extraction.envelope.conditioned_floor_area} sq ft")
    logger.info(f"  WWR: {extraction.envelope.window_to_floor_ratio:.2%}")

    return extraction
