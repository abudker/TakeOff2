---
phase: 05-manual-improvement-loop
plan: 02
subsystem: improvement-loop
tags: [rich, terminal-ui, version-management, interactive-review]

# Dependency graph
requires:
  - phase: 05-01
    provides: "Critic agent and InstructionProposal schema"
provides:
  - "Rich-based interactive proposal review UI"
  - "Instruction file version management and application"
  - "Snapshot/rollback capability for instruction changes"
affects: [05-03]

# Tech tracking
tech-stack:
  added: [rich>=13.9]
  patterns: ["Rich console for terminal UI", "Semantic versioning for instruction files", "Snapshot-based rollback"]

key-files:
  created:
    - src/improvement/review.py
    - src/improvement/apply.py
  modified: []

key-decisions:
  - "Rich library for terminal UI with syntax highlighting"
  - "Semantic versioning on instruction files (vX.Y.Z in header)"
  - "Snapshot saved to iteration directories before modification"
  - "Editor integration via $EDITOR environment variable"

patterns-established:
  - "Instruction file versioning: version in header, bumped on changes"
  - "Snapshot naming: {agent-name}-{file-stem}-vX.Y.Z.md"
  - "Version bump mapping: add_section/modify_section=minor, clarify_rule=patch"

# Metrics
duration: 2min
completed: 2026-02-03
---

# Phase 05 Plan 02: Interactive Review and Application Summary

**Rich-based proposal review UI with accept/edit/reject workflow and semantic versioning for instruction file modifications**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-03T22:10:15Z
- **Completed:** 2026-02-03T22:12:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Interactive proposal presentation with Rich UI including syntax-highlighted markdown
- Editor integration for proposal editing via $EDITOR
- Before/after metrics comparison table with color-coded deltas
- Semantic version parsing and bumping for instruction files
- Snapshot/rollback system saving previous versions to iteration directories

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Rich-Based Interactive Review** - `1c1c9fd` (feat)
   - Rich UI proposal display with panels, syntax highlighting
   - User decision prompts (accept/edit/reject/skip)
   - Editor integration for proposal modification
   - Metrics comparison table

2. **Task 2: Create Proposal Application Logic** - `cf469db` (feat)
   - Version parsing from instruction file headers
   - Semantic version bumping (major/minor/patch)
   - Proposal application with version bump
   - Snapshot saving and rollback functionality

**Plan metadata:** (to be added in final commit)

## Files Created/Modified

- `src/improvement/review.py` - Rich-based interactive proposal review
  - `present_proposal()` - Display formatted proposal and get user decision
  - `edit_proposal()` - Open $EDITOR for proposal modification
  - `show_metrics_comparison()` - Display before/after metrics table

- `src/improvement/apply.py` - Proposal application with version management
  - `parse_instruction_version()` - Extract version from file header
  - `bump_version()` - Semantic version bumping
  - `apply_proposal()` - Apply change and bump version
  - `save_instruction_snapshot()` - Archive version to iteration directory
  - `rollback_instruction()` - Restore from snapshot

## Decisions Made

- **Rich library for UI**: Provides excellent terminal formatting with syntax highlighting, tables, and panels
- **Semantic versioning**: Instruction files follow vX.Y.Z in header, bumped according to change_type
- **Version bump rules**: add_section/modify_section=minor (new functionality), clarify_rule/fix_typo=patch (fixes), restructure=major (breaking changes)
- **Snapshot location**: Saved to iteration directories under instruction-changes/ subdirectory for auditability
- **Editor integration**: Uses $EDITOR or $VISUAL environment variable, falls back to vim

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully with verification passing.

## User Setup Required

None - no external service configuration required. Rich library installed as Python dependency.

## Next Phase Readiness

Ready for Plan 03 (Orchestration and Loop Control):
- Proposal review UI complete and verified
- Application logic handles version management
- Snapshots enable rollback if needed
- All functions tested and working

Blueprint for next plan:
- Orchestrate full loop: extract → verify → critic → review → apply → re-extract
- Handle iteration directories and state tracking
- Implement improvement metrics and convergence detection

---
*Phase: 05-manual-improvement-loop*
*Completed: 2026-02-03*
