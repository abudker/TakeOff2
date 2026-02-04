---
phase: 05-manual-improvement-loop
plan: 03
subsystem: cli
tags: [click, subprocess, cli, improvement-loop, git]

# Dependency graph
requires:
  - phase: 05-01
    provides: Critic agent and failure analysis infrastructure
  - phase: 05-02
    provides: Interactive proposal review and application system
provides:
  - CLI commands for running improvement loop (improve, rollback)
  - Integration with existing agents and verifier CLIs
  - Auto-commit with metrics tracking
affects: [06-autonomous-improvement-loop]

# Tech tracking
tech-stack:
  added: []
  patterns: [subprocess-cli-integration, iteration-tracking]

key-files:
  created:
    - src/improvement/cli.py
    - src/improvement/__main__.py
    - src/agents/__main__.py
  modified:
    - src/improvement/__init__.py

key-decisions:
  - "CLI orchestrates via subprocess (python3 -m agents, python3 -m verifier) not direct imports"
  - "Iteration number tracked globally (max across all evals + 1)"
  - "Auto-commit with metrics delta in commit message"
  - "Rollback by copying snapshots from iteration directories"

patterns-established:
  - "Subprocess pattern: Use subprocess.run() to invoke other CLIs for orchestration"
  - "Iteration tracking: get_next_iteration() finds max across all evals and increments"
  - "Metrics aggregation: Macro average F1/precision/recall across all eval results"

# Metrics
duration: 2min
completed: 2026-02-04
---

# Phase 5 Plan 3: Improvement CLI Summary

**CLI commands for improvement loop orchestration: improve runs full cycle (analyze→critic→review→apply→extract→verify→commit), rollback restores previous iterations**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-04T05:21:21Z
- **Completed:** 2026-02-04T05:23:42Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- improve command orchestrates complete improvement loop with 8 steps
- rollback command restores instruction snapshots from any iteration
- Integration with agents extract-all and verifier verify-all via subprocess
- Auto-commit with before/after metrics delta in message
- CLI accessible via `python3 -m improvement`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Improvement CLI Commands** - `0a35125` (feat)
2. **Task 2: Verify End-to-End Integration** - `6c8615c` (test)

**Plan metadata:** (pending)

## Files Created/Modified
- `src/improvement/cli.py` - CLI with improve and rollback commands
- `src/improvement/__main__.py` - Module entry point for python -m improvement
- `src/agents/__main__.py` - Module entry point for python -m agents (prerequisite)
- `src/improvement/__init__.py` - Updated to expose CLI and all improvement components

## Decisions Made

**CLI orchestration via subprocess:**
- Calls `python3 -m agents extract-all` and `python3 -m verifier verify-all` via subprocess
- Rationale: Clean separation, allows CLI tools to be used independently or orchestrated

**Global iteration tracking:**
- Next iteration = max(all eval iterations) + 1
- Rationale: All evals progress together through iterations, maintains synchronization

**Auto-commit with metrics:**
- Commit message includes F1/precision/recall delta
- Rationale: Git history tracks improvement progress, easy to see which changes helped

**python3 instead of python:**
- Use `python3` explicitly in subprocess calls
- Rationale: MacOS has python2 as default python, python3 is explicit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added agents/__main__.py**
- **Found during:** Task 1 (prerequisite CLI check)
- **Issue:** `python -m agents` failed - agents module had no __main__.py entry point
- **Fix:** Created src/agents/__main__.py importing and calling cli()
- **Files modified:** src/agents/__main__.py (new)
- **Verification:** `python3 -m agents --help` succeeds
- **Committed in:** 0a35125 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for CLI integration. No scope creep.

## Issues Encountered

**Python command not found:**
- Issue: MacOS has `python3` not `python` by default
- Resolution: Used `python3` explicitly in all subprocess calls and verification scripts

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 04 (End-to-End Test):**
- All Python components complete and tested
- CLI commands accessible and verified
- Integration points confirmed working
- Awaiting full end-to-end test with critic agent invocation

**Note:** Full critic invocation test (subprocess.run with `claude --agent critic`) will be tested in Plan 04 checkpoint, as it requires Claude CLI and real eval data.

---
*Phase: 05-manual-improvement-loop*
*Completed: 2026-02-04*
