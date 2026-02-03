"""Discovery agent - Page classification for Title 24 documents."""
import logging
import time
from pathlib import Path
from typing import List
from anthropic import Anthropic
from schemas.discovery import DocumentMap

logger = logging.getLogger(__name__)


def run_discovery(page_images: List[Path], instructions_path: Path) -> DocumentMap:
    """
    Classify pages in Title 24 document using Claude vision API.

    Args:
        page_images: List of PNG file paths (preprocessed pages)
        instructions_path: Path to discovery instructions markdown

    Returns:
        DocumentMap with classified pages

    Raises:
        ValueError: If no page images provided
        RuntimeError: If API call fails after retries
    """
    if not page_images:
        raise ValueError("No page images provided for discovery")

    # Load instructions
    instructions = instructions_path.read_text()

    # Create Anthropic client
    client = Anthropic()

    # Build content array: page labels + images + classification prompt
    content = []

    # Add page labels and images
    for i, page_path in enumerate(page_images, start=1):
        # Upload image via Files API
        with open(page_path, "rb") as f:
            file = client.files.create(file=f, purpose="vision")

        # Add page label
        content.append({
            "type": "text",
            "text": f"--- Page {i} ---"
        })

        # Add image
        content.append({
            "type": "file",
            "file_id": file.id
        })

    # Add classification prompt
    content.append({
        "type": "text",
        "text": f"{instructions}\n\nClassify all {len(page_images)} pages and return the complete DocumentMap JSON."
    })

    # Call API with structured output and retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": content}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_map",
                        "schema": DocumentMap.model_json_schema()
                    }
                }
            )

            # Parse response
            document_map = DocumentMap.model_validate_json(response.content[0].text)

            # Log classifications
            logger.info(f"Classified {document_map.total_pages} pages:")
            for page in document_map.pages:
                logger.info(f"  Page {page.page_number}: {page.page_type} ({page.confidence})")

            return document_map

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Discovery attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Discovery failed after {max_retries} attempts")
                raise RuntimeError(f"Discovery API call failed: {e}")
