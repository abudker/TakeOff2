#!/usr/bin/env python3
"""Test orientation extraction across all evaluations."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.orchestrator import run_discovery, run_orientation_extraction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Ground truth orientations (from ground_truth.csv files)
GROUND_TRUTH = {
    "chamberlin-circle": 73,
    "canterbury-rd": 90,
    "martinez-adu": 284,
    "poonian-adu": 112,
    "lamb-adu": 22,
}

# Tolerance for orientation matching (degrees)
TOLERANCE = 15  # Within 15 degrees is considered correct


def get_page_images(eval_dir: Path) -> list[Path]:
    """Get all preprocessed page images for an eval."""
    preprocessed_base = eval_dir / "preprocessed"
    all_pages = []
    for subdir in sorted(preprocessed_base.iterdir()):
        if subdir.is_dir():
            pages = sorted(subdir.glob("page-*.png"))
            all_pages.extend(pages)
    return all_pages


def angular_distance(a: float, b: float) -> float:
    """Calculate minimum angular distance between two angles (handles wraparound)."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def run_orientation_test(eval_id: str, evals_dir: Path) -> dict:
    """Run orientation extraction test on a single eval."""
    eval_dir = evals_dir / eval_id

    try:
        # Get page images
        page_images = get_page_images(eval_dir)
        if not page_images:
            return {
                "eval_id": eval_id,
                "status": "error",
                "error": "No preprocessed images found"
            }

        logger.info(f"[{eval_id}] Running discovery on {len(page_images)} pages...")

        # Run discovery first to get DocumentMap
        document_map = run_discovery(page_images)

        logger.info(f"[{eval_id}] Running orientation extraction...")
        logger.info(f"[{eval_id}]   Drawing pages: {document_map.drawing_pages}")

        # Run orientation extraction
        orientation_data = run_orientation_extraction(page_images, document_map)

        # Get results
        predicted = orientation_data.get("front_orientation", 0)
        expected = GROUND_TRUTH.get(eval_id)
        confidence = orientation_data.get("confidence", "unknown")
        north_arrow_found = orientation_data.get("north_arrow_found", False)
        north_arrow_page = orientation_data.get("north_arrow_page")
        reasoning = orientation_data.get("reasoning", "")

        # Calculate error
        error = angular_distance(predicted, expected) if expected else None
        correct = error <= TOLERANCE if error is not None else None

        return {
            "eval_id": eval_id,
            "status": "success",
            "predicted": predicted,
            "expected": expected,
            "error_degrees": error,
            "correct": correct,
            "confidence": confidence,
            "north_arrow_found": north_arrow_found,
            "north_arrow_page": north_arrow_page,
            "reasoning": reasoning[:200] if reasoning else None,
            "drawing_pages": document_map.drawing_pages,
        }

    except Exception as e:
        logger.error(f"[{eval_id}] Error: {e}")
        return {
            "eval_id": eval_id,
            "status": "error",
            "error": str(e)
        }


def main():
    evals_dir = Path("evals")

    print("=" * 70)
    print("ORIENTATION EXTRACTOR TEST")
    print("=" * 70)
    print(f"Testing on {len(GROUND_TRUTH)} evaluations")
    print(f"Tolerance: ±{TOLERANCE}°")
    print()

    results = []

    for eval_id in GROUND_TRUTH.keys():
        print(f"\n{'─' * 70}")
        print(f"Testing: {eval_id}")
        print(f"{'─' * 70}")

        result = run_orientation_test(eval_id, evals_dir)
        results.append(result)

        if result["status"] == "success":
            pred = result["predicted"]
            exp = result["expected"]
            err = result["error_degrees"]
            correct = "✓" if result["correct"] else "✗"
            conf = result["confidence"]
            north = "found" if result["north_arrow_found"] else "NOT FOUND"

            print(f"  Predicted:  {pred:.1f}°")
            print(f"  Expected:   {exp}°")
            print(f"  Error:      {err:.1f}° {correct}")
            print(f"  Confidence: {conf}")
            print(f"  North arrow: {north} (page {result['north_arrow_page']})")
            if result.get("reasoning"):
                print(f"  Reasoning:  {result['reasoning'][:100]}...")
        else:
            print(f"  ERROR: {result.get('error', 'Unknown')}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r["status"] == "success"]
    correct = [r for r in successful if r.get("correct")]
    errors = [r for r in results if r["status"] == "error"]

    print(f"\nResults: {len(correct)}/{len(successful)} correct (within ±{TOLERANCE}°)")

    if successful:
        avg_error = sum(r["error_degrees"] for r in successful) / len(successful)
        print(f"Average error: {avg_error:.1f}°")

        high_conf = [r for r in successful if r["confidence"] == "high"]
        north_found = [r for r in successful if r["north_arrow_found"]]
        print(f"High confidence: {len(high_conf)}/{len(successful)}")
        print(f"North arrow found: {len(north_found)}/{len(successful)}")

    if errors:
        print(f"\nFailed extractions: {len(errors)}")
        for r in errors:
            print(f"  - {r['eval_id']}: {r.get('error', 'Unknown')}")

    # Detailed table
    print("\n" + "─" * 70)
    print(f"{'Eval':<20} {'Pred':>8} {'Exp':>8} {'Error':>8} {'Status':>10}")
    print("─" * 70)
    for r in results:
        if r["status"] == "success":
            status = "✓ PASS" if r["correct"] else "✗ FAIL"
            print(f"{r['eval_id']:<20} {r['predicted']:>7.1f}° {r['expected']:>7}° {r['error_degrees']:>7.1f}° {status:>10}")
        else:
            print(f"{r['eval_id']:<20} {'ERROR':>8} {'-':>8} {'-':>8} {'ERROR':>10}")

    # Save results to JSON
    output_path = Path("orientation_test_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "tolerance_degrees": TOLERANCE,
            "summary": {
                "total": len(results),
                "successful": len(successful),
                "correct": len(correct),
                "accuracy": len(correct) / len(successful) if successful else 0,
                "avg_error": avg_error if successful else None,
            },
            "results": results,
        }, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    # Return exit code based on success
    return 0 if len(correct) == len(successful) else 1


if __name__ == "__main__":
    sys.exit(main())
