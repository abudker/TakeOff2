# Phase 5: Manual Improvement Loop - Research

**Researched:** 2026-02-03
**Domain:** LLM critic agents, failure pattern analysis, instruction file optimization, terminal-based review workflows
**Confidence:** MEDIUM-HIGH

## Summary

Phase 5 implements a manual improvement loop where a critic agent analyzes verification results, identifies failure patterns, and proposes targeted changes to instruction files. The user reviews proposals in the terminal, can accept/edit/reject them, and accepted changes trigger automatic re-extraction and verification. Each iteration is tracked in numbered folders with auto-commits showing metrics deltas.

Research reveals that LLM-based critic systems for prompt optimization have matured significantly in 2025-2026, with systems like AgentDevel, PromptWizard, and PromptAgent demonstrating implementation-blind failure analysis and iterative refinement. The standard approach involves: (1) structured failure pattern analysis grouping errors by type and domain, (2) hypothesis-driven proposal generation with clear rationale, (3) interactive terminal review using Rich library for presentation, and (4) git-based versioning with semantic version bumps for instruction files.

Key insight: The critic should NOT access agent internals or extraction code - it operates purely on verification results (eval-results.json with discrepancies and metrics). This "implementation-blind" approach, validated by AgentDevel research (January 2026), focuses the critic on observable symptoms rather than implementation details, leading to more generalizable improvements.

**Primary recommendation:** Build a critic agent that groups discrepancies by error type and domain, generates hypothesis-driven proposals targeting instruction files with version bumps, presents proposals interactively using Rich library, and commits accepted changes with metrics deltas in commit messages.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess | stdlib | Invoke critic agent via Claude Code | Established pattern from Phase 3-4 |
| json | stdlib | Parse eval-results.json, load instruction files | Already used throughout |
| pathlib | stdlib | File path handling for iteration folders | Already used throughout |
| git (via Bash) | system | Version control for instruction files | Industry standard for config versioning |

### Supporting (Needs Installation)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich | 13.9+ | Terminal UI for proposal presentation | Interactive prompts, tables, syntax highlighting |
| click | 8.1+ | CLI framework with prompts | Already used, extends for Accept/Edit/Reject workflow |
| difflib | stdlib | Generate diffs for instruction file changes | Show before/after comparisons |
| shutil | stdlib | Copy iteration folders for rollback | Directory operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rich | Textual (Rich's sister project) | Textual is full TUI framework, overkill for simple prompts |
| Rich | Prompt Toolkit | More powerful but steeper learning curve, Rich sufficient |
| Manual diff | git diff | git diff requires committed files, difflib works on strings |
| $EDITOR | Inline paste | $EDITOR more familiar, but requires temp file handling |

**Installation:**
```bash
pip install rich>=13.9
# click already installed from Phase 3-4
```

## Architecture Patterns

### Recommended Project Structure

```
.claude/
  agents/
    critic.md                    # Critic agent definition
  instructions/
    critic/
      instructions.md            # Main critic workflow
      failure-analysis.md        # Pattern recognition guide
      proposal-format.md         # Proposal structure template
    verifier/
      instructions.md            # v1.0.0 -> v1.1.0 (example evolution)
      error-types.md
      metrics.md
    project-extractor/
      instructions.md            # v1.0.0 -> v1.0.1 (example evolution)
      field-guide.md
    # ... other extractors
evals/
  {eval_id}/
    results/
      iteration-001/
        extracted.json
        eval-results.json        # Input to critic
        eval-report.html
      iteration-002/
        extracted.json
        eval-results.json
        eval-report.html
        proposal.json            # Critic's proposal (optional record)
        instruction-changes/     # Copies of changed instruction files
          verifier-instructions-v1.1.0.md
      aggregate.json             # Metrics history across iterations
src/
  improvement/
    critic.py                    # Invoke critic agent, parse proposals
    review.py                    # Terminal review workflow
    versioning.py                # Instruction file version management
    apply.py                     # Apply proposal to instruction files
    cli.py                       # CLI commands: improve, rollback
```

### Pattern 1: Implementation-Blind Failure Analysis

**What:** Critic analyzes only verification results, not agent code or extraction logic
**When to use:** Analyzing extraction failures to propose instruction improvements
**Example:**

```python
# Source: AgentDevel (arxiv.org/abs/2601.04620) - implementation-blind critic
from typing import Dict, List, Any
from pathlib import Path
import json

def analyze_failure_patterns(eval_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze eval-results.json to identify failure patterns.

    Implementation-blind: only looks at discrepancies and metrics,
    NOT at agent code or extraction implementation.

    Returns:
        Structured failure analysis for critic agent
    """
    discrepancies = eval_results["discrepancies"]
    metrics = eval_results["metrics"]

    # Group by error type
    errors_by_type = {
        "omission": [],
        "hallucination": [],
        "wrong_value": [],
        "format_error": []
    }

    for d in discrepancies:
        error_type = d["error_type"]
        errors_by_type[error_type].append(d)

    # Group by domain (project.*, envelope.*, walls[*].*, etc.)
    errors_by_domain = {}
    for d in discrepancies:
        field_path = d["field_path"]
        domain = field_path.split(".")[0].split("[")[0]  # "project" or "walls" or "windows"
        if domain not in errors_by_domain:
            errors_by_domain[domain] = []
        errors_by_domain[domain].append(d)

    # Identify high-impact fields (critical for energy modeling)
    critical_fields = [
        "envelope.conditioned_floor_area",
        "envelope.window_area",
        "project.climate_zone",
    ]
    critical_errors = [d for d in discrepancies
                       if d["field_path"] in critical_fields]

    return {
        "total_discrepancies": len(discrepancies),
        "errors_by_type": {k: len(v) for k, v in errors_by_type.items()},
        "errors_by_domain": {k: len(v) for k, v in errors_by_domain.items()},
        "critical_errors": len(critical_errors),
        "metrics": metrics,
        "dominant_error_type": max(errors_by_type.items(), key=lambda x: len(x[1]))[0],
        "dominant_domain": max(errors_by_domain.items(), key=lambda x: len(x[1]))[0],
        # Include sample errors for critic context
        "sample_omissions": errors_by_type["omission"][:5],
        "sample_wrong_values": errors_by_type["wrong_value"][:5],
    }
```

### Pattern 2: Hypothesis-Driven Proposal Generation

**What:** Proposals include hypothesis (why failure occurred) and expected impact
**When to use:** Generating instruction file changes based on failure analysis
**Example:**

```python
# Source: PromptAgent (ICLR 2024) - strategic planning for prompt optimization
from dataclasses import dataclass
from typing import Optional

@dataclass
class InstructionProposal:
    """A proposed change to an instruction file."""
    target_file: str                    # e.g., ".claude/instructions/verifier/instructions.md"
    current_version: str                # e.g., "v1.0.0"
    proposed_version: str               # e.g., "v1.1.0" (minor bump for enhancement)
    change_type: str                    # "add_section" | "modify_section" | "clarify_rule"

    # Hypothesis-driven
    failure_pattern: str                # What went wrong (from analysis)
    hypothesis: str                     # Why it went wrong
    proposed_change: str                # What to change (markdown diff format)
    expected_impact: str                # What should improve

    # Metadata
    affected_error_types: List[str]     # ["omission", "wrong_value"]
    affected_domains: List[str]         # ["project", "envelope"]
    estimated_f1_delta: Optional[float] = None  # +0.05 (optimistic estimate)

# Example proposal structure (what critic agent outputs)
example_proposal = InstructionProposal(
    target_file=".claude/instructions/project-extractor/instructions.md",
    current_version="v1.0.0",
    proposed_version="v1.1.0",
    change_type="add_section",
    failure_pattern="High omission rate (154/167 errors) in project fields",
    hypothesis="Extractor is not explicitly instructed to extract all project metadata fields, focusing only on obvious ones like address and climate_zone",
    proposed_change="""
## Required Project Fields Checklist

Before completing extraction, verify ALL these fields are present:

**Always Required:**
- [ ] run_id
- [ ] run_title
- [ ] run_number
- [ ] run_scope
- [ ] address
- [ ] all_orientations
- [ ] bedrooms
- [ ] attached_garage
- [ ] front_orientation

**Instructions:**
- If field is not found in document, set to null (do NOT omit)
- For run_id, run_number: check for values in CBECC output pages
- For run_scope: infer from document type (typically "Newly Constructed" for new buildings)
""",
    expected_impact="Reduce omission errors in project domain from 154 to <20, estimated F1 improvement: +0.15",
    affected_error_types=["omission"],
    affected_domains=["project"],
    estimated_f1_delta=0.15
)
```

### Pattern 3: Rich-Based Interactive Review

**What:** Present proposals in terminal with Rich tables, syntax highlighting, and prompts
**When to use:** User review workflow for accept/edit/reject decisions
**Example:**

```python
# Source: Rich documentation (rich.readthedocs.io) + GitHub Copilot CLI patterns
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

console = Console()

def present_proposal(proposal: InstructionProposal) -> str:
    """
    Present a proposal to user and get decision.

    Returns:
        "accept" | "edit" | "reject" | "skip"
    """
    # Show proposal header
    console.print(Panel.fit(
        f"[bold cyan]Proposal: {proposal.change_type}[/bold cyan]\n"
        f"Target: {proposal.target_file}\n"
        f"Version: {proposal.current_version} → {proposal.proposed_version}",
        title="Instruction Improvement Proposal"
    ))

    # Show failure analysis
    console.print("\n[bold]Failure Pattern:[/bold]")
    console.print(f"  {proposal.failure_pattern}")

    console.print("\n[bold]Hypothesis:[/bold]")
    console.print(f"  {proposal.hypothesis}")

    # Show proposed change with syntax highlighting
    console.print("\n[bold]Proposed Change:[/bold]")
    syntax = Syntax(proposal.proposed_change, "markdown", theme="monokai", line_numbers=False)
    console.print(syntax)

    # Show expected impact
    console.print(f"\n[bold]Expected Impact:[/bold]")
    console.print(f"  {proposal.expected_impact}")
    if proposal.estimated_f1_delta:
        delta_color = "green" if proposal.estimated_f1_delta > 0 else "red"
        console.print(f"  Estimated F1 Δ: [{delta_color}]{proposal.estimated_f1_delta:+.3f}[/{delta_color}]")

    # Get user decision
    console.print("\n[bold]Actions:[/bold]")
    console.print("  [a] Accept - Apply this change")
    console.print("  [e] Edit - Modify before applying")
    console.print("  [r] Reject - Skip this proposal")
    console.print("  [s] Skip - Review later")

    choice = Prompt.ask(
        "Your decision",
        choices=["a", "e", "r", "s"],
        default="a"
    )

    return {"a": "accept", "e": "edit", "r": "reject", "s": "skip"}[choice]
```

### Pattern 4: Semantic Versioning for Instruction Files

**What:** Version instruction files using semver (MAJOR.MINOR.PATCH) with header comments
**When to use:** Tracking instruction file evolution and enabling rollback
**Example:**

```python
# Source: Prompt versioning best practices (latitude-blog.ghost.io/prompt-versioning-best-practices/)
import re
from pathlib import Path
from typing import Tuple

def parse_instruction_version(file_path: Path) -> str:
    """
    Extract version from instruction file header.

    Expected format:
    # Verifier Instructions v1.2.3
    or
    # Instructions v1.0.0
    """
    content = file_path.read_text()
    match = re.search(r"#\s+.*[Ii]nstructions\s+v(\d+\.\d+\.\d+)", content)
    if match:
        return match.group(1)
    return "v0.0.0"  # Default if not found

def bump_version(current: str, bump_type: str) -> str:
    """
    Bump semantic version.

    Args:
        current: Current version (e.g., "1.2.3")
        bump_type: "major" | "minor" | "patch"

    Returns:
        New version string
    """
    major, minor, patch = map(int, current.split("."))

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump_type: {bump_type}")

def apply_version_to_content(content: str, new_version: str) -> str:
    """
    Update version number in instruction file content.

    Replaces:
    # Verifier Instructions v1.0.0
    with:
    # Verifier Instructions v1.1.0
    """
    return re.sub(
        r"(#\s+.*[Ii]nstructions\s+)v\d+\.\d+\.\d+",
        rf"\1v{new_version}",
        content
    )

# Determine bump type from change_type
BUMP_TYPE_MAP = {
    "add_section": "minor",           # New functionality
    "modify_section": "minor",        # Enhancement
    "clarify_rule": "patch",          # Clarification/fix
    "restructure": "major",           # Breaking change
    "fix_typo": "patch",              # Bug fix
}
```

### Pattern 5: Iteration Tracking with Git Commits

**What:** Each accepted proposal creates git commit with metrics delta in message
**When to use:** Tracking instruction improvements with before/after metrics
**Example:**

```python
# Source: GitOps best practices + project iteration tracking pattern
import subprocess
from pathlib import Path
from typing import Dict

def commit_instruction_change(
    proposal: InstructionProposal,
    before_metrics: Dict[str, float],
    after_metrics: Dict[str, float],
    iteration: int
) -> None:
    """
    Commit instruction file changes with metrics delta.

    Commit message format:
    feat(instructions): improve project-extractor v1.0.0 → v1.1.0

    Add required fields checklist to reduce omissions

    Metrics (iteration 2):
    - F1: 0.069 → 0.220 (+0.151)
    - Precision: 0.462 → 0.550 (+0.088)
    - Recall: 0.038 → 0.145 (+0.107)
    - Omissions: 154 → 98 (-56)
    """
    target_file = Path(proposal.target_file)
    agent_name = target_file.parent.parent.name  # Extract from path

    # Calculate deltas
    f1_delta = after_metrics["f1"] - before_metrics["f1"]
    precision_delta = after_metrics["precision"] - before_metrics["precision"]
    recall_delta = after_metrics["recall"] - before_metrics["recall"]

    omissions_before = before_metrics["errors_by_type"]["omission"]
    omissions_after = after_metrics["errors_by_type"]["omission"]
    omissions_delta = omissions_after - omissions_before

    # Build commit message
    commit_msg = f"""feat(instructions): improve {agent_name} {proposal.current_version} → {proposal.proposed_version}

{proposal.hypothesis.split('.')[0]}  # First sentence of hypothesis

Metrics (iteration {iteration}):
- F1: {before_metrics["f1"]:.3f} → {after_metrics["f1"]:.3f} ({f1_delta:+.3f})
- Precision: {before_metrics["precision"]:.3f} → {after_metrics["precision"]:.3f} ({precision_delta:+.3f})
- Recall: {before_metrics["recall"]:.3f} → {after_metrics["recall"]:.3f} ({recall_delta:+.3f})
- Omissions: {omissions_before} → {omissions_after} ({omissions_delta:+d})
"""

    # Stage and commit
    subprocess.run(["git", "add", str(target_file)], check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
```

### Pattern 6: Rollback via Iteration Folder Copy

**What:** Rollback by copying instruction files from previous iteration folder
**When to use:** When a proposal makes metrics worse, need to revert
**Example:**

```python
# Source: CONTEXT.md decision on rollback mechanism
import shutil
from pathlib import Path

def rollback_to_iteration(
    iteration: int,
    evals_dir: Path,
    instructions_dir: Path
) -> None:
    """
    Rollback instruction files to a previous iteration.

    Copies saved instruction files from iteration folder back to
    .claude/instructions/

    Args:
        iteration: Iteration number to rollback to
        evals_dir: Base evals directory
        instructions_dir: .claude/instructions directory
    """
    # Find any eval with that iteration (they all have same instruction versions)
    for eval_dir in evals_dir.iterdir():
        if not eval_dir.is_dir():
            continue

        iter_dir = eval_dir / "results" / f"iteration-{iteration:03d}"
        if not iter_dir.exists():
            continue

        changes_dir = iter_dir / "instruction-changes"
        if not changes_dir.exists():
            continue

        # Copy each saved instruction file back
        for saved_file in changes_dir.glob("*.md"):
            # Parse filename: "verifier-instructions-v1.1.0.md"
            # -> .claude/instructions/verifier/instructions.md
            parts = saved_file.stem.split("-")
            agent_name = parts[0]
            file_name = "-".join(parts[1:-1]) + ".md"  # Remove version suffix

            target_path = instructions_dir / agent_name / file_name
            shutil.copy(saved_file, target_path)
            print(f"Restored: {target_path}")

        print(f"Rolled back to iteration {iteration}")
        return

    raise ValueError(f"No iteration {iteration} found in evals")
```

### Anti-Patterns to Avoid

- **Code-aware critic:** Don't let critic read agent code or extraction implementation. Stay implementation-blind.
- **Auto-applying proposals:** Always require human review. Even with high confidence, mistakes happen.
- **Vague proposals:** Proposals must include specific text changes, not just "improve X".
- **Missing version tracking:** Every instruction file needs version header for rollback to work.
- **Overwriting previous versions:** Save old versions to iteration folder before applying changes.
- **Ignoring metrics deltas:** Always measure before/after F1 - some proposals make things worse.
- **Single-domain focus:** Critic should analyze all domains, not just one with most errors.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal formatting | ANSI escape codes | Rich library | Handles cross-platform, color schemes, table layouts |
| Diff generation | String comparison | difflib.unified_diff | Standard format, handles edge cases |
| Interactive prompts | input() loops | Rich Prompt.ask() with choices | Validation, default handling, better UX |
| Version parsing | String splitting | regex with validation | Handles edge cases (v prefix, missing parts) |
| Git operations | Manual file tracking | Git commands via subprocess | Atomic commits, built-in conflict handling |
| File copying | Manual read/write | shutil.copy | Preserves metadata, handles large files |
| JSON schema validation | Manual dict checking | Pydantic (if needed) | Already used in project |

**Key insight:** The improvement loop workflow is well-trodden ground in 2026. Use established patterns (semantic versioning, git-based rollback, Rich for terminal UI) rather than inventing custom approaches.

## Common Pitfalls

### Pitfall 1: Critic Proposes Code Changes Instead of Instruction Changes

**What goes wrong:** Critic suggests modifying Python code or agent definitions instead of instruction files
**Why it happens:** Critic doesn't understand the thin-agent architecture where behavior is in instructions
**How to avoid:**
- Explicitly constrain critic: "You may ONLY propose changes to files in .claude/instructions/"
- Provide critic with list of valid target files (instruction files only)
- Validate proposals: reject any targeting .py files or agent definitions
**Warning signs:** Proposals targeting src/*.py or .claude/agents/*.md

### Pitfall 2: Overfitting to Single Eval Case

**What goes wrong:** Proposals improve one eval but hurt aggregate performance
**Why it happens:** Critic analyzes single eval in isolation, doesn't consider generalization
**How to avoid:**
- Run critic on aggregate results across all 5 evals, not individual evals
- After applying proposal, re-run ALL evals to measure aggregate F1 delta
- Reject proposals that improve one eval but decrease macro-F1
**Warning signs:** One eval improves significantly but macro-F1 stays flat or decreases

### Pitfall 3: Proposal Doesn't Include Concrete Text

**What goes wrong:** Proposal says "add more detail to extraction instructions" without specific text
**Why it happens:** Critic generates high-level suggestions rather than actionable diffs
**How to avoid:**
- Critic prompt must require: "Provide EXACT text to add/modify in markdown format"
- Show critic examples of good proposals with full markdown sections
- Validation step: reject proposals without concrete proposed_change text
**Warning signs:** Proposals with change_type but empty/vague proposed_change field

### Pitfall 4: Version Drift Across Instruction Files

**What goes wrong:** Some instruction files updated to v1.2.0, others still v1.0.0, unclear which versions work together
**Why it happens:** No tracking of which instruction versions were used in each iteration
**How to avoid:**
- Save ALL current instruction files to iteration folder, not just changed ones
- Track instruction versions in eval-results.json metadata
- Rollback restores complete snapshot, not individual files
**Warning signs:** Rollback works for some agents but others behave inconsistently

### Pitfall 5: Metrics Regression Goes Unnoticed

**What goes wrong:** Apply proposal, don't re-run verification, ship regression
**Why it happens:** Assumed proposal would improve metrics without validation
**How to avoid:**
- ALWAYS run extract + verify after applying proposal
- Compare before/after metrics, require F1 improvement to keep change
- Auto-rollback if F1 decreases by >0.01
**Warning signs:** Iteration N has lower F1 than iteration N-1

### Pitfall 6: Edit Workflow Complexity

**What goes wrong:** User chooses "Edit", workflow doesn't gracefully handle text editing
**Why it happens:** Spawning $EDITOR requires temp files, capturing edits is tricky
**How to avoid:**
- For MVP: "Edit" opens proposal in $EDITOR via tempfile, reads back changes
- Alternative: Skip "Edit" option, user can manually edit and re-run
- CONTEXT.md leaves this to Claude's discretion - simplest viable approach wins
**Warning signs:** Edit flow crashes or loses user's edits

### Pitfall 7: Concurrent Instruction Modifications

**What goes wrong:** Two proposals both modify same instruction file section, second overwrites first
**Why it happens:** Applying proposals sequentially without awareness of previous changes
**How to avoid:**
- Apply one proposal at a time with re-extraction before next proposal
- OR: Detect conflicts (same file, overlapping line ranges) and warn user
- For Phase 5 (manual): One proposal per iteration is sufficient
**Warning signs:** Second proposal's changes don't appear in final file

## Code Examples

Verified patterns from official sources:

### Complete Critic Workflow

```python
# Source: Synthesized from AgentDevel, PromptWizard, Rich docs
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from rich.console import Console
from rich.prompt import Prompt

console = Console()

def run_improvement_iteration(
    eval_ids: List[str],
    evals_dir: Path,
    instructions_dir: Path,
    iteration: int
) -> Optional[InstructionProposal]:
    """
    Run one improvement iteration:
    1. Collect verification results from all evals
    2. Invoke critic agent to analyze and propose changes
    3. Present proposal to user for review
    4. If accepted, apply changes and re-run extraction

    Returns:
        Accepted proposal or None if rejected/skipped
    """
    # Step 1: Collect verification results
    console.print(f"\n[bold cyan]Iteration {iteration}: Analyzing Results[/bold cyan]")

    all_results = []
    for eval_id in eval_ids:
        latest_iter = find_latest_iteration(evals_dir / eval_id)
        results_path = evals_dir / eval_id / "results" / f"iteration-{latest_iter:03d}" / "eval-results.json"
        if results_path.exists():
            all_results.append(json.loads(results_path.read_text()))

    if not all_results:
        console.print("[red]No evaluation results found[/red]")
        return None

    # Step 2: Analyze failure patterns
    console.print("Analyzing failure patterns across all evals...")
    analysis = aggregate_failure_analysis(all_results)

    # Step 3: Invoke critic agent
    console.print("Invoking critic agent to generate proposal...")
    proposal_json = invoke_critic_agent(analysis, instructions_dir)
    proposal = parse_proposal(proposal_json)

    if not proposal:
        console.print("[yellow]Critic did not generate a proposal[/yellow]")
        return None

    # Step 4: Present to user
    decision = present_proposal(proposal)

    if decision == "accept":
        console.print("[green]Proposal accepted![/green]")
        return proposal
    elif decision == "edit":
        edited_proposal = edit_proposal(proposal)
        if edited_proposal:
            console.print("[green]Edited proposal accepted![/green]")
            return edited_proposal
        else:
            console.print("[yellow]Edit cancelled[/yellow]")
            return None
    elif decision == "reject":
        console.print("[red]Proposal rejected[/red]")
        return None
    else:  # skip
        console.print("[yellow]Proposal skipped[/yellow]")
        return None

def aggregate_failure_analysis(eval_results: List[Dict]) -> Dict[str, Any]:
    """Aggregate failure patterns across all evals."""
    total_discrepancies = sum(len(r["discrepancies"]) for r in eval_results)

    # Aggregate error types
    total_errors_by_type = {
        "omission": 0,
        "hallucination": 0,
        "wrong_value": 0,
        "format_error": 0
    }

    for result in eval_results:
        for error_type, count in result["metrics"]["errors_by_type"].items():
            total_errors_by_type[error_type] += count

    # Aggregate by domain
    all_discrepancies = []
    for result in eval_results:
        all_discrepancies.extend(result["discrepancies"])

    errors_by_domain = {}
    for d in all_discrepancies:
        domain = d["field_path"].split(".")[0].split("[")[0]
        errors_by_domain[domain] = errors_by_domain.get(domain, 0) + 1

    # Calculate aggregate metrics
    total_f1 = sum(r["metrics"]["f1"] for r in eval_results) / len(eval_results)

    return {
        "num_evals": len(eval_results),
        "total_discrepancies": total_discrepancies,
        "aggregate_f1": total_f1,
        "errors_by_type": total_errors_by_type,
        "errors_by_domain": errors_by_domain,
        "dominant_error_type": max(total_errors_by_type.items(), key=lambda x: x[1])[0],
        "dominant_domain": max(errors_by_domain.items(), key=lambda x: x[1])[0],
        # Sample errors for critic context
        "sample_discrepancies": all_discrepancies[:20],
    }
```

### Proposal Application with Snapshot

```python
# Source: Git-based versioning + iteration tracking patterns
from pathlib import Path
import shutil
import json

def apply_proposal(
    proposal: InstructionProposal,
    instructions_dir: Path,
    iteration: int,
    evals_dir: Path
) -> None:
    """
    Apply proposal to instruction file with version bump.

    Process:
    1. Read current instruction file
    2. Save snapshot to all iteration folders
    3. Apply proposed change
    4. Bump version in header
    5. Write updated file
    """
    target_path = Path(proposal.target_file)

    # Read current content
    current_content = target_path.read_text()
    current_version = parse_instruction_version(target_path)

    # Save snapshot to iteration folders (before applying change)
    for eval_dir in evals_dir.iterdir():
        if not eval_dir.is_dir():
            continue

        iter_dir = eval_dir / "results" / f"iteration-{iteration:03d}"
        if not iter_dir.exists():
            continue

        changes_dir = iter_dir / "instruction-changes"
        changes_dir.mkdir(exist_ok=True)

        # Save with version in filename
        agent_name = target_path.parent.name
        file_name = target_path.stem
        snapshot_name = f"{agent_name}-{file_name}-{current_version}.md"
        snapshot_path = changes_dir / snapshot_name
        snapshot_path.write_text(current_content)

    # Apply change (simple append for add_section, more complex for modify)
    if proposal.change_type == "add_section":
        new_content = current_content.rstrip() + "\n\n" + proposal.proposed_change
    elif proposal.change_type == "modify_section":
        # For modify, proposed_change includes section header
        # This is simplified - production would need smarter section replacement
        new_content = current_content + "\n\n" + proposal.proposed_change + "\n\n(TODO: Replace existing section)"
    else:
        new_content = current_content + "\n\n" + proposal.proposed_change

    # Bump version
    new_version = proposal.proposed_version
    new_content = apply_version_to_content(new_content, new_version)

    # Write updated file
    target_path.write_text(new_content)

    print(f"Applied: {target_path} ({current_version} → {new_version})")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual prompt tweaking | LLM-powered critic analysis | 2024-2025 | Systematic identification of failure patterns |
| Code-aware optimization | Implementation-blind critic | Jan 2026 (AgentDevel) | More generalizable improvements |
| Simple prompt versioning | Semantic versioning with git | 2025-2026 | Structured rollback, better tracking |
| Batch processing | Interactive terminal review | 2026 | Human judgment on risky changes |
| Git revert | Iteration folder snapshots | User decision | Simpler rollback without git history complexity |
| Text file diffs | Rich syntax highlighting | 2024-2026 | Better proposal readability |

**Deprecated/outdated:**
- **Direct prompt editing:** Manual tweaking without failure analysis is less effective
- **Auto-applying all proposals:** High error rate, human review is critical
- **Git branch per iteration:** Folder-based tracking simpler for this use case
- **Complex TUI frameworks:** Rich prompts sufficient, Textual overkill

## Open Questions

Things that couldn't be fully resolved:

1. **Edit Workflow Implementation**
   - What we know: User wants ability to edit proposals before accepting
   - What's unclear: Best UX (temp file + $EDITOR vs inline paste vs skip entirely)
   - Recommendation: Start with temp file + $EDITOR, simplest familiar workflow

2. **Proposal Scope (Single vs Batch)**
   - What we know: Each proposal targets one instruction file
   - What's unclear: Should critic generate multiple proposals per iteration?
   - Recommendation: One proposal per iteration for Phase 5 (manual), batch for Phase 6 (auto)

3. **Critic Invocation Trigger**
   - What we know: User manually triggers improvement loop
   - What's unclear: Should critic auto-run after each extraction? Or on-demand only?
   - Recommendation: On-demand via CLI command (improve), not automatic

4. **Rollback Granularity**
   - What we know: Rollback by copying instruction files from iteration folder
   - What's unclear: Rollback all instruction files or only changed ones?
   - Recommendation: Rollback all (complete snapshot) to avoid version drift

5. **Confidence Thresholds for Auto-Accept**
   - What we know: Phase 5 is manual (human-in-loop)
   - What's unclear: Should high-confidence proposals auto-apply?
   - Recommendation: No auto-accept in Phase 5, leave for Phase 6

6. **Multi-Eval vs Single-Eval Analysis**
   - What we know: Critic should analyze aggregate results to avoid overfitting
   - What's unclear: Should critic also show per-eval breakdowns?
   - Recommendation: Aggregate analysis primary, per-eval details in verbose mode

## Sources

### Primary (HIGH confidence)
- [AgentDevel: Reframing Self-Evolving LLM Agents](https://arxiv.org/abs/2601.04620) - Implementation-blind critic, January 2026
- [PromptAgent: Strategic Planning with Language Models](https://openreview.net/forum?id=22pyNMuIoa) - ICLR 2024, hypothesis-driven optimization
- [RISE: Recursive Introspection for Self-Improvement](https://proceedings.neurips.cc/paper_files/paper/2024/file/639d992f819c2b40387d4d5170b8ffd7-Paper-Conference.pdf) - NeurIPS 2024
- [Rich Library Documentation](https://rich.readthedocs.io/en/stable/prompt.html) - Interactive prompts, v14.1.0
- [Claude Prompt Engineering Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) - Official Anthropic docs

### Secondary (MEDIUM confidence)
- [Prompt Versioning Best Practices](https://latitude-blog.ghost.io/blog/prompt-versioning-best-practices/) - Semantic versioning patterns
- [GitHub Copilot CLI Agentic Workflows](https://github.blog/ai-and-ml/github-copilot/power-agentic-workflows-in-your-terminal-with-github-copilot-cli/) - Terminal review patterns, Jan 2026
- [PromptWizard: Feedback-Driven Self-Evolving Prompts](https://www.microsoft.com/en-us/research/blog/promptwizard-the-future-of-prompt-optimization-through-feedback-driven-self-evolving-prompts/) - Microsoft Research, Jan 2025
- [GitOps Rollback Strategies](https://www.aviator.co/blog/automated-failover-and-git-rollback-strategies-with-gitops-and-argo-rollouts/) - Git-based config versioning
- [Agentic AI Design Patterns 2026](https://medium.com/@dewasheesh.rana/agentic-ai-design-patterns-2026-ed-e3a5125162c5) - Reflection pattern
- [Claude 4.x Prompt Engineering Guide](https://ai-engineering-trend.medium.com/claude-4-x-prompt-engineering-a-practical-guide-for-medium-developers-4d1068ba0100) - Jan 2026

### Tertiary (LOW confidence)
- [Top 5 Prompt Versioning Tools for Enterprise AI 2026](https://www.getmaxim.ai/articles/top-5-prompt-versioning-tools-for-enterprise-ai-teams-in-2026/) - Commercial tools overview
- [AI Code Review Automation with LLMs](https://kinde.com/learn/ai-for-software-engineering/code-reviews/building-your-personal-ai-code-review-bot-github-actions-llm-integration/) - Review workflow patterns
- [Meta-Prompting: LLMs Crafting Their Own Prompts](https://intuitionlabs.ai/articles/meta-prompting-llm-self-optimization) - Self-optimization techniques

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Rich library well-documented, git commands standard, existing patterns from Phase 3-4
- Failure analysis patterns: HIGH - AgentDevel (Jan 2026) validates implementation-blind approach
- Proposal format: MEDIUM - Structure clear, but exact schema needs validation
- Interactive review: HIGH - Rich library capabilities verified, GitHub Copilot CLI demonstrates similar patterns
- Versioning: MEDIUM-HIGH - Semantic versioning standard, but instruction file application needs testing
- Rollback: MEDIUM - Folder-based approach simpler than git, but edge cases may emerge

**Research date:** 2026-02-03
**Valid until:** 2026-02-24 (21 days - fast-moving domain with recent 2026 research)

**Key uncertainties requiring validation:**
1. Edit workflow UX - needs user testing to determine best approach
2. Proposal application logic for "modify_section" - may need smarter text replacement
3. Optimal iteration folder structure - may evolve after first few iterations
4. Critic prompt engineering - will require iteration to produce actionable proposals
5. Multi-proposal handling - deferred to Phase 6, but may inform Phase 5 design
