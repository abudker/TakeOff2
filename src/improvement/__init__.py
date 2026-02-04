"""Improvement loop infrastructure for self-improving extraction system."""

from .critic import (
    find_latest_iteration,
    load_eval_results,
    aggregate_failure_analysis,
    format_analysis_for_critic,
    InstructionProposal,
    invoke_critic,
    parse_proposal,
)

__all__ = [
    "find_latest_iteration",
    "load_eval_results",
    "aggregate_failure_analysis",
    "format_analysis_for_critic",
    "InstructionProposal",
    "invoke_critic",
    "parse_proposal",
]
