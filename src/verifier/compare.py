"""Field-level comparison logic for extraction evaluation."""
# Placeholder - will be implemented in Task 3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FieldDiscrepancy:
    """Represents a single field-level discrepancy."""
    field_path: str
    expected: Any
    actual: Any
    error_type: str  # omission, hallucination, format_error, wrong_value


def compare_fields(
    ground_truth: Dict[str, Any],
    extracted: Dict[str, Any],
    mapping: Optional[Dict] = None
) -> List[FieldDiscrepancy]:
    """Compare extracted data against ground truth at field level."""
    return []
