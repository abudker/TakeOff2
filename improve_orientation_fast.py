#!/usr/bin/env python3
"""Fast orientation improvement loop.

Runs rapid iteration cycles:
1. Run fast orientation test (cached discovery, parallel extraction)
2. Analyze failures and invoke critic focused on orientation-extractor
3. Auto-apply proposals
4. Re-test and check improvement
5. Repeat until target accuracy or max iterations
"""
import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from test_orientation_fast import (
    run_parallel_orientation_test,
    print_results,
    GROUND_TRUTH,
    FAILING_EVALS,
    TOLERANCE,
)

# Configuration
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_TARGET_ACCURACY = 1.0  # 100% = all passing
EVALS_DIR = Path("evals")
PROJECT_ROOT = Path(".")
INSTRUCTIONS_DIR = PROJECT_ROOT / ".claude" / "instructions"


def build_orientation_analysis(results: List[Dict]) -> Dict:
    """Build analysis dict for critic from orientation test results."""
    failures = [r for r in results if r["status"] == "success" and not r["correct"]]
    successes = [r for r in results if r["status"] == "success" and r["correct"]]

    # Build discrepancy patterns
    discrepancies = []
    for r in failures:
        discrepancies.append({
            "eval_id": r["eval_id"],
            "field": "front_orientation",
            "expected": r["expected"],
            "extracted": r["predicted"],
            "error_degrees": r["error_degrees"],
            "error_type": "wrong_value",
            "confidence": r.get("confidence", "unknown"),
            "north_arrow_found": r.get("north_arrow_found"),
            "north_arrow_page": r.get("north_arrow_page"),
            "reasoning": r.get("reasoning", ""),
        })

    return {
        "total_discrepancies": len(failures),
        "total_correct": len(successes),
        "total_tested": len(results),
        "accuracy": len(successes) / len(results) if results else 0,
        "avg_error_degrees": sum(r.get("error_degrees", 0) for r in results if r["status"] == "success") / len(results) if results else 0,
        "dominant_error_type": "wrong_value",
        "dominant_domain": "orientation",
        "discrepancies": discrepancies,
        "errors_by_type": {"wrong_value": len(failures)},
        "errors_by_domain": {"orientation": len(failures)},
    }


def format_analysis_for_critic(analysis: Dict) -> str:
    """Format orientation analysis for critic prompt."""
    output = []
    output.append("# Orientation Extraction Analysis\n")
    output.append(f"**Accuracy:** {analysis['accuracy']:.1%} ({analysis['total_correct']}/{analysis['total_tested']} correct)")
    output.append(f"**Average error:** {analysis['avg_error_degrees']:.1f}° (tolerance: {TOLERANCE}°)\n")

    if analysis["discrepancies"]:
        output.append("## Failures\n")
        for d in analysis["discrepancies"]:
            output.append(f"### {d['eval_id']}")
            output.append(f"- Expected: {d['expected']}°")
            output.append(f"- Predicted: {d['extracted']}°")
            output.append(f"- Error: {d['error_degrees']:.1f}°")
            output.append(f"- Confidence: {d['confidence']}")
            output.append(f"- North arrow: {'found' if d['north_arrow_found'] else 'NOT FOUND'} (page {d['north_arrow_page']})")
            output.append(f"- Reasoning: {d['reasoning'][:300]}...")
            output.append("")

    return "\n".join(output)


def invoke_orientation_critic(analysis: Dict) -> str:
    """Invoke critic agent focused on orientation-extractor."""
    analysis_text = format_analysis_for_critic(analysis)

    # Read current instructions for context
    instructions_path = INSTRUCTIONS_DIR / "orientation-extractor" / "instructions.md"
    instructions_content = ""
    if instructions_path.exists():
        instructions_content = instructions_path.read_text()

    prompt = f"""You are the critic agent analyzing orientation extraction failures.

## Analysis Summary

{analysis_text}

## Current Instructions

File: {instructions_path}

```markdown
{instructions_content[:4000]}
```

## Your Task

Analyze WHY the orientation extractor is failing on these cases. The failures show:
- Predicted orientations are significantly off from expected values
- The extractor found north arrows but calculated incorrect front_orientation

Focus on:
1. Common patterns in the errors (are they all off by similar amounts?)
2. Possible issues with the calculation method (front_drawing_angle - north_arrow_angle formula)
3. Ambiguity in identifying the "front" of the building
4. Issues with elevation labels vs true compass directions

Propose ONE specific, targeted change to the instructions that addresses the root cause.

Return a JSON proposal:
```json
{{
  "target_file": ".claude/instructions/orientation-extractor/instructions.md",
  "change_type": "add_section|modify_section|add_example|clarify_rule",
  "hypothesis": "Why this change will fix the failures",
  "change_description": "What to add/modify",
  "new_content": "The actual text to add or the modified section",
  "insert_after": "Text pattern to insert after (for add_section)",
  "section_to_modify": "Section header to modify (for modify_section)",
  "affected_domains": ["orientation"],
  "expected_impact": "high|medium|low",
  "risks": "Potential downsides of this change"
}}
```

Be specific and targeted. Small, focused changes are better than large rewrites.
"""

    cmd = [
        "claude",
        "--agent", "critic",
        "--print",
        prompt
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(PROJECT_ROOT)
    )

    if result.returncode != 0:
        raise RuntimeError(f"Critic failed: {result.stderr}")

    return result.stdout


def extract_json_from_response(response: str) -> Optional[Dict]:
    """Extract JSON from critic response."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try markdown code block
    lines = response.split('\n')
    in_block = False
    json_lines = []

    for line in lines:
        if line.strip().startswith('```'):
            if in_block:
                json_str = '\n'.join(json_lines)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    json_lines = []
            in_block = not in_block
        elif in_block:
            json_lines.append(line)

    # Last resort: find {...}
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass

    return None


def apply_proposal(proposal: Dict) -> bool:
    """Apply a critic proposal to the instructions file."""
    target_file = Path(proposal.get("target_file", ""))
    if not target_file.exists():
        print(f"  Target file not found: {target_file}")
        return False

    content = target_file.read_text()
    change_type = proposal.get("change_type", "")

    try:
        if change_type == "add_section":
            insert_after = proposal.get("insert_after", "")
            new_content = proposal.get("new_content", "")

            if insert_after and insert_after in content:
                # Find end of the line containing insert_after
                idx = content.find(insert_after)
                end_of_line = content.find('\n', idx + len(insert_after))
                if end_of_line == -1:
                    end_of_line = len(content)

                content = content[:end_of_line] + "\n\n" + new_content + content[end_of_line:]
            else:
                # Append to end
                content = content + "\n\n" + new_content

        elif change_type == "modify_section":
            section_header = proposal.get("section_to_modify", "")
            new_content = proposal.get("new_content", "")

            if section_header in content:
                # Find section start and end
                start_idx = content.find(section_header)
                # Find next section header (line starting with #)
                lines = content[start_idx:].split('\n')
                end_offset = 0
                for i, line in enumerate(lines[1:], 1):
                    if line.startswith('#'):
                        end_offset = sum(len(l) + 1 for l in lines[:i])
                        break
                else:
                    end_offset = len(content) - start_idx

                content = content[:start_idx] + new_content + content[start_idx + end_offset:]
            else:
                print(f"  Section not found: {section_header}")
                return False

        elif change_type == "add_example":
            # Add example after existing examples or at end of relevant section
            new_content = proposal.get("new_content", "")
            if "**Example" in content:
                # Find last example
                last_example = content.rfind("**Example")
                end_of_example = content.find('\n\n', last_example)
                if end_of_example == -1:
                    end_of_example = len(content)
                content = content[:end_of_example] + "\n\n" + new_content + content[end_of_example:]
            else:
                content = content + "\n\n" + new_content

        elif change_type == "clarify_rule":
            # Similar to modify_section but more targeted
            section_header = proposal.get("section_to_modify", "")
            new_content = proposal.get("new_content", "")

            if section_header and section_header in content:
                start_idx = content.find(section_header)
                end_of_header = content.find('\n', start_idx)
                content = content[:end_of_header + 1] + "\n" + new_content + "\n" + content[end_of_header + 1:]
            else:
                # Append as new section
                content = content + "\n\n" + new_content

        else:
            print(f"  Unknown change type: {change_type}")
            return False

        # Update version in content
        import re
        version_match = re.search(r'\*\*Version:\*\* v(\d+)\.(\d+)\.(\d+)', content)
        if version_match:
            major, minor, patch = map(int, version_match.groups())
            new_version = f"v{major}.{minor}.{patch + 1}"
            content = re.sub(
                r'\*\*Version:\*\* v\d+\.\d+\.\d+',
                f'**Version:** {new_version}',
                content
            )
            print(f"  Version bumped to {new_version}")

        # Write back
        target_file.write_text(content)
        return True

    except Exception as e:
        print(f"  Error applying proposal: {e}")
        return False


def run_iteration(iteration: int, test_all: bool = False) -> Dict:
    """Run one improvement iteration."""
    print(f"\n{'='*60}")
    print(f"ITERATION {iteration}")
    print(f"{'='*60}")

    # Step 1: Run orientation test
    print("\n[Test] Running orientation test...")
    eval_ids = list(GROUND_TRUTH.keys()) if test_all else FAILING_EVALS
    results = asyncio.run(run_parallel_orientation_test(eval_ids, EVALS_DIR))
    summary = print_results(results)

    # Check if we're done
    if summary["accuracy"] >= 1.0:
        print("\n[Success] All tests passing!")
        return {"status": "success", "summary": summary, "results": results}

    # Step 2: Build analysis and invoke critic
    print("\n[Critic] Analyzing failures and generating proposal...")
    analysis = build_orientation_analysis(results)

    try:
        critic_output = invoke_orientation_critic(analysis)
        proposal = extract_json_from_response(critic_output)
    except Exception as e:
        print(f"  Critic failed: {e}")
        return {"status": "critic_failed", "summary": summary, "error": str(e)}

    if not proposal:
        print("  No valid proposal generated")
        return {"status": "no_proposal", "summary": summary}

    # Step 3: Show and apply proposal
    print(f"\n[Proposal]")
    print(f"  Type: {proposal.get('change_type')}")
    print(f"  Hypothesis: {proposal.get('hypothesis', '')[:100]}...")

    print("\n[Apply] Applying proposal...")
    if apply_proposal(proposal):
        print("  Applied successfully")
    else:
        print("  Failed to apply")
        return {"status": "apply_failed", "summary": summary, "proposal": proposal}

    return {
        "status": "applied",
        "summary": summary,
        "results": results,
        "proposal": proposal
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fast orientation improvement loop")
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS,
                        help=f"Maximum iterations (default: {DEFAULT_MAX_ITERATIONS})")
    parser.add_argument("--target-accuracy", type=float, default=DEFAULT_TARGET_ACCURACY,
                        help=f"Target accuracy to stop at (default: {DEFAULT_TARGET_ACCURACY})")
    parser.add_argument("--test-all", action="store_true",
                        help="Test all 5 evals, not just failing ones")
    parser.add_argument("--single", action="store_true",
                        help="Run single iteration only")
    parser.add_argument("--output", type=str, default="orientation_improvement_log.json",
                        help="Output log file")
    args = parser.parse_args()

    print("=" * 60)
    print("ORIENTATION IMPROVEMENT LOOP")
    print("=" * 60)
    print(f"Max iterations: {args.max_iterations}")
    print(f"Target accuracy: {args.target_accuracy:.0%}")
    print(f"Testing: {'all evals' if args.test_all else 'failing evals only'}")

    log = {
        "started": datetime.now().isoformat(),
        "config": vars(args),
        "iterations": []
    }

    best_accuracy = 0.0

    for i in range(1, args.max_iterations + 1):
        result = run_iteration(i, test_all=args.test_all)
        log["iterations"].append({
            "iteration": i,
            "timestamp": datetime.now().isoformat(),
            **result
        })

        accuracy = result.get("summary", {}).get("accuracy", 0)
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            print(f"\n[Best] New best accuracy: {best_accuracy:.0%}")

        if result["status"] == "success":
            print(f"\n{'='*60}")
            print("TARGET REACHED!")
            print(f"{'='*60}")
            break

        if args.single:
            print("\n[Single iteration mode - stopping]")
            break

        if result["status"] in ("critic_failed", "no_proposal", "apply_failed"):
            print(f"\n[Warning] Iteration failed with status: {result['status']}")
            # Continue anyway - next iteration may work

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Iterations run: {len(log['iterations'])}")
    print(f"Best accuracy: {best_accuracy:.0%}")

    # Save log
    log["completed"] = datetime.now().isoformat()
    log["best_accuracy"] = best_accuracy

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(log, f, indent=2, default=str)
    print(f"\nLog saved to: {output_path}")

    # Run final test on all evals
    if not args.test_all and best_accuracy > 0:
        print("\n[Final] Running test on all evals...")
        all_results = asyncio.run(run_parallel_orientation_test(list(GROUND_TRUTH.keys()), EVALS_DIR))
        final_summary = print_results(all_results)
        log["final_all_evals"] = final_summary

        with open(output_path, "w") as f:
            json.dump(log, f, indent=2, default=str)

    return 0 if best_accuracy >= args.target_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
