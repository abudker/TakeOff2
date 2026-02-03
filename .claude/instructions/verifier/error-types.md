# Error Type Taxonomy v1.0.0

This document defines the four error categories used to classify field-level discrepancies between extracted data and ground truth. Error categorization informs the self-improvement loop about which aspects of extraction need attention.

## Error Categories

### 1. Omission

**Definition:** An expected field from ground truth is missing from the extraction.

**Detection:** Field path exists in ground truth but returns `null`/`None` when navigated in extracted JSON.

**Impact on Metrics:**
- Decreases recall (missed a true positive)
- Does not affect precision

**Examples from Building Extraction:**

| Expected (Ground Truth) | Extracted | Why Omission |
|------------------------|-----------|--------------|
| `bedrooms: 3` | Field not present | Extractor failed to find/include bedroom count |
| `water_heater.fuel_type: "natural_gas"` | `water_heater: {}` (empty) | Extractor found water heater but missed fuel type |
| `envelope.window_count: 8` | No window_count field | Extractor skipped window counting entirely |

**Improvement Signal:**
- Extractor instructions need to emphasize completeness
- May need explicit checklist of required fields
- Consider adding validation step before output
- May indicate missing data in source PDF (check manually)

---

### 2. Hallucination

**Definition:** A field present in the extraction that has no corresponding field in ground truth.

**Detection:** Field path exists in extracted JSON but has no mapping in ground truth.

**Impact on Metrics:**
- Decreases precision (false positive)
- Does not affect recall

**Examples from Building Extraction:**

| Expected (Ground Truth) | Extracted | Why Hallucination |
|------------------------|-----------|-------------------|
| No solar_panels field | `solar_panels: { count: 4 }` | Extractor invented solar panels that don't exist |
| No basement field | `basement: { area: 500 }` | Extractor assumed basement when building has none |
| `zones: [zone1, zone2]` | `zones: [zone1, zone2, zone3]` | Extractor hallucinated a third zone |

**Improvement Signal:**
- Extractor instructions need to emphasize evidence grounding
- Add requirement: "Only include fields with explicit evidence in PDF"
- May need validation rules to reject implausible values
- Consider confidence thresholds for uncertain fields

---

### 3. Format Error

**Definition:** A field is present in both ground truth and extraction, but the extracted value has the wrong type or format.

**Detection:** Field exists in both, but type comparison fails (e.g., expected int, got string).

**Impact on Metrics:**
- Counts as false positive for precision
- Counts as false negative for recall
- Both metrics decrease

**Examples from Building Extraction:**

| Expected (Ground Truth) | Extracted | Why Format Error |
|------------------------|-----------|------------------|
| `climate_zone: 12` (int) | `climate_zone: "12"` (string) | Correct value but wrong type |
| `window_area: 45.5` (float) | `window_area: "45.5 sq ft"` (string with units) | Units included in value |
| `has_garage: true` (bool) | `has_garage: "yes"` (string) | Boolean as string |
| `project.address` (string) | `project.address: ["123 Main St"]` (array) | Single value as array |

**Improvement Signal:**
- Extractor instructions need explicit type hints
- Add schema validation step before output
- Consider type coercion in output generation
- May need post-processing to normalize formats

---

### 4. Wrong Value

**Definition:** A field is present with the correct type, but the value does not match ground truth (outside tolerance for numeric fields).

**Detection:** Field exists in both, types match, but value comparison fails.

**Impact on Metrics:**
- Counts as false positive for precision
- Counts as false negative for recall
- Both metrics decrease

**Examples from Building Extraction:**

| Expected (Ground Truth) | Extracted | Why Wrong Value |
|------------------------|-----------|-----------------|
| `bedrooms: 3` | `bedrooms: 2` | Miscounted or misread |
| `conditioned_floor_area: 1850` | `conditioned_floor_area: 1650` | Read wrong value or calculation error |
| `climate_zone: 12` | `climate_zone: 4` | Extracted from wrong document area |
| `hvac.system_type: "heat_pump"` | `hvac.system_type: "furnace"` | Misidentified system type |

**Improvement Signal:**
- Extractor instructions need domain-specific guidance
- For counts: "Count all items on all pages/elevations"
- For numeric values: "Cross-reference with summary tables"
- May need multi-pass extraction with verification
- Consider extracting from multiple sources and comparing

---

## Error Priority for Improvement

When analyzing errors for the improvement loop, prioritize in this order:

1. **Omissions** - Missing data is usually most critical for downstream use
2. **Wrong Values** - Present but incorrect is better than missing, but still problematic
3. **Format Errors** - Often fixable with post-processing without prompt changes
4. **Hallucinations** - Extra data can usually be filtered, but indicates unreliable extraction

## Categorization Logic

```python
def categorize_discrepancy(expected, actual, expected_type):
    """
    Categorize a field discrepancy into one of four error types.

    Args:
        expected: Value from ground truth (None if field shouldn't exist)
        actual: Value from extraction (None if field missing)
        expected_type: Python type expected for this field

    Returns:
        str: One of "omission", "hallucination", "format_error", "wrong_value"
    """
    # Field missing from extraction but expected in ground truth
    if actual is None and expected is not None:
        return "omission"

    # Field present in extraction but not expected
    if expected is None and actual is not None:
        return "hallucination"

    # Field present in both - check type
    if not isinstance(actual, expected_type):
        # Special handling for numeric types
        if expected_type in (int, float) and isinstance(actual, (int, float)):
            pass  # Allow int/float interchangeability
        else:
            return "format_error"

    # Type correct but value wrong
    return "wrong_value"
```

## Notes

- This taxonomy is designed for field-level (not document-level) evaluation
- Each discrepancy gets exactly one error type
- Error types inform which aspects of extraction instructions to improve
- This file can be modified by the improvement loop to refine categorization
