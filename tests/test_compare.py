"""Tests for verifier field comparison."""
import pytest
from verifier.compare import (
    FieldDiscrepancy,
    normalize_text,
    values_match,
    flatten_dict,
    compare_fields,
)


class TestFieldDiscrepancy:
    def test_to_dict(self):
        d = FieldDiscrepancy("project.city", "Oakland", "San Jose", "wrong_value")
        result = d.to_dict()
        assert result == {
            "field_path": "project.city",
            "expected": "Oakland",
            "actual": "San Jose",
            "error_type": "wrong_value",
        }


class TestNormalizeText:
    def test_basic_normalization(self):
        assert normalize_text("  Hello  World  ") == "hello world"

    def test_none_handling(self):
        # normalize_text lowercases but doesn't strip sentinel values
        assert normalize_text("N/A") == "n/a"

    def test_empty_string(self):
        assert normalize_text("") == ""


class TestFlattenDict:
    def test_simple_dict(self):
        data = {"a": 1, "b": "two"}
        result = flatten_dict(data)
        assert result == {"a": 1, "b": "two"}

    def test_nested_dict(self):
        data = {"project": {"city": "Oakland", "zone": 12}}
        result = flatten_dict(data)
        assert result == {
            "project.city": "Oakland",
            "project.zone": 12,
        }

    def test_list_values(self):
        data = {"walls": [{"name": "W1"}, {"name": "W2"}]}
        result = flatten_dict(data)
        assert result == {
            "walls[0].name": "W1",
            "walls[1].name": "W2",
        }


class TestCompareFields:
    def test_identical_data(self):
        gt = {"project": {"city": "Oakland", "zone": 12}}
        ext = {"project": {"city": "Oakland", "zone": 12}}
        discrepancies = compare_fields(gt, ext)
        assert len(discrepancies) == 0

    def test_omission(self):
        gt = {"project": {"city": "Oakland", "zone": 12}}
        ext = {"project": {"city": "Oakland"}}
        discrepancies = compare_fields(gt, ext)
        omissions = [d for d in discrepancies if d.error_type == "omission"]
        assert len(omissions) == 1
        assert omissions[0].field_path == "project.zone"

    def test_hallucination(self):
        gt = {"project": {"city": "Oakland"}}
        ext = {"project": {"city": "Oakland", "extra_field": "surprise"}}
        discrepancies = compare_fields(gt, ext)
        hallucinations = [d for d in discrepancies if d.error_type == "hallucination"]
        assert len(hallucinations) == 1

    def test_wrong_value(self):
        gt = {"project": {"city": "Oakland"}}
        ext = {"project": {"city": "San Jose"}}
        discrepancies = compare_fields(gt, ext)
        wrong = [d for d in discrepancies if d.error_type == "wrong_value"]
        assert len(wrong) == 1
