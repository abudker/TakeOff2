"""Field-level comparison logic for extraction evaluation."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import re
import yaml


def normalize_text(text: str, field_path: str = None) -> str:
    """Normalize text for comparison.

    Args:
        text: The text to normalize
        field_path: Optional field path for context-aware normalization

    Returns:
        Normalized text string
    """
    text = text.strip().lower()

    # Remove trailing punctuation (periods, commas)
    text = re.sub(r'[.,;:]+$', '', text)

    # For name fields, remove parenthetical content like "(3020)"
    if field_path and ('name' in field_path or 'window' in field_path or 'wall' in field_path):
        text = re.sub(r'\s*\([^)]*\)\s*', '', text)

    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


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


def is_non_extractable(field_path: str, exclusion_set: Set[str]) -> bool:
    """Check if a field path should be excluded from comparison.

    Args:
        field_path: The dot-separated field path (e.g., "project.run_id" or "zones[0].name")
        exclusion_set: Set of field paths to exclude

    Returns:
        True if the field should be excluded from comparison
    """
    if field_path in exclusion_set:
        return True

    # Handle array notation (zones[0].name matches zones[*].name)
    normalized = re.sub(r'\[\d+\]', '[*]', field_path)
    if normalized in exclusion_set:
        return True

    # Handle prefix wildcards (extraction_status.* matches extraction_status.project.domain)
    for pattern in exclusion_set:
        if pattern.endswith('.*'):
            prefix = pattern[:-2]  # Remove .*
            if field_path.startswith(prefix + '.'):
                return True

    return False


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

    # String comparison (case-insensitive, trimmed, normalized)
    if isinstance(expected, str) and isinstance(actual, str):
        return normalize_text(expected, field_path) == normalize_text(actual, field_path)

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


@dataclass
class FieldComparison:
    """Represents a single field comparison (match or mismatch)."""
    field_path: str
    expected: Any
    actual: Any
    matches: bool
    error_type: Optional[str] = None  # omission, hallucination, format_error, wrong_value


def compare_all_fields(
    ground_truth: Dict[str, Any],
    extracted: Dict[str, Any],
    mapping: Optional[Dict] = None
) -> List[FieldComparison]:
    """
    Compare all fields between extracted data and ground truth.

    Returns all comparisons, including matches.
    """
    if mapping is None:
        mapping = load_field_mapping()

    tolerances = mapping.get("tolerances", {"default": {"percent": 0.5, "absolute": 0.01}})
    tolerance_categories = mapping.get("tolerance_categories", {})
    non_extractable = set(mapping.get("non_extractable_fields", []))
    comparisons = []

    gt_flat = flatten_dict(ground_truth)
    ext_flat = flatten_dict(extracted)

    # All paths from both sides
    all_paths = set(gt_flat.keys()) | set(ext_flat.keys())

    for path in sorted(all_paths):
        # Skip non-extractable fields (CBECC-only)
        if is_non_extractable(path, non_extractable):
            continue

        expected = gt_flat.get(path)
        actual = ext_flat.get(path)

        if expected is None:
            # Hallucination - in extracted but not in ground truth
            comparisons.append(FieldComparison(
                field_path=path,
                expected=None,
                actual=actual,
                matches=False,
                error_type="hallucination"
            ))
        elif actual is None:
            # Omission - in ground truth but not in extracted
            comparisons.append(FieldComparison(
                field_path=path,
                expected=expected,
                actual=None,
                matches=False,
                error_type="omission"
            ))
        elif values_match(expected, actual, path, tolerances, tolerance_categories):
            # Match
            comparisons.append(FieldComparison(
                field_path=path,
                expected=expected,
                actual=actual,
                matches=True,
                error_type=None
            ))
        else:
            # Mismatch - determine error type
            expected_type = type(expected)
            actual_type = type(actual)
            numeric_types = (int, float)

            if isinstance(expected, numeric_types) and isinstance(actual, numeric_types):
                error_type = "wrong_value"
            elif expected_type != actual_type:
                error_type = "format_error"
            else:
                error_type = "wrong_value"

            comparisons.append(FieldComparison(
                field_path=path,
                expected=expected,
                actual=actual,
                matches=False,
                error_type=error_type
            ))

    return comparisons


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
    non_extractable = set(mapping.get("non_extractable_fields", []))
    discrepancies = []

    gt_flat = flatten_dict(ground_truth)
    ext_flat = flatten_dict(extracted)

    # Check each ground truth field
    for gt_path, expected_value in gt_flat.items():
        # Skip non-extractable fields (CBECC-only)
        if is_non_extractable(gt_path, non_extractable):
            continue

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
        # Skip non-extractable fields (CBECC-only)
        if is_non_extractable(ext_path, non_extractable):
            continue

        if ext_path not in gt_flat:
            discrepancies.append(FieldDiscrepancy(
                field_path=ext_path,
                expected=None,
                actual=actual_value,
                error_type="hallucination"
            ))

    return discrepancies
