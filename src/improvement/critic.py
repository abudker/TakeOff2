"""Critic agent invocation and failure analysis for improvement loop."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import subprocess
import re
from dataclasses import dataclass


def find_latest_iteration(eval_dir: Path) -> int:
    """
    Find the latest iteration number in eval's results directory.

    Args:
        eval_dir: Path to eval directory (e.g., evals/chamberlin-circle)

    Returns:
        Latest iteration number (e.g., 5 for iteration-005)
        Returns 0 if no iterations found
    """
    results_dir = eval_dir / "results"
    if not results_dir.exists():
        return 0

    iteration_dirs = [
        d for d in results_dir.iterdir()
        if d.is_dir() and d.name.startswith("iteration-")
    ]

    if not iteration_dirs:
        return 0

    # Extract numbers from iteration-NNN format
    iterations = []
    for d in iteration_dirs:
        match = re.match(r"iteration-(\d+)", d.name)
        if match:
            iterations.append(int(match.group(1)))

    return max(iterations) if iterations else 0


def load_eval_results(evals_dir: Path, eval_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Load eval-results.json from latest iteration of each eval.

    Args:
        evals_dir: Base evals directory (e.g., Path("evals"))
        eval_ids: List of eval IDs to load (e.g., ["chamberlin-circle"])

    Returns:
        List of eval result dicts, each containing:
        - eval_id
        - metrics
        - discrepancies
        - timestamp
        - iteration
    """
    results = []

    for eval_id in eval_ids:
        eval_dir = evals_dir / eval_id
        if not eval_dir.exists():
            continue

        latest_iter = find_latest_iteration(eval_dir)
        if latest_iter == 0:
            continue

        results_path = (
            eval_dir / "results" / f"iteration-{latest_iter:03d}" / "eval-results.json"
        )

        if results_path.exists():
            with open(results_path, "r") as f:
                result = json.load(f)
                results.append(result)

    return results


def aggregate_failure_analysis(eval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate failure patterns across all evals.

    Implementation-blind: only looks at discrepancies and metrics,
    not at agent code or extraction implementation.

    Args:
        eval_results: List of eval-results.json data

    Returns:
        Dict with:
        - num_evals: int
        - total_discrepancies: int
        - aggregate_f1: float (macro average across evals)
        - errors_by_type: {omission: N, hallucination: N, ...}
        - errors_by_domain: {project: N, walls: N, ...}
        - dominant_error_type: str
        - dominant_domain: str
        - sample_discrepancies: List[Dict] (first 20 for context)
    """
    if not eval_results:
        return {
            "num_evals": 0,
            "total_discrepancies": 0,
            "aggregate_f1": 0.0,
            "errors_by_type": {},
            "errors_by_domain": {},
            "dominant_error_type": None,
            "dominant_domain": None,
            "sample_discrepancies": [],
        }

    # Aggregate total discrepancies
    total_discrepancies = sum(len(r["discrepancies"]) for r in eval_results)

    # Aggregate error types
    total_errors_by_type: Dict[str, int] = {
        "omission": 0,
        "hallucination": 0,
        "wrong_value": 0,
        "format_error": 0,
    }

    for result in eval_results:
        errors_by_type = result["metrics"].get("errors_by_type", {})
        for error_type, count in errors_by_type.items():
            total_errors_by_type[error_type] = total_errors_by_type.get(error_type, 0) + count

    # Aggregate by domain (extract from field_path)
    all_discrepancies = []
    for result in eval_results:
        all_discrepancies.extend(result["discrepancies"])

    errors_by_domain: Dict[str, int] = {}
    for d in all_discrepancies:
        field_path = d["field_path"]
        # Extract domain: "project.run_id" -> "project", "walls[0].name" -> "walls"
        domain = field_path.split(".")[0].split("[")[0]
        errors_by_domain[domain] = errors_by_domain.get(domain, 0) + 1

    # Calculate aggregate metrics
    aggregate_f1 = sum(r["metrics"]["f1"] for r in eval_results) / len(eval_results)
    aggregate_precision = sum(r["metrics"]["precision"] for r in eval_results) / len(eval_results)
    aggregate_recall = sum(r["metrics"]["recall"] for r in eval_results) / len(eval_results)

    # Find dominant patterns
    dominant_error_type = None
    if total_errors_by_type:
        dominant_error_type = max(total_errors_by_type.items(), key=lambda x: x[1])[0]

    dominant_domain = None
    if errors_by_domain:
        dominant_domain = max(errors_by_domain.items(), key=lambda x: x[1])[0]

    return {
        "num_evals": len(eval_results),
        "total_discrepancies": total_discrepancies,
        "aggregate_f1": aggregate_f1,
        "aggregate_precision": aggregate_precision,
        "aggregate_recall": aggregate_recall,
        "errors_by_type": total_errors_by_type,
        "errors_by_domain": errors_by_domain,
        "dominant_error_type": dominant_error_type,
        "dominant_domain": dominant_domain,
        "sample_discrepancies": all_discrepancies[:20],  # First 20 for context
    }


def format_analysis_for_critic(analysis: Dict[str, Any]) -> str:
    """
    Format analysis as text prompt for critic agent.

    Args:
        analysis: Aggregated failure analysis from aggregate_failure_analysis()

    Returns:
        Formatted text prompt suitable for critic agent
    """
    lines = []

    # Summary stats
    lines.append("## Summary Statistics")
    lines.append("")
    lines.append(f"- Evaluations analyzed: {analysis['num_evals']}")
    lines.append(f"- Total discrepancies: {analysis['total_discrepancies']}")
    lines.append(f"- Aggregate F1: {analysis['aggregate_f1']:.3f}")
    lines.append(f"- Aggregate Precision: {analysis['aggregate_precision']:.3f}")
    lines.append(f"- Aggregate Recall: {analysis['aggregate_recall']:.3f}")
    lines.append("")

    # Error breakdown by type
    lines.append("## Errors by Type")
    lines.append("")
    errors_by_type = analysis["errors_by_type"]
    total = sum(errors_by_type.values())
    for error_type, count in sorted(errors_by_type.items(), key=lambda x: -x[1]):
        if count > 0:
            percentage = (count / total * 100) if total > 0 else 0
            lines.append(f"- **{error_type}**: {count} ({percentage:.1f}%)")
    lines.append("")
    if analysis["dominant_error_type"]:
        lines.append(f"**Dominant error type:** {analysis['dominant_error_type']}")
        lines.append("")

    # Error breakdown by domain
    lines.append("## Errors by Domain")
    lines.append("")
    errors_by_domain = analysis["errors_by_domain"]
    for domain, count in sorted(errors_by_domain.items(), key=lambda x: -x[1]):
        lines.append(f"- **{domain}**: {count} errors")
    lines.append("")
    if analysis["dominant_domain"]:
        lines.append(f"**Dominant domain:** {analysis['dominant_domain']}")
        lines.append("")

    # Sample discrepancies
    lines.append("## Sample Discrepancies")
    lines.append("")
    lines.append("(First 20 discrepancies for context)")
    lines.append("")
    for i, d in enumerate(analysis["sample_discrepancies"], 1):
        lines.append(f"{i}. **{d['field_path']}** ({d['error_type']})")
        lines.append(f"   - Expected: {d['expected']}")
        lines.append(f"   - Actual: {d['actual']}")
        lines.append("")

    return "\n".join(lines)


@dataclass
class InstructionProposal:
    """A proposed change to an instruction file."""
    target_file: str
    current_version: str
    proposed_version: str
    change_type: str  # add_section | modify_section | clarify_rule
    failure_pattern: str
    hypothesis: str
    proposed_change: str
    expected_impact: str
    affected_error_types: List[str]
    affected_domains: List[str]
    estimated_f1_delta: Optional[float] = None


def invoke_critic(
    analysis: Dict[str, Any],
    instructions_dir: Path,
    project_root: Path
) -> str:
    """
    Invoke critic agent via Claude CLI subprocess.

    Args:
        analysis: Aggregated failure analysis
        instructions_dir: Path to .claude/instructions/
        project_root: Project root for working directory

    Returns:
        Raw output from critic agent

    Raises:
        RuntimeError: If critic agent fails
    """
    # Format analysis as prompt text
    prompt = format_analysis_for_critic(analysis)

    # List available instruction files for critic context
    instruction_files = list(instructions_dir.rglob("*.md"))
    files_list = "\n".join(
        f"- {f.relative_to(project_root)}" for f in instruction_files
    )

    full_prompt = f"""Analyze the following extraction failure patterns and propose ONE instruction file improvement.

## Failure Analysis

{prompt}

## Available Instruction Files

{files_list}

## Your Task

Based on the failure patterns above, generate a proposal to improve ONE instruction file.
Output your proposal as JSON following the schema in .claude/instructions/critic/proposal-format.md
"""

    # Invoke via subprocess
    result = subprocess.run(
        ["claude", "--agent", "critic", "--print", full_prompt],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300  # 5 min timeout
    )

    if result.returncode != 0:
        raise RuntimeError(f"Critic agent failed: {result.stderr}")

    return result.stdout


def parse_proposal(critic_output: str) -> Optional[InstructionProposal]:
    """
    Parse critic output to extract proposal JSON.

    Handles cases where JSON is embedded in markdown code blocks.

    Args:
        critic_output: Raw output from critic agent

    Returns:
        InstructionProposal if valid proposal found, None otherwise
    """
    # Try to find JSON in code block first
    json_match = re.search(r'```json\s*(.*?)\s*```', critic_output, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON object with target_file field
        # Use more flexible pattern to handle nested braces
        json_match = re.search(
            r'\{[^{}]*"target_file"[^{}]*"[^"]*"[^{}]*\}',
            critic_output,
            re.DOTALL
        )
        if json_match:
            json_str = json_match.group(0)
        else:
            return None

    try:
        data = json.loads(json_str)
        return InstructionProposal(
            target_file=data["target_file"],
            current_version=data.get("current_version", "v1.0.0"),
            proposed_version=data.get("proposed_version", "v1.0.1"),
            change_type=data.get("change_type", "add_section"),
            failure_pattern=data["failure_pattern"],
            hypothesis=data["hypothesis"],
            proposed_change=data["proposed_change"],
            expected_impact=data["expected_impact"],
            affected_error_types=data.get("affected_error_types", []),
            affected_domains=data.get("affected_domains", []),
            estimated_f1_delta=data.get("estimated_f1_delta")
        )
    except (json.JSONDecodeError, KeyError) as e:
        return None
