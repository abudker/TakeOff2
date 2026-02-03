"""HTML report generation for evaluation results."""
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass
class EvalReport:
    """
    Evaluation report generator.

    Renders HTML reports from evaluation results using Jinja2 templates.
    """
    eval_id: str
    metrics: Dict[str, Any]
    discrepancies: List[Dict[str, Any]]
    iteration: Optional[int] = None
    history: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for template rendering."""
        return {
            "eval_id": self.eval_id,
            "metrics": self.metrics,
            "discrepancies": self.discrepancies,
            "iteration": self.iteration,
            "history": self.history,
            "timestamp": self.timestamp,
        }

    def render_html(self, template_dir: Optional[Path] = None) -> str:
        """
        Render the report as HTML.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         Defaults to the templates directory in this package.

        Returns:
            Rendered HTML string
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        template = env.get_template("eval-report.html.j2")
        return template.render(**self.to_dict())

    def save_html(self, output_path: Path, template_dir: Optional[Path] = None) -> Path:
        """
        Render and save HTML report to file.

        Args:
            output_path: Path to save the HTML file
            template_dir: Optional template directory override

        Returns:
            Path to saved file
        """
        html = self.render_html(template_dir)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)
        return output_path


def generate_html_report(
    eval_id: str,
    metrics: Dict[str, Any],
    discrepancies: List[Dict[str, Any]],
    output_path: Path,
    iteration: Optional[int] = None,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Path:
    """
    Convenience function to generate and save an HTML report.

    Args:
        eval_id: Evaluation identifier
        metrics: Dict containing precision, recall, f1, errors_by_type, etc.
        discrepancies: List of discrepancy dicts with field_path, expected, actual, error_type
        output_path: Path to save the HTML file
        iteration: Optional iteration number
        history: Optional list of historical metrics for trend display

    Returns:
        Path to saved HTML file
    """
    report = EvalReport(
        eval_id=eval_id,
        metrics=metrics,
        discrepancies=discrepancies,
        iteration=iteration,
        history=history,
    )
    return report.save_html(output_path)
