"""Orchestrator - LangGraph workflow for extraction pipeline."""
import logging
from pathlib import Path
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from agents.discovery import run_discovery
from agents.extractors.project import run_project_extractor, ProjectExtraction
from schemas.discovery import DocumentMap
from schemas.building_spec import BuildingSpec

logger = logging.getLogger(__name__)


class ExtractionState(TypedDict):
    """State for extraction workflow."""
    eval_name: str
    pdf_path: str
    page_images: List[str]
    document_map: Optional[DocumentMap]
    project_extraction: Optional[ProjectExtraction]
    building_spec: Optional[dict]
    error: Optional[str]


def discovery_node(state: ExtractionState) -> dict:
    """
    Discovery node: Classify pages in document.

    Args:
        state: Current extraction state

    Returns:
        Updated state with document_map or error
    """
    try:
        logger.info(f"[{state['eval_name']}] Starting discovery phase")
        page_paths = [Path(p) for p in state["page_images"]]
        instructions_path = Path(".claude/instructions/discovery/instructions.md")

        document_map = run_discovery(page_paths, instructions_path)

        logger.info(f"[{state['eval_name']}] Discovery complete: {document_map.total_pages} pages classified")
        return {"document_map": document_map}

    except Exception as e:
        logger.error(f"[{state['eval_name']}] Discovery failed: {e}")
        return {"error": f"Discovery failed: {str(e)}"}


def project_extraction_node(state: ExtractionState) -> dict:
    """
    Project extraction node: Extract ProjectInfo and EnvelopeInfo.

    Args:
        state: Current extraction state

    Returns:
        Updated state with project_extraction or error
    """
    try:
        logger.info(f"[{state['eval_name']}] Starting project extraction")
        page_paths = [Path(p) for p in state["page_images"]]
        instructions_dir = Path(".claude/instructions/project-extractor")

        extraction = run_project_extractor(
            page_paths,
            state["document_map"],
            instructions_dir
        )

        logger.info(f"[{state['eval_name']}] Project extraction complete")
        return {"project_extraction": extraction}

    except Exception as e:
        logger.error(f"[{state['eval_name']}] Project extraction failed: {e}")
        return {"error": f"Project extraction failed: {str(e)}"}


def merge_node(state: ExtractionState) -> dict:
    """
    Merge node: Create BuildingSpec from extraction results.

    Args:
        state: Current extraction state

    Returns:
        Updated state with building_spec or error
    """
    try:
        logger.info(f"[{state['eval_name']}] Merging extraction results")

        # Create BuildingSpec from project extraction
        building_spec = BuildingSpec(
            project=state["project_extraction"].project,
            envelope=state["project_extraction"].envelope
        )

        logger.info(f"[{state['eval_name']}] BuildingSpec created successfully")
        return {"building_spec": building_spec.model_dump()}

    except Exception as e:
        logger.error(f"[{state['eval_name']}] Merge failed: {e}")
        return {"error": f"Merge failed: {str(e)}"}


# Build workflow graph
workflow = StateGraph(ExtractionState)

# Add nodes
workflow.add_node("discovery", discovery_node)
workflow.add_node("extract_project", project_extraction_node)
workflow.add_node("merge", merge_node)

# Add edges
workflow.add_edge("discovery", "extract_project")
workflow.add_edge("extract_project", "merge")
workflow.add_edge("merge", END)

# Set entry point
workflow.set_entry_point("discovery")

# Compile workflow
app = workflow.compile()


def run_extraction(eval_name: str, eval_dir: Path) -> dict:
    """
    Run extraction workflow on an evaluation case.

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

    # Initialize state
    initial_state: ExtractionState = {
        "eval_name": eval_name,
        "pdf_path": str(pdf_path),
        "page_images": [str(p) for p in page_images],
        "document_map": None,
        "project_extraction": None,
        "building_spec": None,
        "error": None
    }

    # Run workflow
    try:
        final_state = app.invoke(initial_state)
        logger.info(f"Extraction complete for {eval_name}")
        return final_state

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise RuntimeError(f"Extraction workflow failed: {e}")
