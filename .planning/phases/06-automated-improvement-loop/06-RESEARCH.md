# Phase 6: Automated Improvement Loop - Research

**Researched:** 2026-02-04
**Domain:** Automated iterative improvement loops with convergence detection
**Confidence:** MEDIUM-HIGH

## Summary

Automated improvement loops require orchestrating multiple subprocess calls (extraction, verification, proposal generation, application) in a continuous feedback cycle until convergence or target metrics are achieved. The research focused on five key areas: loop orchestration patterns, stop condition strategies, iteration history tracking, subprocess error handling, and progress visualization.

The standard approach for Python automation loops is to use `subprocess.run()` with proper error handling, Rich for CLI progress display, and file-based JSON storage for iteration history. Stop conditions should include both target achievement (F1 >= 0.90) and plateau detection (no improvement for K iterations) to prevent infinite loops. State must be checkpointed after each iteration to enable resume and rollback capabilities.

The existing Phase 5 implementation already provides the building blocks (critic invocation, proposal application, metrics tracking, rollback). Phase 6 extends this with loop control logic, plateau detection, progress tracking, and comprehensive iteration history.

**Primary recommendation:** Build a `improve loop` command that wraps the existing `improve` workflow, adds stop condition checks, tracks iteration metrics in a centralized history file, and uses Rich progress bars for long-running automation.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess | stdlib | Process orchestration | Official Python approach for spawning subprocesses |
| Rich | 13.x-14.x | CLI progress/UI | Already decided in Phase 5, best-in-class terminal UI |
| Click | 8.x | CLI framework | Already used in Phase 5, industry standard for Python CLIs |
| json | stdlib | State persistence | Lightweight, human-readable, no dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tqdm | 4.x | Simple progress bars | Alternative to Rich (not recommended, stick with Rich) |
| alive-progress | 3.x | Animated progress | Alternative to Rich (not recommended, stick with Rich) |
| pathlib | stdlib | File path handling | Already used throughout project |
| dataclasses | stdlib | Structured data | Already used for InstructionProposal |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON files | SQLite | SQLite adds dependency and complexity, JSON sufficient for 5-100 iterations |
| JSON files | Pickle | Pickle not human-readable, harder to debug iteration state |
| subprocess | asyncio | Asyncio adds complexity, subprocess calls are already fast enough |
| File-based | MLflow/W&B | Enterprise experiment tracking overkill for simple F1 improvement loop |

**Installation:**
```bash
# No new installations needed - all dependencies already in place from Phase 5
# Rich, Click, and stdlib only
```

## Architecture Patterns

### Recommended Project Structure
```
src/improvement/
├── cli.py              # Existing CLI with improve, apply, rollback commands
├── loop.py             # NEW: Loop orchestration with stop conditions
├── history.py          # NEW: Iteration history tracking and persistence
├── critic.py           # Existing: Critic invocation
├── apply.py            # Existing: Proposal application
└── review.py           # Existing: Interactive review UI
```

### Pattern 1: Loop Controller with Stop Conditions

**What:** Main loop that orchestrates improve iterations and evaluates stop conditions
**When to use:** When automating the manual improve workflow for N iterations

**Example:**
```python
# Source: Research synthesis from PyTorch Lightning Early Stopping patterns
from pathlib import Path
from typing import Optional, Dict, List
import json

class ImprovementLoop:
    """Orchestrates automated improvement iterations with stop conditions."""

    def __init__(
        self,
        evals_dir: Path,
        max_iterations: int = 100,
        target_f1: float = 0.90,
        plateau_patience: int = 5,
        min_improvement: float = 0.001
    ):
        self.evals_dir = evals_dir
        self.max_iterations = max_iterations
        self.target_f1 = target_f1
        self.plateau_patience = plateau_patience
        self.min_improvement = min_improvement
        self.history: List[Dict] = []

    def should_stop(self) -> tuple[bool, str]:
        """Evaluate all stop conditions.

        Returns:
            (should_stop, reason)
        """
        if not self.history:
            return False, ""

        current_f1 = self.history[-1]["metrics"]["f1"]

        # Condition 1: Target achieved
        if current_f1 >= self.target_f1:
            return True, f"Target F1 {self.target_f1:.3f} achieved"

        # Condition 2: Max iterations reached
        if len(self.history) >= self.max_iterations:
            return True, f"Max iterations ({self.max_iterations}) reached"

        # Condition 3: Plateau detection (no improvement for K iterations)
        if len(self.history) >= self.plateau_patience:
            recent = self.history[-self.plateau_patience:]
            best_recent_f1 = max(h["metrics"]["f1"] for h in recent)
            improvement = best_recent_f1 - recent[0]["metrics"]["f1"]

            if improvement < self.min_improvement:
                return True, f"Plateau detected: no improvement for {self.plateau_patience} iterations"

        return False, ""

    def run(self):
        """Execute improvement loop until stop condition met."""
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        from rich.console import Console

        console = Console()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            task = progress.add_task(
                f"[cyan]Improvement loop (target F1: {self.target_f1:.3f})",
                total=self.max_iterations
            )

            while True:
                # Check stop conditions
                should_stop, reason = self.should_stop()
                if should_stop:
                    console.print(f"\n[green]✓ Loop stopped: {reason}[/green]")
                    break

                # Run one improve iteration
                iteration_num = len(self.history) + 1
                console.print(f"\n[bold]Iteration {iteration_num}[/bold]")

                success, metrics = self._run_iteration()

                if success:
                    self.history.append({
                        "iteration": iteration_num,
                        "metrics": metrics,
                        "timestamp": datetime.now().isoformat()
                    })
                    progress.update(task, advance=1)
                else:
                    console.print("[red]Iteration failed, stopping loop[/red]")
                    break
```

### Pattern 2: Iteration History Tracking

**What:** Centralized JSON file tracking all iteration metrics and metadata
**When to use:** For resume capability and historical analysis

**Example:**
```python
# Source: Research on Python JSON persistence best practices
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime

class IterationHistory:
    """Tracks iteration history with file-based persistence."""

    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.iterations: List[Dict] = []
        self._load()

    def _load(self):
        """Load existing history from file."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                data = json.load(f)
                self.iterations = data.get("iterations", [])

    def save(self):
        """Persist history to file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w") as f:
            json.dump({
                "iterations": self.iterations,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)

    def add_iteration(
        self,
        iteration_num: int,
        metrics: Dict,
        proposal: Optional[Dict] = None,
        status: str = "success"
    ):
        """Record a completed iteration."""
        self.iterations.append({
            "iteration": iteration_num,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "proposal": proposal,
            "status": status
        })
        self.save()

    def get_latest_metrics(self) -> Optional[Dict]:
        """Get metrics from most recent iteration."""
        if not self.iterations:
            return None
        return self.iterations[-1]["metrics"]

    def get_best_iteration(self) -> Optional[Dict]:
        """Find iteration with highest F1 score."""
        if not self.iterations:
            return None
        return max(self.iterations, key=lambda x: x["metrics"]["f1"])

    def get_plateau_iterations(self, patience: int = 5, min_delta: float = 0.001) -> int:
        """Count iterations since last significant improvement."""
        if len(self.iterations) < 2:
            return 0

        best_f1 = max(it["metrics"]["f1"] for it in self.iterations)

        # Count backward from end
        count = 0
        for it in reversed(self.iterations):
            if best_f1 - it["metrics"]["f1"] < min_delta:
                count += 1
            else:
                break

        return count
```

### Pattern 3: Resume from Checkpoint

**What:** Resume loop from specific iteration using saved state
**When to use:** After manual inspection or when loop interrupted

**Example:**
```python
# Source: Research on LangGraph checkpointing patterns adapted for file-based state
def resume_loop(
    evals_dir: Path,
    from_iteration: Optional[int] = None,
    max_iterations: int = 100,
    target_f1: float = 0.90
):
    """Resume improvement loop from a previous iteration.

    Args:
        evals_dir: Evals directory path
        from_iteration: Specific iteration to resume from (None = latest)
        max_iterations: Additional iterations to run
        target_f1: Target F1 score
    """
    history_file = evals_dir.parent / ".improvement-history.json"
    history = IterationHistory(history_file)

    if not history.iterations:
        print("No previous iterations found. Starting fresh loop.")
        return run_loop(evals_dir, max_iterations, target_f1)

    # Determine resume point
    if from_iteration is None:
        resume_from = len(history.iterations)
        print(f"Resuming from latest iteration: {resume_from}")
    else:
        if from_iteration > len(history.iterations):
            print(f"Error: Iteration {from_iteration} not found")
            return
        resume_from = from_iteration
        # Truncate history to resume point
        history.iterations = history.iterations[:from_iteration]
        history.save()
        print(f"Resuming from iteration {resume_from}")

    # Continue loop with adjusted max
    remaining_iterations = max_iterations - resume_from
    loop = ImprovementLoop(
        evals_dir,
        max_iterations=remaining_iterations,
        target_f1=target_f1
    )
    loop.history = history.iterations
    loop.run()
```

### Anti-Patterns to Avoid

- **Infinite loops without stop conditions:** Always include max_iterations as safety valve even if targeting F1 score
- **No intermediate checkpointing:** Save iteration state immediately after each iteration, not at end of loop
- **Silent subprocess failures:** Always check return codes and capture stderr for debugging
- **Blocking on user input in automated mode:** Automated loop must run unattended, use separate interactive command
- **Not tracking negative iterations:** Log failed iterations to understand what went wrong
- **Hardcoded paths:** Use configurable paths for history file and evals directory

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bars | Custom print() with \r carriage return | Rich Progress API | Rich handles refresh rate, nesting, concurrent tasks, auto-cleanup |
| Subprocess error handling | Manual returncode checking | subprocess.run(check=True, capture_output=True) | Built-in exception raising, proper output capture |
| Stop condition logic | Multiple if statements scattered | Centralized should_stop() method | Single source of truth, easier to test and modify |
| JSON schema validation | Manual dict key checking | dataclasses with type hints | Automatic validation, better IDE support |
| Iteration metrics storage | CSV or custom format | JSON with structured schema | Human-readable, Python native, easy to query |
| Resume logic | Manual state reconstruction | Load history, truncate, continue | Preserves full audit trail with timestamps |

**Key insight:** Automation reliability comes from proper error handling and state persistence, not clever optimizations. Use boring, proven patterns (subprocess.run, JSON files, explicit stop conditions) rather than creative solutions.

## Common Pitfalls

### Pitfall 1: Plateau False Positives from Noise

**What goes wrong:** Metrics fluctuate slightly between iterations (±0.001), triggering premature plateau detection

**Why it happens:** Improvements may be genuinely small but cumulative; F1 scores naturally have some variance

**How to avoid:**
- Set `min_improvement` threshold appropriate to metric precision (e.g., 0.005 for F1 scores)
- Require improvement over *any* of last K iterations, not just sequential improvement
- Log warning when plateau detected but allow manual override to continue

**Warning signs:** Loop stops after only 3-4 iterations despite clear improvement trend

### Pitfall 2: Subprocess Timeouts Too Aggressive

**What goes wrong:** Extraction or verification subprocess killed due to timeout, causing loop to fail

**Why it happens:** Some eval cases take longer to process, especially PDFs with many pages

**How to avoid:**
- Set conservative timeouts (5+ minutes for extraction, 3+ minutes for verification)
- Log timeout separately from failure
- Consider retry with longer timeout before failing entire loop

**Warning signs:** Subprocess TimeoutExpired exceptions in logs

### Pitfall 3: No Disk Space Handling

**What goes wrong:** Loop generates many iteration snapshots (instruction files, eval results), fills disk, crashes

**Why it happens:** Each iteration saves snapshots across N evals, can be 50+ files per iteration

**How to avoid:**
- Check disk space before starting loop
- Implement cleanup policy (keep only last 10 iterations, or iterations that improved F1)
- Provide --cleanup flag to prune old iteration directories

**Warning signs:** OSError: [Errno 28] No space left on device

### Pitfall 4: Git Merge Conflicts in Instruction Files

**What goes wrong:** Automated commits modify instruction files, creating merge conflicts if branch diverges

**Why it happens:** Loop commits after each iteration; if user pulls changes, instruction files conflict

**How to avoid:**
- Check git status before starting loop, warn if not up-to-date
- Use feature branch for automated improvement
- Provide --no-commit mode for dry-run testing

**Warning signs:** Git commit fails with "conflict" error

### Pitfall 5: No Progress Visibility in Long Loops

**What goes wrong:** User runs 100-iteration loop, sees no output for minutes, thinks it's hung

**Why it happens:** Subprocess calls are silent, no feedback between iterations

**How to avoid:**
- Use Rich Progress with spinner to show activity
- Log each subprocess step ("Running extraction...", "Running verification...")
- Show intermediate metrics after each iteration
- Provide --verbose flag for detailed logging

**Warning signs:** User Ctrl+C kills loop thinking it's frozen

### Pitfall 6: Proposal Rejection Stops Loop

**What goes wrong:** Critic generates invalid proposal or no proposal, loop exits instead of continuing

**Why it happens:** Critic may not find improvement opportunity at current iteration

**How to avoid:**
- Treat "no proposal" as non-failure, continue loop
- Implement skip/retry logic when proposal parsing fails
- Count consecutive failures, stop only after 3-5 failures

**Warning signs:** Loop stops after 1-2 iterations with "no proposal" message

## Code Examples

Verified patterns from official sources:

### Subprocess Error Handling in Loop Context

```python
# Source: Python subprocess documentation - https://docs.python.org/3/library/subprocess.html
import subprocess
from pathlib import Path

def run_extraction(evals_dir: Path, timeout: int = 300) -> bool:
    """Run extraction with proper error handling.

    Returns True on success, False on failure.
    """
    try:
        result = subprocess.run(
            ["python3", "-m", "agents", "extract-all", "--evals-dir", str(evals_dir), "--force"],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            cwd=evals_dir.parent
        )
        return True

    except subprocess.TimeoutExpired as e:
        print(f"[red]Extraction timed out after {e.timeout}s[/red]")
        print(f"Output so far: {e.output}")
        return False

    except subprocess.CalledProcessError as e:
        print(f"[red]Extraction failed with exit code {e.returncode}[/red]")
        print(f"stderr: {e.stderr}")
        return False

    except FileNotFoundError:
        print("[red]python3 or agents module not found[/red]")
        return False
```

### Rich Progress with Nested Tasks

```python
# Source: Rich documentation - https://rich.readthedocs.io/en/stable/progress.html
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console

def run_loop_with_progress(max_iterations: int):
    """Run loop with detailed progress tracking."""
    console = Console()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        # Overall loop progress
        loop_task = progress.add_task(
            "[cyan]Improvement loop",
            total=max_iterations
        )

        for i in range(max_iterations):
            # Nested task for current iteration
            iter_task = progress.add_task(
                f"[green]Iteration {i+1}",
                total=3  # 3 steps: extract, verify, apply
            )

            # Step 1: Extract
            progress.update(iter_task, description=f"[green]Iteration {i+1}: Extracting")
            run_extraction()
            progress.update(iter_task, advance=1)

            # Step 2: Verify
            progress.update(iter_task, description=f"[green]Iteration {i+1}: Verifying")
            run_verification()
            progress.update(iter_task, advance=1)

            # Step 3: Apply proposal
            progress.update(iter_task, description=f"[green]Iteration {i+1}: Applying")
            apply_proposal()
            progress.update(iter_task, advance=1)

            # Complete iteration
            progress.update(loop_task, advance=1)
            progress.remove_task(iter_task)
```

### Plateau Detection Algorithm

```python
# Source: PyTorch ReduceLROnPlateau pattern - https://pytorch.org/docs/stable/optim.html
def detect_plateau(
    history: List[Dict],
    patience: int = 5,
    min_delta: float = 0.001,
    mode: str = "max"
) -> bool:
    """Detect if metric has plateaued.

    Args:
        history: List of iteration dicts with 'metrics' field
        patience: Number of iterations without improvement
        min_delta: Minimum change to qualify as improvement
        mode: 'max' for metrics like F1, 'min' for loss

    Returns:
        True if plateaued, False otherwise
    """
    if len(history) < patience + 1:
        return False

    # Get metric values for last patience+1 iterations
    recent = history[-(patience + 1):]
    metric_values = [it["metrics"]["f1"] for it in recent]

    # Find best value in recent history
    if mode == "max":
        best_value = max(metric_values)
        best_idx = metric_values.index(best_value)
    else:
        best_value = min(metric_values)
        best_idx = metric_values.index(best_value)

    # Check if best was more than patience iterations ago
    iterations_since_best = len(metric_values) - 1 - best_idx

    if iterations_since_best >= patience:
        # Verify improvement wasn't just noise
        if mode == "max":
            improvement = best_value - metric_values[0]
        else:
            improvement = metric_values[0] - best_value

        if improvement < min_delta:
            return True  # Plateaued

    return False
```

### Click Command with Rich Integration

```python
# Source: Click documentation and Rich integration patterns
import click
from rich.console import Console

console = Console()

@click.command()
@click.option(
    "--max-iterations",
    type=int,
    default=100,
    help="Maximum iterations to run"
)
@click.option(
    "--target-f1",
    type=float,
    default=0.90,
    help="Target F1 score to achieve"
)
@click.option(
    "--patience",
    type=int,
    default=5,
    help="Stop if no improvement for N iterations"
)
@click.option(
    "--resume-from",
    type=int,
    default=None,
    help="Resume from specific iteration"
)
def loop(max_iterations: int, target_f1: float, patience: int, resume_from: int):
    """Run automated improvement loop until convergence."""
    try:
        console.print(f"\n[bold cyan]Automated Improvement Loop[/bold cyan]")
        console.print(f"Target F1: {target_f1:.3f}")
        console.print(f"Max iterations: {max_iterations}")
        console.print(f"Plateau patience: {patience}\n")

        loop = ImprovementLoop(
            evals_dir=Path("evals"),
            max_iterations=max_iterations,
            target_f1=target_f1,
            plateau_patience=patience
        )

        if resume_from:
            loop.resume(resume_from)
        else:
            loop.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Loop interrupted by user[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"\n[red]Loop failed: {e}[/red]")
        raise click.Abort()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual iteration tracking in spreadsheets | File-based JSON history with structured schema | 2024-2025 | Enables programmatic resume and analysis |
| Simple iteration counters | Multi-condition stop logic (target + plateau + max) | 2025 | Prevents wasted compute on converged models |
| Print statements for progress | Rich Progress API with nested tasks | 2023-2024 | Better UX for long-running automation |
| Kill process on timeout | Graceful timeout handling with cleanup | 2024+ | More reliable subprocess orchestration |
| Implicit subprocess errors | Explicit check=True with exception types | Always | Better debugging and error recovery |

**Deprecated/outdated:**
- **tqdm for new projects**: Rich supersedes tqdm with better terminal handling and styling (though tqdm still widely used)
- **Shell scripts for orchestration**: Python subprocess with proper error handling more maintainable than bash
- **SQLite for simple iteration tracking**: JSON sufficient for 5-100 iterations, SQLite overhead not justified
- **asyncio for subprocess**: subprocess.run() sufficient for sequential workflow, asyncio adds complexity

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal patience value for plateau detection**
   - What we know: PyTorch uses 5-10 as default, depends on metric variance
   - What's unclear: Appropriate value for F1 scores in extraction domain
   - Recommendation: Start with patience=5, make configurable flag, adjust based on observation

2. **Whether to auto-resume after failure**
   - What we know: Failure could be transient (network) or permanent (disk full)
   - What's unclear: Safe heuristic for when to retry vs. stop
   - Recommendation: Manual resume only, avoid auto-retry that could infinite loop

3. **Cleanup policy for old iterations**
   - What we know: Each iteration creates snapshots across N evals
   - What's unclear: How many iterations to keep, whether to archive or delete
   - Recommendation: Keep all iterations initially, add --cleanup command later if disk becomes issue

4. **Handling critic failures mid-loop**
   - What we know: Critic may timeout or produce invalid JSON
   - What's unclear: Should loop skip iteration and continue, or stop entirely?
   - Recommendation: Skip iteration, log failure, stop after 3 consecutive failures

## Sources

### Primary (HIGH confidence)
- Python subprocess documentation - https://docs.python.org/3/library/subprocess.html
- Rich Progress API documentation - https://rich.readthedocs.io/en/stable/progress.html
- Click documentation (8.3.x) - https://click.palletsprojects.com/en/stable/
- Python logging best practices - https://docs.python.org/3/howto/logging.html

### Secondary (MEDIUM confidence)
- [PyTorch Lightning Early Stopping](https://lightning.ai/docs/pytorch/stable/common/early_stopping.html) - Early stopping patterns
- [PyTorch ReduceLROnPlateau Guide](https://www.codegenes.net/blog/pytorch-reducelronplateau/) - Plateau detection with patience parameter
- [Python subprocess best practices (Real Python)](https://realpython.com/python-subprocess/) - Subprocess orchestration
- [LangGraph Checkpointing](https://reference.langchain.com/python/langgraph/checkpoints/) - State persistence patterns
- [Click composable CLIs (Better Stack)](https://betterstack.com/community/guides/scaling-python/click-explained/) - CLI best practices
- [Python logging best practices 2026 (Carmatec)](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/) - Logging patterns
- [tqdm progress bars](https://github.com/tqdm/tqdm) - Progress tracking (superseded by Rich)
- [alive-progress](https://pypi.org/project/alive-progress/) - Alternative progress library

### Tertiary (LOW confidence)
- [ML experiment tracking tools comparison](https://dagshub.com/blog/best-8-experiment-tracking-tools-for-machine-learning-2023/) - Context on enterprise tools (overkill for this use case)
- [MLflow vs Weights & Biases](https://neptune.ai/vs/wandb-mlflow) - Enterprise alternatives not needed
- [Python checkpointing libraries](https://github.com/a-rahimi/python-checkpointing) - Complex checkpointing (file-based JSON sufficient)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already decided in Phase 5 or stdlib
- Architecture: MEDIUM-HIGH - Patterns synthesized from multiple sources, need validation in practice
- Pitfalls: MEDIUM - Based on common subprocess/automation issues, some domain-specific (plateau detection thresholds)
- Stop conditions: HIGH - Well-established in ML training loops, directly applicable
- Progress tracking: HIGH - Rich documentation comprehensive and current

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - stable domain, stdlib-based)

**Key assumptions:**
- Loop will run 5-50 iterations typically, not 1000s (affects storage choice)
- Subprocess calls (extraction, verification) complete in 1-5 minutes each
- User can interrupt and resume manually (no requirement for fully unattended operation)
- Git repository is main branch or feature branch (no complex multi-branch scenarios)
- Disk space not severely constrained (can store 50+ iteration snapshots)
