"""CLI for improvement loop."""
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
import click
import yaml

from .critic import (
    load_eval_results,
    aggregate_failure_analysis,
    invoke_critic,
    parse_proposal,
    InstructionProposal
)
from .review import present_proposal, edit_proposal, show_metrics_comparison
from .apply import apply_proposal, rollback_instruction


def get_eval_ids(evals_dir: Path) -> List[str]:
    """Load eval IDs from manifest.yaml."""
    manifest_path = evals_dir / "manifest.yaml"
    if not manifest_path.exists():
        return []
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    return list(manifest.get("evals", {}).keys())


def get_latest_iteration(evals_dir: Path, eval_id: str) -> int:
    """Get latest iteration number for an eval."""
    results_dir = evals_dir / eval_id / "results"
    if not results_dir.exists():
        return 0

    iterations = [d for d in results_dir.iterdir()
                  if d.is_dir() and d.name.startswith("iteration-")]
    if not iterations:
        return 0

    return max(int(d.name.split("-")[1]) for d in iterations)


def get_next_iteration(evals_dir: Path) -> int:
    """Get next iteration number (max across all evals + 1)."""
    eval_ids = get_eval_ids(evals_dir)
    if not eval_ids:
        return 1
    return max(get_latest_iteration(evals_dir, eid) for eid in eval_ids) + 1


def load_aggregate_metrics(evals_dir: Path) -> dict:
    """Load current aggregate metrics from all evals."""
    eval_ids = get_eval_ids(evals_dir)
    all_metrics = []

    for eval_id in eval_ids:
        latest = get_latest_iteration(evals_dir, eval_id)
        if latest == 0:
            continue
        results_path = evals_dir / eval_id / "results" / f"iteration-{latest:03d}" / "eval-results.json"
        if results_path.exists():
            with open(results_path) as f:
                data = json.load(f)
                all_metrics.append(data["metrics"])

    if not all_metrics:
        return {"f1": 0, "precision": 0, "recall": 0, "errors_by_type": {}}

    # Compute macro averages
    return {
        "f1": sum(m["f1"] for m in all_metrics) / len(all_metrics),
        "precision": sum(m["precision"] for m in all_metrics) / len(all_metrics),
        "recall": sum(m["recall"] for m in all_metrics) / len(all_metrics),
        "errors_by_type": {
            "omission": sum(m["errors_by_type"].get("omission", 0) for m in all_metrics),
            "hallucination": sum(m["errors_by_type"].get("hallucination", 0) for m in all_metrics),
            "wrong_value": sum(m["errors_by_type"].get("wrong_value", 0) for m in all_metrics),
            "format_error": sum(m["errors_by_type"].get("format_error", 0) for m in all_metrics),
        }
    }


def run_extraction(evals_dir: Path, force: bool = True) -> bool:
    """Run extract-all command."""
    click.echo("\n[Extraction] Running extract-all...")
    cmd = ["python3", "-m", "agents", "extract-all", "--evals-dir", str(evals_dir)]
    if force:
        cmd.append("--force")
    result = subprocess.run(cmd, cwd=evals_dir.parent)
    return result.returncode == 0


def run_verification(evals_dir: Path, save: bool = True) -> bool:
    """Run verify-all command."""
    click.echo("\n[Verification] Running verify-all...")
    cmd = ["python3", "-m", "verifier", "verify-all", "--evals-dir", str(evals_dir)]
    if save:
        cmd.append("--save")
    result = subprocess.run(cmd, cwd=evals_dir.parent)
    return result.returncode == 0


def git_commit_iteration(
    proposal: InstructionProposal,
    before_metrics: dict,
    after_metrics: dict,
    iteration: int,
    project_root: Path
) -> bool:
    """Commit instruction file changes with metrics delta."""
    target_path = Path(proposal.target_file)
    agent_name = target_path.parent.name

    f1_delta = after_metrics["f1"] - before_metrics["f1"]
    precision_delta = after_metrics["precision"] - before_metrics["precision"]
    recall_delta = after_metrics["recall"] - before_metrics["recall"]

    # Build commit message
    commit_msg = f"""feat(instructions): improve {agent_name} {proposal.current_version} -> {proposal.proposed_version}

{proposal.hypothesis.split('.')[0] if proposal.hypothesis else 'Improve extraction accuracy'}

Metrics (iteration {iteration}):
- F1: {before_metrics["f1"]:.3f} -> {after_metrics["f1"]:.3f} ({f1_delta:+.3f})
- Precision: {before_metrics["precision"]:.3f} -> {after_metrics["precision"]:.3f} ({precision_delta:+.3f})
- Recall: {before_metrics["recall"]:.3f} -> {after_metrics["recall"]:.3f} ({recall_delta:+.3f})
"""

    try:
        # Stage instruction file
        subprocess.run(
            ["git", "add", proposal.target_file],
            cwd=project_root,
            check=True
        )

        # Commit with message
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=project_root,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


@click.group()
def cli():
    """Improvement loop CLI for instruction optimization."""
    pass


@cli.command()
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("evals"),
    help="Directory containing evaluation cases"
)
@click.option(
    "--skip-extraction",
    is_flag=True,
    help="Skip re-extraction (use existing results)"
)
@click.option(
    "--no-commit",
    is_flag=True,
    help="Don't auto-commit accepted proposals"
)
@click.option(
    "--focus",
    type=str,
    default=None,
    help="Focus critic on specific agent (e.g., 'orientation-extractor')"
)
@click.option(
    "--focus-reason",
    type=str,
    default=None,
    help="Explanation for why focus area is priority"
)
@click.option(
    "--auto",
    is_flag=True,
    help="Auto-accept proposals without user review (for autonomous iteration)"
)
def improve(evals_dir: Path, skip_extraction: bool, no_commit: bool, focus: str, focus_reason: str, auto: bool):
    """
    Run one iteration of the improvement loop.

    1. Analyze current verification results
    2. Invoke critic to generate proposal
    3. Present proposal for user review (or auto-accept with --auto)
    4. If accepted, apply change and re-run extraction/verification
    5. Show before/after metrics comparison
    6. Auto-commit with metrics

    Use --focus to constrain the critic to a specific extractor's instructions.
    Use --auto for autonomous iteration (can be run in a loop).

    Example for 5 iterations focused on orientation:
        for i in {1..5}; do
          python3 -m improvement improve --auto --focus orientation-extractor \\
            --focus-reason "Orientation errors cascade to wall/window azimuths"
        done
    """
    project_root = evals_dir.parent
    instructions_dir = project_root / ".claude" / "instructions"

    # Check prerequisites
    if not instructions_dir.exists():
        click.echo("Error: No .claude/instructions/ directory found", err=True)
        sys.exit(1)

    eval_ids = get_eval_ids(evals_dir)
    if not eval_ids:
        click.echo("Error: No evals found in manifest.yaml", err=True)
        sys.exit(1)

    click.echo(f"Improvement Loop - {len(eval_ids)} evals")
    if focus:
        click.echo(f"Focus: {focus}")
    click.echo("=" * 60)

    # Step 1: Load current results and compute metrics
    click.echo("\n[Analysis] Loading evaluation results...")
    results = load_eval_results(evals_dir, eval_ids)

    if not results:
        click.echo("No evaluation results found. Run extraction and verification first:")
        click.echo("  python3 -m agents extract-all")
        click.echo("  python3 -m verifier verify-all --save")
        sys.exit(1)

    before_metrics = load_aggregate_metrics(evals_dir)
    click.echo(f"Current aggregate F1: {before_metrics['f1']:.3f}")

    # Step 2: Aggregate failure analysis
    click.echo("\n[Analysis] Aggregating failure patterns...")
    analysis = aggregate_failure_analysis(results)

    click.echo(f"  Total discrepancies: {analysis['total_discrepancies']}")
    click.echo(f"  Dominant error type: {analysis['dominant_error_type']}")
    click.echo(f"  Dominant domain: {analysis['dominant_domain']}")

    # Step 3: Invoke critic
    if focus:
        click.echo(f"\n[Critic] Generating improvement proposal (focus: {focus})...")
    else:
        click.echo("\n[Critic] Generating improvement proposal...")
    try:
        critic_output = invoke_critic(
            analysis, instructions_dir, project_root,
            focus_agent=focus, focus_reason=focus_reason
        )
        proposal = parse_proposal(critic_output)
    except Exception as e:
        click.echo(f"Error invoking critic: {e}", err=True)
        sys.exit(1)

    if not proposal:
        click.echo("Critic did not generate a valid proposal.")
        click.echo("This may happen if metrics are already good or no clear pattern found.")
        sys.exit(0)

    # Step 4: Present proposal for review (or auto-accept)
    if auto:
        click.echo(f"\n[Auto] Auto-accepting proposal for {proposal.target_file}")
        click.echo(f"  Change: {proposal.change_type}")
        click.echo(f"  Hypothesis: {proposal.hypothesis[:100]}...")
        decision = "accept"
    else:
        decision = present_proposal(proposal)

        if decision == "edit":
            edited = edit_proposal(proposal)
            if edited:
                proposal = edited
                decision = "accept"
            else:
                decision = "reject"

        if decision in ("reject", "skip"):
            click.echo(f"\nProposal {decision}ed. No changes made.")
            sys.exit(0)

    # Step 5: Apply proposal
    click.echo(f"\n[Apply] Applying proposal to {proposal.target_file}...")

    # Determine iteration directories for snapshots
    next_iter = get_next_iteration(evals_dir)
    iteration_dirs = [
        evals_dir / eid / "results" / f"iteration-{next_iter:03d}"
        for eid in eval_ids
    ]

    # Create iteration directories
    for iter_dir in iteration_dirs:
        iter_dir.mkdir(parents=True, exist_ok=True)

    old_version, new_version = apply_proposal(proposal, project_root, iteration_dirs)
    click.echo(f"  Version: {old_version} -> {new_version}")

    # Step 6: Re-run extraction and verification
    if not skip_extraction:
        if not run_extraction(evals_dir):
            click.echo("Extraction failed!", err=True)
            sys.exit(1)

    if not run_verification(evals_dir):
        click.echo("Verification failed!", err=True)
        sys.exit(1)

    # Step 7: Show metrics comparison
    after_metrics = load_aggregate_metrics(evals_dir)
    show_metrics_comparison(before_metrics, after_metrics, next_iter)

    # Step 8: Auto-commit
    if not no_commit:
        click.echo("\n[Git] Committing changes...")
        if git_commit_iteration(proposal, before_metrics, after_metrics, next_iter, project_root):
            click.echo("  Committed successfully")
        else:
            click.echo("  Commit failed (may need manual commit)", err=True)

    # Summary
    f1_delta = after_metrics["f1"] - before_metrics["f1"]
    if f1_delta > 0:
        click.echo(f"\n[green]Iteration {next_iter} complete: F1 improved by {f1_delta:+.3f}[/green]")
    elif f1_delta < 0:
        click.echo(f"\n[yellow]Iteration {next_iter} complete: F1 decreased by {f1_delta:.3f}[/yellow]")
        click.echo("Consider running: improve rollback")
    else:
        click.echo(f"\n[dim]Iteration {next_iter} complete: F1 unchanged[/dim]")


@cli.command()
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("evals"),
    help="Directory containing evaluation cases"
)
def context(evals_dir: Path):
    """
    Output failure analysis context for conversational mode.

    Used by the /improve skill to bootstrap conversational improvement.
    Prints failure analysis and lists available instruction files.
    """
    project_root = evals_dir.parent
    instructions_dir = project_root / ".claude" / "instructions"

    # Check prerequisites
    if not instructions_dir.exists():
        click.echo("Error: No .claude/instructions/ directory found", err=True)
        sys.exit(1)

    eval_ids = get_eval_ids(evals_dir)
    if not eval_ids:
        click.echo("Error: No evals found in manifest.yaml", err=True)
        sys.exit(1)

    # Load evaluation results
    results = load_eval_results(evals_dir, eval_ids)
    if not results:
        click.echo("No evaluation results found. Run extraction and verification first:")
        click.echo("  python3 -m agents extract-all")
        click.echo("  python3 -m verifier verify-all --save")
        sys.exit(1)

    # Aggregate failure analysis
    from .critic import format_analysis_for_critic
    analysis = aggregate_failure_analysis(results)

    # Print formatted analysis
    print(format_analysis_for_critic(analysis))

    # List available instruction files
    print("\n## Available Instruction Files\n")
    for f in sorted(instructions_dir.rglob("*.md")):
        print(f"- {f.relative_to(project_root)}")


@cli.command()
@click.argument(
    "json_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("evals"),
    help="Directory containing evaluation cases"
)
@click.option(
    "--no-commit",
    is_flag=True,
    help="Skip git commit"
)
def apply(json_file: Path, evals_dir: Path, no_commit: bool):
    """
    Apply a proposal from JSON file.

    JSON_FILE is a path to a JSON file containing a proposal
    (see .claude/instructions/critic/proposal-format.md for schema).
    """
    project_root = evals_dir.parent

    # Read and parse proposal
    json_str = json_file.read_text()
    proposal = parse_proposal(json_str)

    if not proposal:
        click.echo("Could not parse proposal JSON", err=True)
        sys.exit(1)

    # Apply the proposal
    try:
        old_ver, new_ver = apply_proposal(proposal, project_root, [])
        click.echo(f"Applied: v{old_ver} -> v{new_ver}")
        click.echo(f"  File: {proposal.target_file}")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Optionally commit
    if not no_commit:
        import subprocess
        try:
            # Stage the modified file
            subprocess.run(
                ["git", "add", proposal.target_file],
                cwd=project_root,
                check=True
            )

            # Build commit message
            commit_msg = f"""feat(instructions): {proposal.change_type} in {Path(proposal.target_file).parent.name}

{proposal.hypothesis.split('.')[0] if proposal.hypothesis else 'Improve extraction accuracy'}

Version: v{old_ver} -> v{new_ver}
Change type: {proposal.change_type}
Affected domains: {', '.join(proposal.affected_domains)}
"""
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=project_root,
                check=True
            )
            click.echo("  Committed successfully")
        except subprocess.CalledProcessError:
            click.echo("  Commit failed (may need manual commit)", err=True)


@cli.command()
@click.argument("iteration", type=int)
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("evals"),
    help="Directory containing evaluation cases"
)
def rollback(iteration: int, evals_dir: Path):
    """
    Rollback instruction files to a previous iteration.

    ITERATION is the iteration number to rollback to (e.g., 2).

    This copies saved instruction file snapshots from the iteration
    folder back to .claude/instructions/.
    """
    project_root = evals_dir.parent
    instructions_dir = project_root / ".claude" / "instructions"

    click.echo(f"Rolling back to iteration {iteration}...")

    # Find iteration directories with snapshots
    eval_ids = get_eval_ids(evals_dir)
    restored_files = []

    for eval_id in eval_ids:
        iter_dir = evals_dir / eval_id / "results" / f"iteration-{iteration:03d}"
        changes_dir = iter_dir / "instruction-changes"

        if not changes_dir.exists():
            continue

        for snapshot in changes_dir.glob("*.md"):
            # Parse filename: agent-name-filename-vX.Y.Z.md
            parts = snapshot.stem.rsplit("-v", 1)
            if len(parts) != 2:
                continue

            name_parts = parts[0].rsplit("-", 1)
            if len(name_parts) != 2:
                continue

            agent_name, file_stem = name_parts
            target_path = instructions_dir / agent_name / f"{file_stem}.md"

            if target_path.exists():
                import shutil
                shutil.copy(snapshot, target_path)
                restored_files.append(str(target_path.relative_to(project_root)))

        # Only need to check one eval (all have same snapshots)
        break

    if restored_files:
        click.echo(f"Restored {len(restored_files)} file(s):")
        for f in restored_files:
            click.echo(f"  - {f}")
        click.echo("\nYou may want to re-run extraction and verification:")
        click.echo("  python3 -m agents extract-all --force")
        click.echo("  python3 -m verifier verify-all --save")
    else:
        click.echo(f"No instruction snapshots found for iteration {iteration}")


if __name__ == "__main__":
    cli()
