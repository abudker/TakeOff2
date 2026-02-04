"""Improvement loop infrastructure for self-improving extraction system."""

from .cli import cli
from .critic import (
    find_latest_iteration,
    load_eval_results,
    aggregate_failure_analysis,
    format_analysis_for_critic,
    InstructionProposal,
    invoke_critic,
    parse_proposal,
)
from .review import present_proposal, edit_proposal, show_metrics_comparison
from .apply import apply_proposal, rollback_instruction

__all__ = [
    "cli",
    "find_latest_iteration",
    "load_eval_results",
    "aggregate_failure_analysis",
    "format_analysis_for_critic",
    "InstructionProposal",
    "invoke_critic",
    "parse_proposal",
    "present_proposal",
    "edit_proposal",
    "show_metrics_comparison",
    "apply_proposal",
    "rollback_instruction",
]
