#!/usr/bin/env python3
"""
Focused improvement loop for orientation extractor.

Runs the orientation extraction test, analyzes failures, invokes critic
with focus on orientation-extractor, applies proposals, and re-tests.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from improvement.critic import InstructionProposal, parse_proposal
from improvement.apply import apply_proposal

# Ground truth orientations
GROUND_TRUTH = {
    "chamberlin-circle": 73,
    "canterbury-rd": 90,
    "martinez-adu": 284,
    "poonian-adu": 112,
    "lamb-adu": 22,
}

TOLERANCE = 15  # degrees


def angular_distance(a: float, b: float) -> float:
    """Calculate minimum angular distance between two angles."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def run_orientation_test() -> dict:
    """Run orientation extraction on all evals and return results."""
    print("\n[Test] Running orientation extraction on all evals...")

    result = subprocess.run(
        ["python3", "test_orientation.py"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )

    # Load results from JSON file
    results_path = Path(__file__).parent / "orientation_test_results.json"
    if results_path.exists():
        with open(results_path) as f:
            return json.load(f)
    return None


def format_orientation_failures(results: dict) -> str:
    """Format orientation test failures for critic analysis."""
    lines = []

    lines.append("## Orientation Extraction Failures\n")
    lines.append("The orientation extractor determines building front orientation from site plans.")
    lines.append("Incorrect orientation cascades to ~11 downstream errors (4 walls + 7 windows).\n")

    lines.append("### Test Results\n")
    lines.append(f"- Accuracy: {results['summary']['correct']}/{results['summary']['successful']} correct (within ±{results['tolerance_degrees']}°)")
    lines.append(f"- Average error: {results['summary']['avg_error']:.1f}°\n")

    lines.append("### Detailed Results\n")
    lines.append("| Eval | Predicted | Expected | Error | Status |")
    lines.append("|------|-----------|----------|-------|--------|")

    for r in results["results"]:
        if r["status"] == "success":
            status = "✓ PASS" if r["correct"] else "✗ FAIL"
            lines.append(f"| {r['eval_id']} | {r['predicted']:.1f}° | {r['expected']}° | {r['error_degrees']:.1f}° | {status} |")

    lines.append("\n### Failure Analysis\n")

    failures = [r for r in results["results"] if r["status"] == "success" and not r["correct"]]

    for r in failures:
        lines.append(f"**{r['eval_id']}** (error: {r['error_degrees']:.1f}°)")
        lines.append(f"- Predicted: {r['predicted']:.1f}°, Expected: {r['expected']}°")
        lines.append(f"- Confidence: {r['confidence']}")
        lines.append(f"- North arrow found: {r['north_arrow_found']} (page {r['north_arrow_page']})")
        if r.get('reasoning'):
            lines.append(f"- Reasoning: {r['reasoning']}")
        lines.append("")

    return "\n".join(lines)


def invoke_orientation_critic(failure_analysis: str, project_root: Path) -> str:
    """Invoke critic agent focused on orientation-extractor."""
    instructions_dir = project_root / ".claude" / "instructions"

    # List only orientation-extractor instructions
    orientation_files = list((instructions_dir / "orientation-extractor").rglob("*.md"))
    files_list = "\n".join(f"- {f.relative_to(project_root)}" for f in orientation_files)

    prompt = f"""Analyze the following orientation extraction failures and propose ONE improvement to the orientation-extractor instructions.

{failure_analysis}

## IMPORTANT: Focus Area

You MUST propose changes to the **orientation-extractor** instructions only.
The orientation extractor is the priority because incorrect orientation causes cascading errors in wall and window azimuths.

## Available Instruction Files

{files_list}

## Your Task

Based on the failure patterns above, generate a proposal to improve the orientation-extractor instructions.
Focus on:
1. Why the agent is misidentifying the front orientation
2. How to improve north arrow angle measurement
3. How to better identify which side of the building is the "front"

Output your proposal as JSON following this schema:
{{
  "target_file": ".claude/instructions/orientation-extractor/instructions.md",
  "current_version": "v1.0.0",
  "proposed_version": "v1.1.0",
  "change_type": "add_section|modify_section|clarify_rule",
  "failure_pattern": "Description of what's failing",
  "hypothesis": "Why it's failing (instruction gap)",
  "proposed_change": "Exact markdown text to add or modify",
  "expected_impact": "What should improve",
  "affected_error_types": ["wrong_value"],
  "affected_domains": ["project"]
}}
"""

    print("\n[Critic] Invoking critic agent...")
    result = subprocess.run(
        ["claude", "--agent", "critic", "--print", prompt],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"Critic failed: {result.stderr}")

    return result.stdout


def run_improvement_iteration(iteration: int, project_root: Path) -> dict:
    """Run one iteration of orientation improvement."""
    print(f"\n{'='*60}")
    print(f"ITERATION {iteration}")
    print(f"{'='*60}")

    # Step 1: Run orientation test
    results = run_orientation_test()
    if not results:
        print("Failed to run orientation test")
        return {"status": "error", "error": "Test failed"}

    before_accuracy = results["summary"]["correct"] / results["summary"]["successful"]
    before_avg_error = results["summary"]["avg_error"]

    print(f"\n[Before] Accuracy: {before_accuracy:.1%}, Avg error: {before_avg_error:.1f}°")

    # Check if we're already at 100%
    if results["summary"]["correct"] == results["summary"]["successful"]:
        print("\n[Success] All orientation extractions correct!")
        return {"status": "complete", "accuracy": 1.0, "avg_error": before_avg_error}

    # Step 2: Format failures for critic
    failure_analysis = format_orientation_failures(results)

    # Step 3: Invoke critic
    try:
        critic_output = invoke_orientation_critic(failure_analysis, project_root)
        proposal = parse_proposal(critic_output)
    except Exception as e:
        print(f"Critic error: {e}")
        return {"status": "error", "error": str(e)}

    if not proposal:
        print("Critic did not generate a valid proposal")
        return {"status": "no_proposal"}

    print(f"\n[Proposal] {proposal.change_type} in {proposal.target_file}")
    print(f"  Hypothesis: {proposal.hypothesis[:100]}...")

    # Step 4: Apply proposal
    print(f"\n[Apply] Applying proposal...")
    try:
        old_ver, new_ver = apply_proposal(proposal, project_root, [])
        print(f"  Version: {old_ver} -> {new_ver}")
    except Exception as e:
        print(f"Apply error: {e}")
        return {"status": "error", "error": str(e)}

    # Step 5: Re-run test
    print("\n[Retest] Running orientation extraction again...")
    after_results = run_orientation_test()

    if after_results:
        after_accuracy = after_results["summary"]["correct"] / after_results["summary"]["successful"]
        after_avg_error = after_results["summary"]["avg_error"]

        accuracy_delta = after_accuracy - before_accuracy
        error_delta = after_avg_error - before_avg_error

        print(f"\n[After] Accuracy: {after_accuracy:.1%} ({accuracy_delta:+.1%})")
        print(f"        Avg error: {after_avg_error:.1f}° ({error_delta:+.1f}°)")

        return {
            "status": "success",
            "before_accuracy": before_accuracy,
            "after_accuracy": after_accuracy,
            "before_avg_error": before_avg_error,
            "after_avg_error": after_avg_error,
            "accuracy_delta": accuracy_delta,
            "error_delta": error_delta,
            "proposal": {
                "target_file": proposal.target_file,
                "change_type": proposal.change_type,
                "hypothesis": proposal.hypothesis,
            }
        }

    return {"status": "error", "error": "Retest failed"}


def main():
    project_root = Path(__file__).parent
    max_iterations = 5

    print("=" * 60)
    print("ORIENTATION EXTRACTOR IMPROVEMENT LOOP")
    print("=" * 60)
    print(f"Max iterations: {max_iterations}")
    print(f"Ground truth evals: {len(GROUND_TRUTH)}")
    print(f"Tolerance: ±{TOLERANCE}°")

    all_results = []

    for i in range(1, max_iterations + 1):
        result = run_improvement_iteration(i, project_root)
        all_results.append(result)

        if result["status"] == "complete":
            print(f"\n{'='*60}")
            print("SUCCESS! All orientations correct.")
            break

        if result["status"] == "error":
            print(f"\nIteration {i} failed: {result.get('error')}")
            # Continue anyway

        if result["status"] == "no_proposal":
            print(f"\nNo proposal generated. Stopping.")
            break

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Iterations run: {len(all_results)}")

    successful = [r for r in all_results if r["status"] == "success"]
    if successful:
        first = successful[0]
        last = successful[-1]
        print(f"Accuracy: {first['before_accuracy']:.1%} -> {last['after_accuracy']:.1%}")
        print(f"Avg error: {first['before_avg_error']:.1f}° -> {last['after_avg_error']:.1f}°")

    # Save results
    output_path = project_root / "orientation_improvement_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "iterations": all_results,
        }, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
