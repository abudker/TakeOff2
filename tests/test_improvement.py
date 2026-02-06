"""Tests for improvement module utilities."""
import pytest
from improvement.apply import bump_version, get_bump_type, parse_instruction_version
from improvement.critic import (
    aggregate_failure_analysis,
    parse_proposal,
    InstructionProposal,
)


class TestBumpVersion:
    def test_patch_bump(self):
        assert bump_version("1.0.0", "patch") == "1.0.1"

    def test_minor_bump(self):
        assert bump_version("1.2.3", "minor") == "1.3.0"

    def test_major_bump(self):
        assert bump_version("1.2.3", "major") == "2.0.0"

    def test_invalid_bump_type(self):
        with pytest.raises(ValueError):
            bump_version("1.0.0", "invalid")


class TestGetBumpType:
    def test_add_section(self):
        assert get_bump_type("add_section") == "minor"

    def test_clarify_rule(self):
        assert get_bump_type("clarify_rule") == "patch"

    def test_restructure(self):
        assert get_bump_type("restructure") == "major"

    def test_unknown_defaults_to_patch(self):
        assert get_bump_type("unknown_type") == "patch"


class TestAggregateFailureAnalysis:
    def test_empty_results(self):
        result = aggregate_failure_analysis([])
        assert result["num_evals"] == 0
        assert result["total_discrepancies"] == 0
        assert result["dominant_error_type"] is None

    def test_single_eval(self):
        eval_results = [{
            "metrics": {
                "f1": 0.8,
                "precision": 0.9,
                "recall": 0.7,
                "errors_by_type": {"omission": 3, "hallucination": 1, "wrong_value": 0, "format_error": 0},
            },
            "discrepancies": [
                {"field_path": "project.city", "error_type": "omission", "expected": "Oakland", "actual": None},
                {"field_path": "project.zone", "error_type": "omission", "expected": 12, "actual": None},
                {"field_path": "walls[0].name", "error_type": "omission", "expected": "W1", "actual": None},
                {"field_path": "extra.field", "error_type": "hallucination", "expected": None, "actual": "val"},
            ],
        }]
        result = aggregate_failure_analysis(eval_results)
        assert result["num_evals"] == 1
        assert result["total_discrepancies"] == 4
        assert result["dominant_error_type"] == "omission"
        assert result["errors_by_domain"]["project"] == 2
        assert result["errors_by_domain"]["walls"] == 1


class TestParseProposal:
    def test_parse_json_code_block(self):
        output = """Here is my analysis.

```json
{
    "target_file": ".claude/instructions/test.md",
    "failure_pattern": "Missing orientation data",
    "hypothesis": "Instructions lack clarity",
    "proposed_change": "Add section about orientation",
    "expected_impact": "Fewer omissions"
}
```
"""
        proposal = parse_proposal(output)
        assert proposal is not None
        assert proposal.target_file == ".claude/instructions/test.md"
        assert proposal.failure_pattern == "Missing orientation data"

    def test_parse_no_json(self):
        output = "No JSON here, just text."
        proposal = parse_proposal(output)
        assert proposal is None
