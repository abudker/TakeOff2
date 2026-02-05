#!/usr/bin/env python3
"""Two-pass orientation extraction with verification.

This approach runs orientation extraction twice with different methods:
- Pass 1: North arrow + street/entry direction (fast, direct)
- Pass 2: Elevation label + footprint matching (thorough, cross-referenced)

Then compares results to catch systematic errors:
- 90° difference = side/front confusion
- 180° difference = front/back confusion
- Agreement = high confidence
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.orchestrator import (
    run_discovery,
    invoke_claude_agent_async,
    extract_json_from_response,
    get_relevant_pages_for_domain,
    discover_source_pdfs,
    build_pdf_read_instructions,
    run_cv_sensors,
)
from schemas.discovery import DocumentMap, PDFSource, CACHE_VERSION

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

TOLERANCE = 15  # degrees
CACHE_DIR = Path("evals/.cache")


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
            cached_version = data.get("cache_version", 1)
            if cached_version < CACHE_VERSION:
                cache_file.unlink()
                return None
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


def ensure_discovery(eval_id: str, evals_dir: Path) -> Tuple[DocumentMap, Path]:
    """Get discovery result, using cache if available."""
    eval_dir = evals_dir / eval_id
    source_pdfs = discover_source_pdfs(eval_dir)

    document_map = get_cached_discovery(eval_id)
    if document_map:
        logger.info(f"[{eval_id}] Using cached discovery")
        return document_map, eval_dir

    total_pages = sum(pdf.total_pages for pdf in source_pdfs.values())
    logger.info(f"[{eval_id}] Running discovery on {total_pages} pages...")
    document_map = run_discovery(eval_dir, source_pdfs)
    save_discovery_cache(eval_id, document_map)
    return document_map, eval_dir


async def run_pass(
    eval_id: str,
    eval_dir: Path,
    document_map: DocumentMap,
    pass_num: int,
    cv_hints: Optional[Dict] = None,
) -> Dict:
    """Run a single orientation extraction pass."""

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
        logger.error(f"[{eval_id}] Pass {pass_num} error: {e}")
        return {
            "pass": pass_num,
            "status": "error",
            "error": str(e)
        }


def verify_passes(pass1: Dict, pass2: Dict) -> Dict:
    """Compare two pass results and determine final orientation."""

    if pass1["status"] != "success" and pass2["status"] != "success":
        return {
            "final_orientation": None,
            "confidence": "low",
            "verification": "both_failed",
            "notes": "Both passes failed"
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
        # Handle wraparound
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
    # Prefer higher confidence; on tie, prefer Pass 1
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

    # Arbitrary disagreement
    return {
        "final_orientation": chosen,
        "confidence": "low",
        "verification": "disagreement",
        "notes": f"Passes disagree by {diff:.1f}° - trusting {chosen_pass} (higher confidence)",
        "pass1_orientation": o1,
        "pass2_orientation": o2,
    }


async def run_twopass_extraction(
    eval_id: str,
    eval_dir: Path,
    document_map: DocumentMap,
    use_cv_hints: bool = True
) -> Dict:
    """Run both passes in parallel and verify results."""

    logger.info(f"[{eval_id}] Running two-pass extraction...")

    # Run CV sensors first if enabled
    cv_hints = None
    if use_cv_hints:
        try:
            cv_hints = run_cv_sensors(eval_dir, document_map)
            logger.info(f"[{eval_id}] CV hints: north={cv_hints['north_arrow']['angle']}°, "
                       f"walls={len(cv_hints['wall_edges'])}, "
                       f"building_rot={cv_hints['building_rotation']['rotation_from_horizontal']}°")
        except Exception as e:
            logger.warning(f"[{eval_id}] CV sensors failed, proceeding without hints: {e}")

    # Run both passes in parallel with CV hints
    pass1_task = run_pass(eval_id, eval_dir, document_map, 1, cv_hints)
    pass2_task = run_pass(eval_id, eval_dir, document_map, 2, cv_hints)

    pass1, pass2 = await asyncio.gather(pass1_task, pass2_task)

    # Verify and combine results
    verification = verify_passes(pass1, pass2)

    expected = GROUND_TRUTH.get(eval_id)
    final_orientation = verification["final_orientation"]

    if final_orientation is not None and expected is not None:
        error = angular_distance(final_orientation, expected)
        correct = error <= TOLERANCE
    else:
        error = None
        correct = None

    return {
        "eval_id": eval_id,
        "status": "success",
        "pass1": pass1,
        "pass2": pass2,
        "verification": verification["verification"],
        "final_orientation": final_orientation,
        "expected": expected,
        "error_degrees": error,
        "correct": correct,
        "confidence": verification["confidence"],
        "notes": verification["notes"],
        "cv_hints": cv_hints,
    }


async def run_all_evals(evals_dir: Path = Path("evals"), use_cv_hints: bool = True) -> List[Dict]:
    """Run two-pass extraction on all evals."""

    eval_ids = list(GROUND_TRUTH.keys())

    # Ensure all discoveries are cached
    discoveries = {}
    for eval_id in eval_ids:
        document_map, eval_dir = ensure_discovery(eval_id, evals_dir)
        discoveries[eval_id] = (document_map, eval_dir)

    # Run extractions
    logger.info(f"Running two-pass extraction on {len(eval_ids)} evals...")

    tasks = [
        run_twopass_extraction(eval_id, eval_dir, document_map, use_cv_hints)
        for eval_id, (document_map, eval_dir) in discoveries.items()
    ]

    return await asyncio.gather(*tasks)


def print_results(results: List[Dict]):
    """Print formatted results."""
    print("\n" + "=" * 80)
    print("TWO-PASS ORIENTATION VERIFICATION RESULTS")
    print("=" * 80)

    successful = [r for r in results if r["status"] == "success"]
    correct = [r for r in successful if r.get("correct")]
    agreements = [r for r in successful if r.get("verification") == "agreement"]

    print(f"\nResults: {len(correct)}/{len(successful)} correct (within ±{TOLERANCE}°)")
    print(f"Pass agreement: {len(agreements)}/{len(successful)} evals")

    if successful:
        avg_error = sum(r["error_degrees"] for r in successful if r["error_degrees"]) / len(successful)
        print(f"Average error: {avg_error:.1f}°")

    print("\n" + "─" * 80)
    print(f"{'Eval':<18} {'Pass1':>7} {'Pass2':>7} {'Final':>7} {'Exp':>7} {'Err':>6} {'Verify':<12} {'Status'}")
    print("─" * 80)

    for r in results:
        if r["status"] == "success":
            p1 = r["pass1"].get("orientation", "-") if r["pass1"]["status"] == "success" else "ERR"
            p2 = r["pass2"].get("orientation", "-") if r["pass2"]["status"] == "success" else "ERR"
            final = r["final_orientation"] or "-"
            exp = r["expected"] or "-"
            err = f"{r['error_degrees']:.1f}" if r["error_degrees"] is not None else "-"
            verify = r["verification"][:12]
            status = "✓ PASS" if r["correct"] else "✗ FAIL"

            p1_str = f"{p1:.0f}°" if isinstance(p1, (int, float)) else p1
            p2_str = f"{p2:.0f}°" if isinstance(p2, (int, float)) else p2
            final_str = f"{final:.0f}°" if isinstance(final, (int, float)) else final

            print(f"{r['eval_id']:<18} {p1_str:>7} {p2_str:>7} {final_str:>7} {exp:>7}° {err:>6}° {verify:<12} {status}")
        else:
            print(f"{r['eval_id']:<18} {'ERROR':>7} {'-':>7} {'-':>7} {'-':>7} {'-':>6} {'-':<12} ERROR")

    # Save detailed results
    output_file = Path("orientation_twopass_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Two-pass orientation extraction")
    parser.add_argument("--eval", type=str, help="Run single eval")
    parser.add_argument("--all", action="store_true", help="Run all evals")
    parser.add_argument("--no-cv", action="store_true", help="Disable CV hints (for A/B comparison)")
    args = parser.parse_args()

    use_cv_hints = not args.no_cv

    if args.eval:
        evals_dir = Path("evals")
        document_map, eval_dir = ensure_discovery(args.eval, evals_dir)
        result = asyncio.run(run_twopass_extraction(args.eval, eval_dir, document_map, use_cv_hints))
        print_results([result])
    elif args.all:
        results = asyncio.run(run_all_evals(use_cv_hints=use_cv_hints))
        print_results(results)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
