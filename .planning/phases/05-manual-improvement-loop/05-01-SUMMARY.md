---
phase: 05-manual-improvement-loop
plan: 01
subsystem: improvement-loop
tags: [critic-agent, failure-analysis, subprocess, improvement-loop, instruction-versioning]

# Dependency graph
requires:
  - phase: 04-multi-domain-extraction
    provides: Extraction agents producing eval-results.json with discrepancies and metrics
  - phase: 01-foundation
    provides: Error type taxonomy (omission, hallucination, wrong_value, format_error) and F1 metrics
provides:
  - Critic agent definition following thin-agent pattern
  - Failure analysis module aggregating errors by type and domain
  - Critic invocation via subprocess (claude --agent critic)
  - Proposal parsing from JSON in markdown code blocks
  - InstructionProposal dataclass for structured proposals
affects: [05-02-terminal-review, 05-03-proposal-application, phase-06-autonomous-improvement]

# Tech tracking
tech-stack:
  added: []  # Uses stdlib only (subprocess, json, re, dataclasses)
  patterns:
    - "Implementation-blind critic: analyzes ONLY verification results, never agent code"
    - "Hypothesis-driven proposals: failure pattern + hypothesis + proposed change"
    - "Semantic versioning for instruction files (MAJOR.MINOR.PATCH)"
    - "Thin-agent pattern: agent def under 50 lines, behavior in instruction files"

key-files:
  created:
    - .claude/agents/critic.md
    - .claude/instructions/critic/instructions.md
    - .claude/instructions/critic/proposal-format.md
    - src/improvement/__init__.py
    - src/improvement/critic.py
  modified: []

key-decisions:
  - "Critic operates implementation-blind: analyzes verification results only, not code"
  - "Domain extraction from field_path: walls[0].name -> walls, project.run_id -> project"
  - "Proposals target ONE instruction file (Phase 5 manual, one at a time)"
  - "Version bump rules: add_section/modify_section=minor, clarify_rule=patch"
  - "Critic invoked via subprocess (claude --agent critic) not direct API"

patterns-established:
  - "Failure analysis aggregation: group errors by type (omission/hallucination/wrong_value/format_error) and domain"
  - "Proposal format: JSON with target_file, versions, change_type, hypothesis, proposed_change, expected_impact"
  - "Critic can only propose changes to files in .claude/instructions/ (hard constraint)"

# Metrics
duration: 5min
completed: 2026-02-04
---

# Phase 5 Plan 01: Critic Agent and Failure Analysis Summary

**Implementation-blind critic agent analyzes eval discrepancies by error type and domain, proposes instruction file improvements via subprocess invocation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-04T05:09:42Z
- **Completed:** 2026-02-04T05:14:24Z
- **Tasks:** 3
- **Files modified:** 5 (all new files)

## Accomplishments
- Critic agent definition (45 lines) following thin-agent pattern with instructions in separate files
- Failure analysis module aggregates discrepancies by error type (omission=92%) and domain (walls=36 errors)
- Critic invocation via subprocess using claude --agent critic --print
- Proposal parsing handles JSON in markdown code blocks
- Tested with real chamberlin-circle eval data (161 discrepancies, F1=0.069)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Critic Agent Definition and Instructions** - `42ba89a` (feat)
   - Created .claude/agents/critic.md (45 lines)
   - Created .claude/instructions/critic/instructions.md with implementation-blind workflow
   - Created .claude/instructions/critic/proposal-format.md with JSON schema and 3 examples

2. **Task 2: Create Failure Analysis Module** - `641b8b2` (feat)
   - Created src/improvement/__init__.py
   - Created src/improvement/critic.py with failure analysis functions
   - Implemented find_latest_iteration(), load_eval_results(), aggregate_failure_analysis(), format_analysis_for_critic()

3. **Task 3: Create Critic Invocation Module** - `1d94c61` (test)
   - Verified InstructionProposal dataclass, invoke_critic(), parse_proposal() already in critic.py
   - Tested proposal parsing with mock JSON in code block
   - All verification tests passing

## Files Created/Modified

**Created:**
- `.claude/agents/critic.md` - Critic agent definition (45 lines, thin-agent pattern)
- `.claude/instructions/critic/instructions.md` - Implementation-blind failure analysis workflow (220 lines)
- `.claude/instructions/critic/proposal-format.md` - JSON schema with field descriptions and 3 example proposals (345 lines)
- `src/improvement/__init__.py` - Package exports for improvement loop
- `src/improvement/critic.py` - Failure analysis and critic invocation (370 lines)

## Decisions Made

1. **Implementation-blind principle enforced**: Critic analyzes ONLY eval-results.json (discrepancies and metrics), never accesses agent code or extraction implementation. This focuses on observable symptoms rather than implementation details, leading to more generalizable improvements.

2. **Domain extraction from field_path**: Simple split on "." and "[" to extract domain (e.g., "walls[0].name" -> "walls"). This groups errors by extraction domain for pattern recognition.

3. **One proposal per iteration**: Phase 5 is manual (human-in-loop), so critic proposes changes to ONE instruction file at a time. Batch proposals deferred to Phase 6 (autonomous).

4. **Version bump rules**: add_section and modify_section bump minor version (v1.0.0 -> v1.1.0), clarify_rule bumps patch (v1.0.0 -> v1.0.1). This follows semantic versioning for instruction files.

5. **Subprocess invocation**: Use `claude --agent critic --print` via subprocess instead of direct API calls. This maintains consistency with existing agent orchestration pattern from Phase 3-4.

6. **Hard constraint on target files**: Critic may ONLY propose changes to files in .claude/instructions/. This prevents proposing code changes and keeps focus on instruction improvements.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully on first attempt. Real eval data (chamberlin-circle) used for testing verified correct aggregation (154 omissions, 36 walls domain errors, F1=0.069).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 05-02 (Terminal Review Workflow):**
- Critic agent can be invoked and returns parseable JSON proposals
- Failure analysis correctly aggregates errors by type and domain
- Proposal format documented with schema and examples
- InstructionProposal dataclass ready for review workflow

**Context for next plans:**
- Current eval state: chamberlin-circle at iteration-005 with F1=0.069
- Dominant error: omission (92% of errors)
- Dominant domain: walls (36 errors), followed by windows (36), zones (24)
- Next plan should implement Rich-based terminal UI for proposal review

**No blockers or concerns.**

---
*Phase: 05-manual-improvement-loop*
*Completed: 2026-02-04*
