# Metric Computation Guide v1.0.0

This document defines how to compute precision, recall, and F1 metrics for extraction quality evaluation. All metrics are computed at the **field level**, not document level.

## Field-Level Metrics

### Why Field-Level?

Document-level metrics (did we extract the document correctly? yes/no) are too coarse for improvement. We need to know which specific fields are problematic:

- **Document-level:** "Extraction failed" - no actionable feedback
- **Field-level:** "window_count has 60% accuracy, bedrooms has 95%" - actionable improvement targets

### Terms

**True Positive (TP):** A field that exists in ground truth AND was correctly extracted with matching value.

**False Positive (FP):** A field that is in the extraction but either:
- Does not exist in ground truth (hallucination), OR
- Has wrong type (format_error), OR
- Has wrong value (wrong_value)

**False Negative (FN):** A field that exists in ground truth but was not extracted (omission).

### Relationship to Error Types

| Error Type | Counts As | Effect on Precision | Effect on Recall |
|------------|-----------|--------------------:|:-----------------|
| omission | FN | None | Decreases |
| hallucination | FP | Decreases | None |
| format_error | FP + FN | Decreases | Decreases |
| wrong_value | FP + FN | Decreases | Decreases |

Note: format_error and wrong_value count as both FP and FN because the field was attempted (counted in extracted) but incorrect (not a true positive in ground truth).

## Formulas

### Precision

**Definition:** Of all the fields we extracted, what fraction are correct?

**Formula:**
```
Precision = TP / (TP + FP)
```

**Interpretation:**
- High precision = extraction is accurate, few false extractions
- Low precision = extraction makes many mistakes or hallucinations

### Recall

**Definition:** Of all the fields that should exist, what fraction did we correctly extract?

**Formula:**
```
Recall = TP / (TP + FN)
```

**Interpretation:**
- High recall = extraction is complete, few omissions
- Low recall = extraction misses many expected fields

### F1 Score

**Definition:** Harmonic mean of precision and recall, balancing both concerns.

**Formula:**
```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

**Interpretation:**
- F1 = 1.0: Perfect extraction
- F1 = 0.0: Complete failure
- F1 = 0.90 (project target): High-quality extraction suitable for downstream use

## Computation Process

### Step 1: Count Discrepancies by Type

```python
def count_by_type(discrepancies):
    """Count discrepancies by error type."""
    counts = {
        'omission': 0,
        'hallucination': 0,
        'format_error': 0,
        'wrong_value': 0
    }
    for d in discrepancies:
        counts[d.error_type] += 1
    return counts
```

### Step 2: Compute TP, FP, FN

```python
def compute_confusion_counts(total_gt_fields, discrepancies):
    """
    Compute true positives, false positives, and false negatives.

    Args:
        total_gt_fields: Number of fields in ground truth
        discrepancies: List of FieldDiscrepancy objects

    Returns:
        tuple: (TP, FP, FN)
    """
    counts = count_by_type(discrepancies)

    omissions = counts['omission']
    hallucinations = counts['hallucination']
    format_errors = counts['format_error']
    wrong_values = counts['wrong_value']

    # True positives: ground truth fields that were correctly extracted
    # Total GT fields minus those that were omitted or had wrong value/format
    TP = total_gt_fields - omissions - format_errors - wrong_values

    # False positives: extractions that were wrong
    # Hallucinations (shouldn't exist) + format errors + wrong values
    FP = hallucinations + format_errors + wrong_values

    # False negatives: ground truth fields not correctly captured
    # Omissions (completely missing)
    FN = omissions

    return TP, FP, FN
```

### Step 3: Compute Metrics

```python
def compute_metrics(total_gt_fields, discrepancies):
    """
    Compute precision, recall, and F1 from field counts and discrepancies.

    Args:
        total_gt_fields: Number of fields in ground truth
        discrepancies: List of FieldDiscrepancy objects

    Returns:
        dict: Metrics dictionary with precision, recall, f1, and counts
    """
    TP, FP, FN = compute_confusion_counts(total_gt_fields, discrepancies)

    # Handle edge case: division by zero
    if (TP + FP) == 0:
        precision = 0.0
    else:
        precision = TP / (TP + FP)

    if (TP + FN) == 0:
        recall = 0.0
    else:
        recall = TP / (TP + FN)

    # F1: Handle case where precision + recall = 0
    if (precision + recall) == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'true_positives': TP,
        'false_positives': FP,
        'false_negatives': FN,
        'total_gt_fields': total_gt_fields,
        'correct_fields': TP
    }
```

## Aggregate Metrics Across Evals

When computing metrics across all 5 evaluation cases, use **macro-averaging** (average of per-eval metrics).

### Macro-F1 (Primary Metric)

**Definition:** Average of F1 scores across all evals.

**Formula:**
```
Macro-F1 = (F1_eval1 + F1_eval2 + F1_eval3 + F1_eval4 + F1_eval5) / 5
```

**Why Macro-F1:**
- Treats each eval equally regardless of number of fields
- Prevents larger documents from dominating metrics
- Better represents performance across diverse document types

### Micro-F1 (Secondary Metric)

**Definition:** Pool all fields across evals, then compute F1.

**Formula:**
```
Total_TP = sum(TP for each eval)
Total_FP = sum(FP for each eval)
Total_FN = sum(FN for each eval)

Micro_Precision = Total_TP / (Total_TP + Total_FP)
Micro_Recall = Total_TP / (Total_TP + Total_FN)
Micro_F1 = 2 * (Micro_Precision * Micro_Recall) / (Micro_Precision + Micro_Recall)
```

**When to Report:**
- Include in detailed reports alongside macro-F1
- Useful for understanding overall field accuracy
- May differ from macro-F1 if eval sizes vary significantly

### Implementation

```python
def compute_aggregate_metrics(eval_results):
    """
    Compute aggregate metrics across all evaluation cases.

    Args:
        eval_results: List of dicts, each with 'metrics' key containing
                      precision, recall, f1, TP, FP, FN

    Returns:
        dict: Aggregate metrics including macro and micro F1
    """
    # Macro-averaging (average of per-eval metrics)
    macro_precision = sum(r['metrics']['precision'] for r in eval_results) / len(eval_results)
    macro_recall = sum(r['metrics']['recall'] for r in eval_results) / len(eval_results)
    macro_f1 = sum(r['metrics']['f1'] for r in eval_results) / len(eval_results)

    # Micro-averaging (pool all fields)
    total_tp = sum(r['metrics']['true_positives'] for r in eval_results)
    total_fp = sum(r['metrics']['false_positives'] for r in eval_results)
    total_fn = sum(r['metrics']['false_negatives'] for r in eval_results)

    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    micro_f1 = 2 * (micro_precision * micro_recall) / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0

    return {
        'macro': {
            'precision': macro_precision,
            'recall': macro_recall,
            'f1': macro_f1
        },
        'micro': {
            'precision': micro_precision,
            'recall': micro_recall,
            'f1': micro_f1
        },
        'total_true_positives': total_tp,
        'total_false_positives': total_fp,
        'total_false_negatives': total_fn,
        'eval_count': len(eval_results)
    }
```

## Edge Cases

### Division by Zero

All division operations must handle the zero case:

```python
# Pattern: Use conditional or default to 0
result = numerator / denominator if denominator > 0 else 0.0
```

Specific cases:
- `TP + FP = 0`: Precision undefined, return 0 (no extractions made)
- `TP + FN = 0`: Recall undefined, return 0 (no ground truth fields - indicates data error)
- `Precision + Recall = 0`: F1 undefined, return 0

### Empty Results

If extraction produces no output:
- TP = 0, FP = 0, FN = total_gt_fields
- Precision = 0 (no extractions, 0/0 = 0)
- Recall = 0 (no correct extractions)
- F1 = 0

### Perfect Extraction

If extraction matches ground truth exactly:
- TP = total_gt_fields, FP = 0, FN = 0
- Precision = 1.0
- Recall = 1.0
- F1 = 1.0

## Notes

- Project target is 0.90 macro-F1 across all 5 evals
- Report both macro and micro metrics in HTML reports
- Store per-eval and aggregate metrics in eval-results.json
- This file can be modified by the improvement loop to adjust metric computation
