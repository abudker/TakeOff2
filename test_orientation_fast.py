#!/usr/bin/env python3
"""Fast orientation testing with caching and parallelism.

Optimizations:
- Caches discovery results to avoid re-running discovery each time
- Runs orientation extraction in parallel across evals
- Option to test only failing evals for faster iteration
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.orchestrator import (
    run_discovery,
    invoke_claude_agent_async,
    extract_json_from_response,
)
from schemas.discovery import DocumentMap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Ground truth orientations
GROUND_TRUTH = {
    "chamberlin-circle": 73,
    "canterbury-rd": 90,
    "martinez-adu": 284,
    "poonian-adu": 112,
    "lamb-adu": 22,
}

# Default to failing evals for fast iteration
FAILING_EVALS = ["martinez-adu", "poonian-adu", "lamb-adu"]

TOLERANCE = 15  # degrees

# Cache directory for discovery results
CACHE_DIR = Path("evals/.cache")


def get_page_images(eval_dir: Path) -> List[Path]:
    """Get all preprocessed page images for an eval."""
    preprocessed_base = eval_dir / "preprocessed"
    all_pages = []
    for subdir in sorted(preprocessed_base.iterdir()):
        if subdir.is_dir():
            pages = sorted(subdir.glob("page-*.png"))
            all_pages.extend(pages)
    return all_pages


def angular_distance(a: float, b: float) -> float:
    """Calculate minimum angular distance between two angles."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def get_cached_discovery(eval_id: str) -> Optional[DocumentMap]:
    """Load cached discovery result if available."""
    cache_file = CACHE_DIR / f"{eval_id}_discovery.json"
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                data = json.load(f)
            return DocumentMap.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load cache for {eval_id}: {e}")
    return None


def save_discovery_cache(eval_id: str, document_map: DocumentMap):
    """Save discovery result to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{eval_id}_discovery.json"
    with open(cache_file, "w") as f:
        json.dump(document_map.model_dump(), f, indent=2)
    logger.info(f"Cached discovery for {eval_id}")


def ensure_discovery(eval_id: str, evals_dir: Path) -> tuple[DocumentMap, List[Path]]:
    """Get discovery result, using cache if available."""
    eval_dir = evals_dir / eval_id
    page_images = get_page_images(eval_dir)

    # Try cache first
    document_map = get_cached_discovery(eval_id)
    if document_map:
        logger.info(f"[{eval_id}] Using cached discovery ({len(document_map.drawing_pages)} drawing pages)")
        return document_map, page_images

    # Run discovery and cache
    logger.info(f"[{eval_id}] Running discovery on {len(page_images)} pages...")
    document_map = run_discovery(page_images)
    save_discovery_cache(eval_id, document_map)

    return document_map, page_images


async def run_orientation_async(
    eval_id: str,
    page_images: List[Path],
    document_map: DocumentMap
) -> Dict:
    """Run orientation extraction asynchronously."""
    # Filter to drawing pages
    relevant_page_numbers = set(document_map.drawing_pages)
    if not relevant_page_numbers:
        relevant_page_numbers = set(range(1, min(6, len(page_images) + 1)))

    # Limit to first 5 drawing pages for speed
    relevant_page_numbers = set(sorted(relevant_page_numbers)[:5])

    relevant_images = [
        page_images[page_num - 1]
        for page_num in sorted(relevant_page_numbers)
        if page_num <= len(page_images)
    ]

    logger.info(f"[{eval_id}] Running orientation on pages {sorted(relevant_page_numbers)}")

    # Build prompt
    page_list = "\n".join([
        f"- Page {sorted(relevant_page_numbers)[i]}: {p}"
        for i, p in enumerate(relevant_images)
    ])

    document_map_json = json.dumps(document_map.model_dump(), indent=2)

    prompt = f"""Extract building orientation from this Title 24 document.

Document structure (from discovery):
{document_map_json}

Drawing page image paths (site plans, floor plans):
{page_list}

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

    try:
        response = await invoke_claude_agent_async("orientation-extractor", prompt, timeout=300)
        json_data = extract_json_from_response(response)

        predicted = json_data.get("front_orientation", 0)
        expected = GROUND_TRUTH.get(eval_id)
        error = angular_distance(predicted, expected) if expected else None
        correct = error <= TOLERANCE if error is not None else None

        return {
            "eval_id": eval_id,
            "status": "success",
            "predicted": predicted,
            "expected": expected,
            "error_degrees": error,
            "correct": correct,
            "confidence": json_data.get("confidence", "unknown"),
            "north_arrow_found": json_data.get("north_arrow_found", False),
            "north_arrow_page": json_data.get("north_arrow_page"),
            "reasoning": json_data.get("reasoning", "")[:200],
        }
    except Exception as e:
        logger.error(f"[{eval_id}] Error: {e}")
        return {
            "eval_id": eval_id,
            "status": "error",
            "error": str(e)
        }


async def run_parallel_orientation_test(
    eval_ids: List[str],
    evals_dir: Path
) -> List[Dict]:
    """Run orientation extraction on multiple evals in parallel."""

    # First, ensure all discovery results are cached (sequential - uses sync agent)
    discoveries = {}
    for eval_id in eval_ids:
        document_map, page_images = ensure_discovery(eval_id, evals_dir)
        discoveries[eval_id] = (document_map, page_images)

    # Now run orientation extraction in parallel
    logger.info(f"Running orientation extraction in parallel on {len(eval_ids)} evals...")

    tasks = [
        run_orientation_async(eval_id, page_images, document_map)
        for eval_id, (document_map, page_images) in discoveries.items()
    ]

    results = await asyncio.gather(*tasks)
    return list(results)


def print_results(results: List[Dict], tolerance: int = TOLERANCE):
    """Print formatted test results."""
    print("\n" + "=" * 70)
    print("ORIENTATION TEST RESULTS")
    print("=" * 70)

    successful = [r for r in results if r["status"] == "success"]
    correct = [r for r in successful if r.get("correct")]

    print(f"\nResults: {len(correct)}/{len(successful)} correct (within ±{tolerance}°)")

    if successful:
        avg_error = sum(r["error_degrees"] for r in successful) / len(successful)
        print(f"Average error: {avg_error:.1f}°")

    print("\n" + "─" * 70)
    print(f"{'Eval':<20} {'Pred':>8} {'Exp':>8} {'Error':>8} {'Status':>10}")
    print("─" * 70)

    for r in results:
        if r["status"] == "success":
            status = "✓ PASS" if r["correct"] else "✗ FAIL"
            print(f"{r['eval_id']:<20} {r['predicted']:>7.1f}° {r['expected']:>7}° {r['error_degrees']:>7.1f}° {status:>10}")
        else:
            print(f"{r['eval_id']:<20} {'ERROR':>8} {'-':>8} {'-':>8} {'ERROR':>10}")

    return {
        "total": len(results),
        "successful": len(successful),
        "correct": len(correct),
        "accuracy": len(correct) / len(successful) if successful else 0,
        "avg_error": avg_error if successful else None,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fast orientation testing")
    parser.add_argument("--all", action="store_true", help="Test all evals, not just failing ones")
    parser.add_argument("--evals", nargs="+", help="Specific evals to test")
    parser.add_argument("--clear-cache", action="store_true", help="Clear discovery cache before running")
    parser.add_argument("--output", type=str, default="orientation_test_results.json", help="Output file")
    args = parser.parse_args()

    evals_dir = Path("evals")

    # Clear cache if requested
    if args.clear_cache and CACHE_DIR.exists():
        import shutil
        shutil.rmtree(CACHE_DIR)
        logger.info("Cleared discovery cache")

    # Determine which evals to test
    if args.evals:
        eval_ids = args.evals
    elif args.all:
        eval_ids = list(GROUND_TRUTH.keys())
    else:
        eval_ids = FAILING_EVALS
        print(f"Testing failing evals only: {eval_ids}")
        print("Use --all to test all evals")

    # Run parallel test
    results = asyncio.run(run_parallel_orientation_test(eval_ids, evals_dir))

    # Print and save results
    summary = print_results(results)

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "tolerance_degrees": TOLERANCE,
            "evals_tested": eval_ids,
            "summary": summary,
            "results": results,
        }, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    # Return exit code based on success
    return 0 if summary["correct"] == summary["successful"] else 1


if __name__ == "__main__":
    sys.exit(main())
