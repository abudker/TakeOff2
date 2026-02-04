"""HTML report generation for evaluation results."""
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape


def extract_domain(field_path: str) -> str:
    """Extract domain from field path.

    Examples:
        "project.run_title" -> "project"
        "envelope.conditioned_floor_area" -> "envelope"
        "windows[0].name" -> "windows"
        "zones[0].volume" -> "zones"
        "hvac_systems[0].type" -> "hvac_systems"
    """
    # Handle array notation: "windows[0].name" -> "windows"
    match = re.match(r'^([a-z_]+)', field_path)
    if match:
        return match.group(1)
    return "other"


def group_fields_by_domain(all_fields: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group fields by domain with summary statistics.

    Returns dict mapping domain name to:
        {
            "fields": list of field dicts,
            "total": int,
            "matches": int,
            "mismatches": int,
            "errors_by_type": {"omission": N, "wrong_value": N, ...}
        }
    """
    groups = defaultdict(lambda: {
        "fields": [],
        "total": 0,
        "matches": 0,
        "mismatches": 0,
        "errors_by_type": defaultdict(int)
    })

    for field in all_fields:
        domain = extract_domain(field["field_path"])
        group = groups[domain]
        group["fields"].append(field)
        group["total"] += 1

        if field.get("matches"):
            group["matches"] += 1
        else:
            group["mismatches"] += 1
            error_type = field.get("error_type", "unknown")
            group["errors_by_type"][error_type] += 1

    # Convert defaultdicts to regular dicts for JSON serialization
    result = {}
    for domain, data in groups.items():
        result[domain] = {
            "fields": data["fields"],
            "total": data["total"],
            "matches": data["matches"],
            "mismatches": data["mismatches"],
            "errors_by_type": dict(data["errors_by_type"])
        }

    return result


# Domain display names and order
DOMAIN_ORDER = [
    "project",
    "envelope",
    "zones",
    "walls",
    "windows",
    "hvac_systems",
    "water_heating_systems",
    "ceilings",
    "slab_floors",
]

DOMAIN_LABELS = {
    "project": "Project Info",
    "envelope": "Envelope Summary",
    "zones": "Thermal Zones",
    "walls": "Walls",
    "windows": "Windows / Fenestration",
    "hvac_systems": "HVAC Systems",
    "water_heating_systems": "Water Heating (DHW)",
    "ceilings": "Ceilings",
    "slab_floors": "Slab Floors",
}


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
    all_fields: Optional[List[Dict[str, Any]]] = None
    extracted_data: Optional[str] = None  # JSON string of extracted data
    ground_truth_data: Optional[str] = None  # JSON string of ground truth

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for template rendering."""
        # Group fields by domain if all_fields is provided
        grouped_fields = None
        if self.all_fields:
            grouped_fields = group_fields_by_domain(self.all_fields)

        return {
            "eval_id": self.eval_id,
            "metrics": self.metrics,
            "discrepancies": self.discrepancies,
            "iteration": self.iteration,
            "history": self.history,
            "timestamp": self.timestamp,
            "all_fields": self.all_fields,
            "grouped_fields": grouped_fields,
            "domain_order": DOMAIN_ORDER,
            "domain_labels": DOMAIN_LABELS,
            "extracted_data": self.extracted_data,
            "ground_truth_data": self.ground_truth_data,
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
    all_fields: Optional[List[Dict[str, Any]]] = None,
    extracted_data: Optional[str] = None,
    ground_truth_data: Optional[str] = None,
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
        all_fields: Optional list of all field comparisons (matches and mismatches)
        extracted_data: Optional JSON string of extracted data for raw view
        ground_truth_data: Optional JSON string of ground truth for raw view

    Returns:
        Path to saved HTML file
    """
    report = EvalReport(
        eval_id=eval_id,
        metrics=metrics,
        discrepancies=discrepancies,
        iteration=iteration,
        history=history,
        all_fields=all_fields,
        extracted_data=extracted_data,
        ground_truth_data=ground_truth_data,
    )
    return report.save_html(output_path)
