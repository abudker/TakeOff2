"""Field-level comparison logic for extraction evaluation."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml


@dataclass
class FieldDiscrepancy:
    """Represents a single field-level discrepancy."""
    field_path: str
    expected: Any
    actual: Any
    error_type: str  # omission, hallucination, format_error, wrong_value


def load_field_mapping() -> Dict:
    """Load field mapping from YAML config."""
    mapping_path = Path(__file__).parent.parent / "schemas" / "field_mapping.yaml"
    with open(mapping_path) as f:
        return yaml.safe_load(f)


def get_nested_value(data: Dict, path: str) -> Any:
    """Navigate nested dict using dot-separated path."""
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def set_nested_value(data: Dict, path: str, value: Any) -> None:
    """Set value in nested dict using dot-separated path."""
    keys = path.split(".")
    for key in keys[:-1]:
        data = data.setdefault(key, {})
    data[keys[-1]] = value


def flatten_dict(data: Dict, prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dict to {path: value} pairs."""
    result = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, path))
        elif isinstance(value, list):
            # For lists, use index in path
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    result.update(flatten_dict(item, f"{path}[{i}]"))
                else:
                    result[f"{path}[{i}]"] = item
        else:
            result[path] = value
    return result


def get_tolerance_for_field(field_path: str, tolerances: Dict, categories: Dict) -> Dict:
    """Determine which tolerance settings to use for a field."""
    field_name = field_path.split(".")[-1]

    # Check tolerance categories
    for category, fields in categories.items():
        if any(f in field_name for f in fields):
            return tolerances.get(category, tolerances["default"])

    return tolerances["default"]


def values_match(expected: Any, actual: Any, field_path: str, tolerances: Dict, tolerance_categories: Dict) -> bool:
    """Compare two values with appropriate logic based on type."""
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False

    # Numeric comparison with tolerance
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        tol = get_tolerance_for_field(field_path, tolerances, tolerance_categories)

        abs_diff = abs(expected - actual)
        rel_diff = abs_diff / abs(expected) if expected != 0 else abs_diff

        return (rel_diff <= tol["percent"] / 100 or
                abs_diff <= tol["absolute"])

    # String comparison (case-insensitive, trimmed)
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().lower() == actual.strip().lower()

    # Boolean exact match
    if isinstance(expected, bool) and isinstance(actual, bool):
        return expected == actual

    # Type mismatch - try coercion
    try:
        if isinstance(expected, (int, float)):
            return values_match(expected, float(actual), field_path, tolerances, tolerance_categories)
        if isinstance(expected, str):
            return values_match(expected, str(actual), field_path, tolerances, tolerance_categories)
    except (ValueError, TypeError):
        pass

    return expected == actual


def compare_fields(
    ground_truth: Dict[str, Any],
    extracted: Dict[str, Any],
    mapping: Optional[Dict] = None
) -> List[FieldDiscrepancy]:
    """
    Compare extracted data against ground truth at field level.

    Args:
        ground_truth: Dict with ground truth values (flattened or nested)
        extracted: Dict with extracted values (from JSON)
        mapping: Optional field mapping config

    Returns:
        List of FieldDiscrepancy objects for each mismatch
    """
    if mapping is None:
        mapping = load_field_mapping()

    tolerances = mapping.get("tolerances", {"default": {"percent": 0.5, "absolute": 0.01}})
    tolerance_categories = mapping.get("tolerance_categories", {})
    discrepancies = []

    gt_flat = flatten_dict(ground_truth)
    ext_flat = flatten_dict(extracted)

    # Check each ground truth field
    for gt_path, expected_value in gt_flat.items():
        actual_value = ext_flat.get(gt_path)

        if actual_value is None:
            discrepancies.append(FieldDiscrepancy(
                field_path=gt_path,
                expected=expected_value,
                actual=None,
                error_type="omission"
            ))
        elif not values_match(expected_value, actual_value, gt_path, tolerances, tolerance_categories):
            # Determine if it's a format error or wrong value
            expected_type = type(expected_value)
            actual_type = type(actual_value)

            # Consider int/float as compatible numeric types
            numeric_types = (int, float)
            if isinstance(expected_value, numeric_types) and isinstance(actual_value, numeric_types):
                error_type = "wrong_value"
            elif expected_type != actual_type:
                error_type = "format_error"
            else:
                error_type = "wrong_value"

            discrepancies.append(FieldDiscrepancy(
                field_path=gt_path,
                expected=expected_value,
                actual=actual_value,
                error_type=error_type
            ))

    # Check for hallucinated fields (in extracted but not in ground truth)
    for ext_path, actual_value in ext_flat.items():
        if ext_path not in gt_flat:
            discrepancies.append(FieldDiscrepancy(
                field_path=ext_path,
                expected=None,
                actual=actual_value,
                error_type="hallucination"
            ))

    return discrepancies
