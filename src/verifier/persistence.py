"""Evaluation result persistence and iteration tracking."""
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvalStore:
    """
    Manages evaluation result storage and iteration tracking.

    Directory structure:
        evals/{eval_id}/results/
            iteration-001/
                extracted.json
                eval-results.json
                eval-report.html
            iteration-002/
                ...
            aggregate.json  (tracks metrics across all iterations)
    """
    evals_dir: Path
    results_subdir: str = "results"

    def __post_init__(self):
        self.evals_dir = Path(self.evals_dir)

    def get_results_dir(self, eval_id: str) -> Path:
        """Get the results directory for an eval."""
        return self.evals_dir / eval_id / self.results_subdir

    def get_iteration_dir(self, eval_id: str, iteration: int) -> Path:
        """Get the directory for a specific iteration."""
        return self.get_results_dir(eval_id) / f"iteration-{iteration:03d}"

    def get_next_iteration(self, eval_id: str) -> int:
        """
        Determine the next iteration number for an eval.

        Returns:
            Next iteration number (1 if no iterations exist)
        """
        results_dir = self.get_results_dir(eval_id)
        if not results_dir.exists():
            return 1

        # Find existing iteration directories
        pattern = re.compile(r"iteration-(\d+)")
        max_iteration = 0

        for item in results_dir.iterdir():
            if item.is_dir():
                match = pattern.match(item.name)
                if match:
                    iteration = int(match.group(1))
                    max_iteration = max(max_iteration, iteration)

        return max_iteration + 1

    def get_latest_iteration(self, eval_id: str) -> Optional[int]:
        """
        Get the latest iteration number for an eval.

        Returns:
            Latest iteration number, or None if no iterations exist
        """
        next_iter = self.get_next_iteration(eval_id)
        return next_iter - 1 if next_iter > 1 else None

    def save_iteration(
        self,
        eval_id: str,
        iteration: int,
        extracted_data: Dict[str, Any],
        eval_results: Dict[str, Any],
        html_report: Optional[str] = None,
    ) -> Path:
        """
        Save evaluation results for an iteration.

        Args:
            eval_id: Evaluation identifier
            iteration: Iteration number
            extracted_data: The extracted JSON data
            eval_results: Evaluation results (metrics, discrepancies)
            html_report: Optional HTML report string

        Returns:
            Path to iteration directory
        """
        iter_dir = self.get_iteration_dir(eval_id, iteration)
        iter_dir.mkdir(parents=True, exist_ok=True)

        # Save extracted data
        (iter_dir / "extracted.json").write_text(
            json.dumps(extracted_data, indent=2, default=str)
        )

        # Add timestamp to eval results
        eval_results["timestamp"] = datetime.utcnow().isoformat() + "Z"
        eval_results["iteration"] = iteration

        # Save evaluation results
        (iter_dir / "eval-results.json").write_text(
            json.dumps(eval_results, indent=2, default=str)
        )

        # Save HTML report if provided
        if html_report:
            (iter_dir / "eval-report.html").write_text(html_report)

        # Update aggregate file
        self._update_aggregate(eval_id, iteration, eval_results)

        return iter_dir

    def _update_aggregate(
        self,
        eval_id: str,
        iteration: int,
        eval_results: Dict[str, Any],
    ) -> None:
        """Update the aggregate.json file with new iteration data."""
        aggregate_path = self.get_results_dir(eval_id) / "aggregate.json"

        # Load existing aggregate or create new
        if aggregate_path.exists():
            aggregate = json.loads(aggregate_path.read_text())
        else:
            aggregate = {
                "eval_id": eval_id,
                "iterations": [],
                "best_f1": 0.0,
                "best_iteration": None,
            }

        # Extract metrics for history
        metrics = eval_results.get("metrics", {})
        history_entry = {
            "iteration": iteration,
            "f1": metrics.get("f1", 0.0),
            "precision": metrics.get("precision", 0.0),
            "recall": metrics.get("recall", 0.0),
            "timestamp": eval_results.get("timestamp"),
            "error_counts": metrics.get("errors_by_type", {}),
        }

        # Calculate trend from previous iteration
        if aggregate["iterations"]:
            prev_f1 = aggregate["iterations"][-1].get("f1", 0.0)
            history_entry["trend"] = history_entry["f1"] - prev_f1
        else:
            history_entry["trend"] = 0.0

        # Append to history
        aggregate["iterations"].append(history_entry)

        # Update best
        if history_entry["f1"] >= aggregate["best_f1"]:
            aggregate["best_f1"] = history_entry["f1"]
            aggregate["best_iteration"] = iteration

        # Save
        aggregate_path.write_text(json.dumps(aggregate, indent=2))

    def load_aggregate(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the aggregate history for an eval.

        Returns:
            Aggregate dict or None if not found
        """
        aggregate_path = self.get_results_dir(eval_id) / "aggregate.json"
        if aggregate_path.exists():
            return json.loads(aggregate_path.read_text())
        return None

    def load_iteration(self, eval_id: str, iteration: int) -> Optional[Dict[str, Any]]:
        """
        Load eval results from a specific iteration.

        Returns:
            Eval results dict or None if not found
        """
        results_path = self.get_iteration_dir(eval_id, iteration) / "eval-results.json"
        if results_path.exists():
            return json.loads(results_path.read_text())
        return None

    def get_history(self, eval_id: str) -> List[Dict[str, Any]]:
        """
        Get F1 history across all iterations.

        Returns:
            List of history entries sorted by iteration
        """
        aggregate = self.load_aggregate(eval_id)
        if aggregate:
            return sorted(aggregate.get("iterations", []), key=lambda x: x["iteration"])
        return []


def get_next_iteration(evals_dir: Path, eval_id: str, results_subdir: str = "results") -> int:
    """
    Convenience function to get next iteration number.

    Args:
        evals_dir: Base evals directory
        eval_id: Evaluation identifier
        results_subdir: Results subdirectory name

    Returns:
        Next iteration number
    """
    store = EvalStore(evals_dir, results_subdir)
    return store.get_next_iteration(eval_id)


def save_evaluation(
    evals_dir: Path,
    eval_id: str,
    extracted_data: Dict[str, Any],
    eval_results: Dict[str, Any],
    html_report: Optional[str] = None,
    iteration: Optional[int] = None,
    results_subdir: str = "results",
) -> Path:
    """
    Convenience function to save evaluation results.

    Args:
        evals_dir: Base evals directory
        eval_id: Evaluation identifier
        extracted_data: The extracted JSON data
        eval_results: Evaluation results (metrics, discrepancies)
        html_report: Optional HTML report string
        iteration: Optional specific iteration (auto-assigns if None)
        results_subdir: Results subdirectory name

    Returns:
        Path to iteration directory
    """
    store = EvalStore(evals_dir, results_subdir)

    if iteration is None:
        iteration = store.get_next_iteration(eval_id)

    return store.save_iteration(
        eval_id=eval_id,
        iteration=iteration,
        extracted_data=extracted_data,
        eval_results=eval_results,
        html_report=html_report,
    )
