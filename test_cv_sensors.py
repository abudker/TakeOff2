#!/usr/bin/env python3
"""CV sensor validation tests on actual eval PDFs.

Tests that CV sensor functions:
1. Return valid structures with expected fields
2. Produce deterministic results (same input = same output)
3. Detect north arrows on most eval PDFs
4. Detect wall edges on all eval PDFs
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cv_sensors import (
    detect_north_arrow_angle,
    measure_wall_edge_angles,
    estimate_building_rotation,
)

# Site plan pages for each eval (from discovery cache)
SITE_PLAN_PAGES = {
    "canterbury-rd": 5,      # Global page 5 = plans.pdf page 4
    "chamberlin-circle": 3,  # Global page 3 = plans.pdf page 3
    "martinez-adu": 3,       # Global page 3 = plans.pdf page 3
    "poonian-adu": 3,        # Global page 3 = plans.pdf page 3
    "lamb-adu": 3,           # Global page 3 = plans.pdf page 3
}

# PDF paths
EVAL_PDFS = {
    "canterbury-rd": "evals/canterbury-rd/plans.pdf",
    "chamberlin-circle": "evals/chamberlin-circle/plans.pdf",
    "martinez-adu": "evals/martinez-adu/plans.pdf",
    "poonian-adu": "evals/poonian-adu/plans.pdf",
    "lamb-adu": "evals/lamb-adu/plans.pdf",
}


def test_north_arrow(eval_id: str) -> Dict[str, Any]:
    """Test north arrow detection on an eval PDF."""
    pdf_path = EVAL_PDFS[eval_id]
    page_num = SITE_PLAN_PAGES[eval_id]

    print(f"\n[{eval_id}] Testing north arrow detection...")
    print(f"  PDF: {pdf_path}, page {page_num}")

    # First run
    result1 = detect_north_arrow_angle(pdf_path, page_num)

    # Validate structure
    assert "angle" in result1, "Result missing 'angle' field"
    assert "confidence" in result1, "Result missing 'confidence' field"
    assert "method" in result1, "Result missing 'method' field"
    assert "debug" in result1, "Result missing 'debug' field"

    # Validate confidence values
    assert result1["confidence"] in ["high", "medium", "low", "none"], \
        f"Invalid confidence: {result1['confidence']}"

    # Validate angle range if detected
    if result1["angle"] is not None:
        assert 0 <= result1["angle"] < 360, \
            f"Angle out of range: {result1['angle']}"

    print(f"  Angle: {result1['angle']}")
    print(f"  Confidence: {result1['confidence']}")
    print(f"  Method: {result1['method']}")

    # Second run for determinism check
    result2 = detect_north_arrow_angle(pdf_path, page_num)

    # Check determinism (angles should be identical)
    if result1["angle"] is not None and result2["angle"] is not None:
        assert result1["angle"] == result2["angle"], \
            f"Non-deterministic: {result1['angle']} != {result2['angle']}"
        assert result1["confidence"] == result2["confidence"], \
            "Non-deterministic confidence"
        print("  Determinism: PASS")
    else:
        print("  Determinism: SKIP (no detection)")

    return {
        "detected": result1["confidence"] != "none",
        "angle": result1["angle"],
        "confidence": result1["confidence"],
        "method": result1["method"],
    }


def test_wall_edges(eval_id: str) -> Dict[str, Any]:
    """Test wall edge detection on an eval PDF."""
    pdf_path = EVAL_PDFS[eval_id]
    page_num = SITE_PLAN_PAGES[eval_id]

    print(f"\n[{eval_id}] Testing wall edge detection...")
    print(f"  PDF: {pdf_path}, page {page_num}")

    # First run
    walls1 = measure_wall_edge_angles(pdf_path, page_num)

    # Validate structure
    assert isinstance(walls1, list), "Result should be a list"
    assert len(walls1) > 0, "Should detect at least one wall edge"

    for wall in walls1[:3]:  # Check first 3
        assert "angle_from_horizontal" in wall
        assert "length" in wall
        assert "position" in wall
        assert "perpendicular_angle" in wall

        # Validate ranges
        assert 0 <= wall["angle_from_horizontal"] < 180, \
            f"Angle out of range: {wall['angle_from_horizontal']}"
        assert wall["length"] > 0, "Length must be positive"
        assert 0 <= wall["perpendicular_angle"] < 360, \
            f"Perpendicular angle out of range: {wall['perpendicular_angle']}"

    print(f"  Detected {len(walls1)} wall edges")
    print(f"  Top 3:")
    for i, wall in enumerate(walls1[:3], 1):
        print(f"    {i}. Angle: {wall['angle_from_horizontal']:.1f}°, "
              f"Length: {wall['length']:.0f}px, "
              f"Position: {wall['position']}")

    # Second run for determinism check
    walls2 = measure_wall_edge_angles(pdf_path, page_num)
    assert len(walls1) == len(walls2), "Non-deterministic wall count"
    for w1, w2 in zip(walls1, walls2):
        assert w1["angle_from_horizontal"] == w2["angle_from_horizontal"], \
            "Non-deterministic wall angles"
        assert w1["length"] == w2["length"], "Non-deterministic wall lengths"
    print("  Determinism: PASS")

    return {
        "count": len(walls1),
        "top_angles": [w["angle_from_horizontal"] for w in walls1[:3]],
    }


def test_building_rotation(eval_id: str) -> Dict[str, Any]:
    """Test building rotation estimation on an eval PDF."""
    pdf_path = EVAL_PDFS[eval_id]
    page_num = SITE_PLAN_PAGES[eval_id]

    print(f"\n[{eval_id}] Testing building rotation estimation...")
    print(f"  PDF: {pdf_path}, page {page_num}")

    # First run
    rotation1 = estimate_building_rotation(pdf_path, page_num)

    # Validate structure
    assert "rotation_from_horizontal" in rotation1
    assert "confidence" in rotation1
    assert "dominant_angles" in rotation1

    # Validate confidence
    assert rotation1["confidence"] in ["high", "medium", "low", "none"], \
        f"Invalid confidence: {rotation1['confidence']}"

    # Validate angle range
    assert 0 <= rotation1["rotation_from_horizontal"] < 180, \
        f"Rotation out of range: {rotation1['rotation_from_horizontal']}"

    print(f"  Rotation: {rotation1['rotation_from_horizontal']:.1f}°")
    print(f"  Confidence: {rotation1['confidence']}")
    print(f"  Dominant angles: {[f'{a:.1f}°' for a in rotation1['dominant_angles'][:3]]}")

    # Second run for determinism check
    rotation2 = estimate_building_rotation(pdf_path, page_num)
    assert rotation1["rotation_from_horizontal"] == rotation2["rotation_from_horizontal"], \
        "Non-deterministic rotation"
    print("  Determinism: PASS")

    return {
        "rotation": rotation1["rotation_from_horizontal"],
        "confidence": rotation1["confidence"],
    }


def run_eval(eval_id: str) -> Dict[str, Any]:
    """Run all CV sensor tests on one eval."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {eval_id}")
    print('=' * 60)

    results = {}

    try:
        results["north_arrow"] = test_north_arrow(eval_id)
    except Exception as e:
        print(f"  ERROR: {e}")
        results["north_arrow"] = {"error": str(e)}

    try:
        results["wall_edges"] = test_wall_edges(eval_id)
    except Exception as e:
        print(f"  ERROR: {e}")
        results["wall_edges"] = {"error": str(e)}

    try:
        results["building_rotation"] = test_building_rotation(eval_id)
    except Exception as e:
        print(f"  ERROR: {e}")
        results["building_rotation"] = {"error": str(e)}

    return results


def print_summary(all_results: Dict[str, Dict[str, Any]]):
    """Print summary table of all results."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # North arrow detection summary
    print("\nNorth Arrow Detection:")
    print(f"{'Eval':<20} {'Detected':<12} {'Angle':<10} {'Confidence':<12} {'Method':<15}")
    print("-" * 80)

    north_arrow_count = 0
    for eval_id, results in all_results.items():
        na = results.get("north_arrow", {})
        if "error" in na:
            print(f"{eval_id:<20} ERROR: {na['error']}")
        else:
            detected = "YES" if na.get("detected", False) else "NO"
            angle = f"{na.get('angle', 0):.1f}°" if na.get("angle") is not None else "N/A"
            confidence = na.get("confidence", "N/A")
            method = na.get("method", "N/A")
            print(f"{eval_id:<20} {detected:<12} {angle:<10} {confidence:<12} {method:<15}")
            if na.get("detected"):
                north_arrow_count += 1

    print(f"\nNorth arrow detected: {north_arrow_count}/{len(all_results)} evals")

    # Wall edge detection summary
    print("\nWall Edge Detection:")
    print(f"{'Eval':<20} {'Count':<8} {'Top 3 Angles':<40}")
    print("-" * 80)

    for eval_id, results in all_results.items():
        we = results.get("wall_edges", {})
        if "error" in we:
            print(f"{eval_id:<20} ERROR: {we['error']}")
        else:
            count = we.get("count", 0)
            angles = we.get("top_angles", [])
            angles_str = ", ".join(f"{a:.1f}°" for a in angles)
            print(f"{eval_id:<20} {count:<8} {angles_str:<40}")

    # Building rotation summary
    print("\nBuilding Rotation Estimation:")
    print(f"{'Eval':<20} {'Rotation':<12} {'Confidence':<12}")
    print("-" * 80)

    for eval_id, results in all_results.items():
        br = results.get("building_rotation", {})
        if "error" in br:
            print(f"{eval_id:<20} ERROR: {br['error']}")
        else:
            rotation = f"{br.get('rotation', 0):.1f}°"
            confidence = br.get("confidence", "N/A")
            print(f"{eval_id:<20} {rotation:<12} {confidence:<12}")

    # Overall pass/fail
    print("\n" + "=" * 80)
    if north_arrow_count >= 3:
        print(f"OVERALL: PASS (north arrow detected on {north_arrow_count}/5 evals, target >= 3)")
    else:
        print(f"OVERALL: FAIL (north arrow detected on {north_arrow_count}/5 evals, target >= 3)")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CV sensor validation tests")
    parser.add_argument(
        "--eval",
        type=str,
        help="Run tests on a specific eval (e.g., canterbury-rd)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run tests on all evals",
    )

    args = parser.parse_args()

    if args.all:
        eval_ids = list(EVAL_PDFS.keys())
    elif args.eval:
        eval_ids = [args.eval]
    else:
        parser.print_help()
        sys.exit(1)

    all_results = {}
    for eval_id in eval_ids:
        all_results[eval_id] = run_eval(eval_id)

    print_summary(all_results)


if __name__ == "__main__":
    main()
