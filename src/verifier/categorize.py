"""Error type categorization for extraction discrepancies."""
from typing import Any
from .compare import FieldDiscrepancy


def categorize_error(expected: Any, actual: Any) -> str:
    """
    Categorize the error type for a field discrepancy.

    Error types:
    - omission: Expected field missing from extraction
    - hallucination: Field present in extraction but not in ground truth
    - format_error: Field present but wrong type/format
    - wrong_value: Field present, correct type, but incorrect value
    """
    if expected is not None and actual is None:
        return "omission"

    if expected is None and actual is not None:
        return "hallucination"

    # Check for type mismatch (format_error)
    expected_type = type(expected)
    actual_type = type(actual)

    # Consider int/float as compatible numeric types
    numeric_types = (int, float)
    if isinstance(expected, numeric_types) and isinstance(actual, numeric_types):
        return "wrong_value"

    if expected_type != actual_type:
        return "format_error"

    return "wrong_value"


def get_improvement_hint(error_type: str, field_path: str) -> str:
    """
    Get a hint for how to improve extraction based on error type.

    Used by critic agent to generate improvement proposals.
    """
    hints = {
        "omission": f"Extractor missed '{field_path}'. Add to extraction checklist or emphasize in instructions.",
        "hallucination": f"Extractor fabricated '{field_path}'. Add validation to require evidence in PDF.",
        "format_error": f"Extractor got wrong type for '{field_path}'. Add type hints to extraction schema.",
        "wrong_value": f"Extractor got wrong value for '{field_path}'. May need domain-specific guidance.",
    }
    return hints.get(error_type, "Unknown error type")


def summarize_errors(discrepancies: list[FieldDiscrepancy]) -> dict[str, list[str]]:
    """
    Group discrepancies by error type for summary reporting.

    Args:
        discrepancies: List of FieldDiscrepancy objects

    Returns:
        Dict mapping error type to list of field paths
    """
    result = {
        "omission": [],
        "hallucination": [],
        "format_error": [],
        "wrong_value": [],
    }

    for d in discrepancies:
        if d.error_type in result:
            result[d.error_type].append(d.field_path)

    return result


def get_critical_errors(discrepancies: list[FieldDiscrepancy],
                        critical_fields: list[str] = None) -> list[FieldDiscrepancy]:
    """
    Filter discrepancies to only critical fields.

    Critical fields are those that significantly impact energy modeling accuracy.

    Args:
        discrepancies: List of all discrepancies
        critical_fields: List of field paths considered critical

    Returns:
        List of discrepancies for critical fields only
    """
    if critical_fields is None:
        # Default critical fields for energy modeling
        critical_fields = [
            "project.climate_zone",
            "envelope.conditioned_floor_area",
            "envelope.window_area",
            "envelope.exterior_wall_area",
        ]

    return [d for d in discrepancies
            if any(cf in d.field_path for cf in critical_fields)]
