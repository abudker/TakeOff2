"""Takeoff v2 Verifier - Evaluate extraction quality against ground truth."""
from .compare import compare_fields, FieldDiscrepancy
from .metrics import compute_field_level_metrics
from .categorize import categorize_error

__all__ = [
    "compare_fields",
    "FieldDiscrepancy",
    "compute_field_level_metrics",
    "categorize_error",
]
