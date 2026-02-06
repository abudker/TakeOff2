"""Tests for verifier metrics computation."""
import pytest
from verifier.compare import FieldDiscrepancy
from verifier.metrics import compute_field_level_metrics, compute_aggregate_metrics


class TestFieldLevelMetrics:
    def test_perfect_extraction(self):
        """No discrepancies means perfect scores."""
        result = compute_field_level_metrics(
            discrepancies=[],
            total_fields_gt=10,
            total_fields_extracted=10,
        )
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["f1"] == 1.0
        assert result["true_positives"] == 10

    def test_all_omissions(self):
        """All fields omitted means 0 recall."""
        discrepancies = [
            FieldDiscrepancy("field1", "val1", None, "omission"),
            FieldDiscrepancy("field2", "val2", None, "omission"),
        ]
        result = compute_field_level_metrics(
            discrepancies=discrepancies,
            total_fields_gt=2,
            total_fields_extracted=0,
        )
        assert result["recall"] == 0.0
        assert result["false_negatives"] == 2

    def test_all_hallucinations(self):
        """All hallucinated fields means 0 precision."""
        discrepancies = [
            FieldDiscrepancy("extra1", None, "val1", "hallucination"),
            FieldDiscrepancy("extra2", None, "val2", "hallucination"),
        ]
        result = compute_field_level_metrics(
            discrepancies=discrepancies,
            total_fields_gt=0,
            total_fields_extracted=2,
        )
        assert result["precision"] == 0.0
        assert result["false_positives"] == 2

    def test_mixed_errors(self):
        """Mix of error types."""
        discrepancies = [
            FieldDiscrepancy("field1", "a", None, "omission"),
            FieldDiscrepancy("field2", "b", "c", "wrong_value"),
            FieldDiscrepancy("extra", None, "d", "hallucination"),
        ]
        result = compute_field_level_metrics(
            discrepancies=discrepancies,
            total_fields_gt=5,
            total_fields_extracted=5,
        )
        assert result["true_positives"] == 3  # 5 - 1 omission - 1 wrong_value
        assert result["false_positives"] == 2  # 1 hallucination + 1 wrong_value
        assert result["false_negatives"] == 1  # 1 omission
        assert result["errors_by_type"]["omission"] == 1
        assert result["errors_by_type"]["wrong_value"] == 1
        assert result["errors_by_type"]["hallucination"] == 1

    def test_true_positives_never_negative(self):
        """TP should be clamped to 0 even with many errors."""
        discrepancies = [
            FieldDiscrepancy(f"field{i}", "a", "b", "wrong_value")
            for i in range(10)
        ]
        result = compute_field_level_metrics(
            discrepancies=discrepancies,
            total_fields_gt=3,
            total_fields_extracted=10,
        )
        assert result["true_positives"] >= 0

    def test_zero_fields(self):
        """Edge case: no fields at all."""
        result = compute_field_level_metrics(
            discrepancies=[],
            total_fields_gt=0,
            total_fields_extracted=0,
        )
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["f1"] == 0.0


class TestAggregateMetrics:
    def test_empty_input(self):
        result = compute_aggregate_metrics([])
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["f1"] == 0.0

    def test_single_eval(self):
        metrics = [{"precision": 0.8, "recall": 0.6, "f1": 0.686,
                     "true_positives": 6, "false_positives": 2, "false_negatives": 4}]
        result = compute_aggregate_metrics(metrics)
        assert result["precision"] == 0.8
        assert result["recall"] == 0.6
        assert result["total_evals"] == 1

    def test_macro_average(self):
        metrics = [
            {"precision": 1.0, "recall": 0.5, "f1": 0.667,
             "true_positives": 5, "false_positives": 0, "false_negatives": 5},
            {"precision": 0.5, "recall": 1.0, "f1": 0.667,
             "true_positives": 5, "false_positives": 5, "false_negatives": 0},
        ]
        result = compute_aggregate_metrics(metrics)
        assert result["precision"] == 0.75  # (1.0 + 0.5) / 2
        assert result["recall"] == 0.75    # (0.5 + 1.0) / 2
        assert result["total_evals"] == 2
