"""Interactive proposal review with Rich UI."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich.table import Table
from typing import Optional
import tempfile
import subprocess
import os

from .critic import InstructionProposal

console = Console()


def present_proposal(proposal: InstructionProposal) -> str:
    """
    Present a proposal to user and get decision.

    Displays:
    - Header with target file and version change
    - Failure pattern (what went wrong)
    - Hypothesis (why it went wrong)
    - Proposed change (syntax highlighted markdown)
    - Expected impact
    - Estimated F1 delta (if available)

    Returns:
        "accept" | "edit" | "reject" | "skip"
    """
    # Show proposal header in a panel
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Proposal: {proposal.change_type}[/bold cyan]\n"
        f"Target: [yellow]{proposal.target_file}[/yellow]\n"
        f"Version: {proposal.current_version} -> [green]{proposal.proposed_version}[/green]",
        title="[bold]Instruction Improvement Proposal[/bold]"
    ))

    # Show failure analysis
    console.print("\n[bold]Failure Pattern:[/bold]")
    console.print(f"  {proposal.failure_pattern}")

    console.print("\n[bold]Hypothesis:[/bold]")
    console.print(f"  {proposal.hypothesis}")

    # Show affected areas
    if proposal.affected_error_types or proposal.affected_domains:
        console.print("\n[bold]Targets:[/bold]")
        if proposal.affected_error_types:
            console.print(f"  Error types: {', '.join(proposal.affected_error_types)}")
        if proposal.affected_domains:
            console.print(f"  Domains: {', '.join(proposal.affected_domains)}")

    # Show proposed change with syntax highlighting
    console.print("\n[bold]Proposed Change:[/bold]")
    syntax = Syntax(proposal.proposed_change, "markdown", theme="monokai", line_numbers=False)
    console.print(syntax)

    # Show expected impact
    console.print(f"\n[bold]Expected Impact:[/bold]")
    console.print(f"  {proposal.expected_impact}")
    if proposal.estimated_f1_delta:
        delta_color = "green" if proposal.estimated_f1_delta > 0 else "red"
        console.print(f"  Estimated F1 delta: [{delta_color}]{proposal.estimated_f1_delta:+.3f}[/{delta_color}]")

    # Show actions menu
    console.print("\n[bold]Actions:[/bold]")
    console.print("  [a] Accept - Apply this change and re-run extraction")
    console.print("  [e] Edit   - Modify the proposed change before applying")
    console.print("  [r] Reject - Skip this proposal")
    console.print("  [s] Skip   - Save for later review")

    choice = Prompt.ask(
        "\nYour decision",
        choices=["a", "e", "r", "s"],
        default="a"
    )

    return {"a": "accept", "e": "edit", "r": "reject", "s": "skip"}[choice]


def edit_proposal(proposal: InstructionProposal) -> Optional[InstructionProposal]:
    """
    Allow user to edit the proposed_change text.

    Opens $EDITOR with the proposed change text.
    Returns modified proposal or None if cancelled.
    """
    # Create temp file with proposed change
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(f"# Edit Proposed Change\n")
        f.write(f"# Target: {proposal.target_file}\n")
        f.write(f"# Save and close to apply, or delete all content to cancel\n\n")
        f.write(proposal.proposed_change)
        temp_path = f.name

    # Get editor from environment
    editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'vim'))

    try:
        # Open in editor
        subprocess.run([editor, temp_path], check=True)

        # Read back edited content
        with open(temp_path) as f:
            content = f.read()

        # Remove comment lines and check if content remains
        lines = [l for l in content.split('\n') if not l.startswith('#')]
        edited_change = '\n'.join(lines).strip()

        if not edited_change:
            console.print("[yellow]Edit cancelled (empty content)[/yellow]")
            return None

        # Create new proposal with edited change
        from dataclasses import replace
        return replace(proposal, proposed_change=edited_change)

    except subprocess.CalledProcessError:
        console.print("[red]Editor exited with error[/red]")
        return None
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def show_metrics_comparison(
    before: dict,
    after: dict,
    iteration: int
) -> None:
    """
    Display before/after metrics comparison table.

    Args:
        before: Metrics dict from before applying proposal
        after: Metrics dict from after applying proposal
        iteration: Current iteration number
    """
    table = Table(title=f"Metrics Comparison (Iteration {iteration})")

    table.add_column("Metric", style="cyan")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Delta", justify="right")

    def delta_style(delta: float) -> str:
        if delta > 0.001:
            return f"[green]+{delta:.3f}[/green]"
        elif delta < -0.001:
            return f"[red]{delta:.3f}[/red]"
        else:
            return f"[dim]{delta:.3f}[/dim]"

    # Core metrics
    for metric in ['f1', 'precision', 'recall']:
        b = before.get(metric, 0)
        a = after.get(metric, 0)
        delta = a - b
        table.add_row(
            metric.upper(),
            f"{b:.3f}",
            f"{a:.3f}",
            delta_style(delta)
        )

    # Error counts
    before_errors = before.get('errors_by_type', {})
    after_errors = after.get('errors_by_type', {})

    for error_type in ['omission', 'hallucination', 'wrong_value', 'format_error']:
        b = before_errors.get(error_type, 0)
        a = after_errors.get(error_type, 0)
        delta = a - b
        # For errors, negative delta is good
        delta_str = f"[green]{delta:+d}[/green]" if delta < 0 else f"[red]{delta:+d}[/red]" if delta > 0 else f"[dim]{delta:+d}[/dim]"
        table.add_row(
            f"  {error_type}",
            str(b),
            str(a),
            delta_str
        )

    console.print()
    console.print(table)
