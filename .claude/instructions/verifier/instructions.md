# Verifier Instructions v1.0.0

## Purpose

Compare extracted BuildingSpec JSON against ground_truth.csv and compute field-level metrics to measure extraction quality. Generate detailed reports showing discrepancies, error breakdowns, and metrics for tracking improvement across iterations.

## Input/Output Specification

**Inputs:**
- `ground_truth.csv` - CSV file with expected field values (CBECC-Res/EnergyPro export format)
- `extracted.json` - JSON file with extraction results from BuildingSpec schema

**Outputs:**
- `eval-results.json` - Structured results with discrepancies, metrics, and metadata
- `eval-report.html` - Human-readable HTML report for debugging
- Updated `aggregate.json` - Metrics across all iterations for this eval

## Field Comparison Process

### Step 1: Load Ground Truth CSV

Use pandas to load the ground_truth.csv file:

```python
import pandas as pd
ground_truth = pd.read_csv(ground_truth_path)
```

The CSV contains rows where each row represents a field with its expected value.

### Step 2: Load Extracted JSON

Parse the extracted.json file to get the BuildingSpec structure:

```python
import json
with open(extracted_path) as f:
    extracted = json.load(f)
```

### Step 3: Map CSV Columns to JSON Field Paths

Use the field_mapping.yaml configuration to translate between formats:
- CSV has human-readable column names: "Climate Zone", "Conditioned Floor Area"
- JSON has nested field paths: "project.climate_zone", "envelope.conditioned_floor_area"

Reference `schemas/field_mapping.yaml` for the authoritative mapping.

### Step 4: Compare Each Field

For each field defined in ground truth:

1. Look up the expected value from CSV
2. Navigate to the corresponding field in extracted JSON using the mapped path
3. Apply appropriate comparison logic based on field type:
   - **Numeric fields:** Use tolerance-based comparison (see Numeric Comparison Rules)
   - **String fields:** Use case-insensitive comparison (see String Comparison Rules)
   - **Boolean fields:** Use exact match comparison
4. If values do not match, record a discrepancy
5. If field is missing from extraction, record as omission
6. After all comparisons, check for hallucinated fields (present in extraction but not in ground truth)

### Step 5: Categorize Errors

For each discrepancy, assign an error type using the taxonomy in error-types.md:
- `omission` - Expected field missing from extraction
- `hallucination` - Field present in extraction but not expected
- `format_error` - Field present but wrong type/format
- `wrong_value` - Field present with correct type but incorrect value

### Step 6: Compute Metrics

Apply the formulas from metrics.md to compute:
- Precision
- Recall
- F1 Score
- Error breakdown by type

### Step 7: Generate HTML Report

Create an HTML report using the Jinja2 template at `src/verifier/templates/eval-report.html.j2`:
- Show overall metrics prominently
- Display error breakdown by type with color coding
- List all discrepancies with expected vs. actual values
- Include timestamp and iteration number

## Comparison Rules

### Numeric Comparison Rules

For numeric fields, use tolerance-based comparison to handle floating-point precision and reasonable variation:

**Tolerance:** Accept values within the LARGER of:
- **Relative tolerance:** plus or minus 0.5% of expected value
- **Absolute tolerance:** plus or minus 0.01 units

**Formula:**
```python
def numeric_match(expected, actual):
    if expected == 0:
        return abs(actual) <= 0.01

    relative_diff = abs(actual - expected) / abs(expected)
    absolute_diff = abs(actual - expected)

    return (relative_diff <= 0.005) or (absolute_diff <= 0.01)
```

**Examples:**
- Expected: 1200, Actual: 1205 (0.4% diff) - MATCH (within 0.5%)
- Expected: 0.31, Actual: 0.3099 (0.03% diff) - MATCH (within tolerance)
- Expected: 1200, Actual: 1210 (0.83% diff) - MISMATCH (exceeds 0.5%)

### String Comparison Rules

For string fields, use case-insensitive comparison after normalizing whitespace:

**Normalization:**
1. Trim leading and trailing whitespace
2. Convert to lowercase
3. Collapse multiple internal spaces to single space

**Formula:**
```python
def string_match(expected, actual):
    if expected is None or actual is None:
        return expected == actual

    normalized_expected = ' '.join(str(expected).strip().lower().split())
    normalized_actual = ' '.join(str(actual).strip().lower().split())

    return normalized_expected == normalized_actual
```

**Examples:**
- Expected: "Climate Zone 12", Actual: "climate zone 12" - MATCH
- Expected: "San Francisco", Actual: "  San  Francisco " - MATCH (after normalization)
- Expected: "Zone 4", Actual: "Zone 5" - MISMATCH

### Boolean Comparison Rules

For boolean fields, require exact match after type normalization:

**Normalization:**
- Convert string "true"/"True"/"TRUE" to boolean True
- Convert string "false"/"False"/"FALSE" to boolean False
- Convert integers 1/0 to True/False

**Formula:**
```python
def boolean_match(expected, actual):
    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == 'true'
        if isinstance(val, int):
            return val != 0
        return bool(val)

    return to_bool(expected) == to_bool(actual)
```

## Field Path Navigation

To access nested fields in the extracted JSON:

```python
def get_nested_value(data, path):
    """Navigate to a nested field using dot notation.

    Example: get_nested_value(data, "project.climate_zone")
    """
    keys = path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                return None
            current = current[key]
        elif isinstance(current, list):
            try:
                index = int(key)
                current = current[index]
            except (ValueError, IndexError):
                return None
        else:
            return None

    return current
```

## Notes

- Detailed metric formulas and computation are defined in metrics.md
- Error type definitions and examples are in error-types.md
- This file can be modified by the improvement loop to adjust comparison behavior
- Version number in header tracks changes for iteration correlation
