"""Precision/recall/F1 computation at field level."""
from typing import Dict, List
from .compare import FieldDiscrepancy


def compute_field_level_metrics(
    discrepancies: List[FieldDiscrepancy],
    total_fields_gt: int,
    total_fields_extracted: int
) -> Dict[str, float]:
    """
    Compute precision, recall, F1 at field level.

    Each field is a binary classification:
    - True Positive (TP): field in ground truth that was correctly extracted
    - False Positive (FP): field in extracted that is wrong or hallucinated
    - False Negative (FN): field in ground truth that was omitted

    Args:
        discrepancies: List of field discrepancies
        total_fields_gt: Total fields in ground truth
        total_fields_extracted: Total fields in extracted JSON

    Returns:
        Dict with precision, recall, f1, and breakdown
    """
    # Count error types
    omissions = sum(1 for d in discrepancies if d.error_type == "omission")
    hallucinations = sum(1 for d in discrepancies if d.error_type == "hallucination")
    wrong_values = sum(1 for d in discrepancies if d.error_type == "wrong_value")
    format_errors = sum(1 for d in discrepancies if d.error_type == "format_error")

    # Compute TP/FP/FN
    # TP = fields in GT that match (correct)
    # FN = omissions (in GT but not extracted)
    # FP = hallucinations + wrong_values + format_errors (in extracted but wrong)

    true_positives = total_fields_gt - omissions - wrong_values - format_errors
    false_positives = hallucinations + wrong_values + format_errors
    false_negatives = omissions

    # Compute metrics with zero-division handling
    precision = (true_positives / (true_positives + false_positives)
                 if (true_positives + false_positives) > 0 else 0.0)
    recall = (true_positives / (true_positives + false_negatives)
              if (true_positives + false_negatives) > 0 else 0.0)
    f1 = (2 * (precision * recall) / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "total_fields_gt": total_fields_gt,
        "total_fields_extracted": total_fields_extracted,
        "correct_fields": true_positives,
        "errors_by_type": {
            "omission": omissions,
            "hallucination": hallucinations,
            "wrong_value": wrong_values,
            "format_error": format_errors,
        }
    }


def compute_aggregate_metrics(eval_metrics: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Compute aggregate metrics across multiple evals (macro-averaging).

    Args:
        eval_metrics: List of per-eval metric dicts

    Returns:
        Dict with aggregated metrics
    """
    if not eval_metrics:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    n = len(eval_metrics)

    # Compute macro-average (average of per-eval metrics)
    avg_precision = sum(m["precision"] for m in eval_metrics) / n
    avg_recall = sum(m["recall"] for m in eval_metrics) / n
    avg_f1 = sum(m["f1"] for m in eval_metrics) / n

    # Also compute micro-average (pooled TP/FP/FN)
    total_tp = sum(m.get("true_positives", 0) for m in eval_metrics)
    total_fp = sum(m.get("false_positives", 0) for m in eval_metrics)
    total_fn = sum(m.get("false_negatives", 0) for m in eval_metrics)

    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2 * micro_precision * micro_recall / (micro_precision + micro_recall)
                if (micro_precision + micro_recall) > 0 else 0.0)

    return {
        # Macro-average (primary metric)
        "precision": avg_precision,
        "recall": avg_recall,
        "f1": avg_f1,
        # Micro-average (pooled)
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        # Metadata
        "total_evals": n,
        "per_eval": eval_metrics,
    }
