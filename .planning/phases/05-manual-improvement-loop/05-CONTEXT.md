# Phase 5: Manual Improvement Loop - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Critic agent analyzes extraction failures and proposes targeted changes to instruction files. User reviews proposals inline, can accept/edit/reject, and accepted changes trigger automatic re-extraction and verification. Each iteration is tracked in numbered folders with auto-commits. This phase is manual (human in the loop) — full automation is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Human review flow
- Proposals displayed inline in terminal (not written to separate files)
- Three actions available: Accept, Edit, Reject
- After accepting a proposal, extraction + verification runs automatically
- User sees before/after metrics comparison immediately

### Iteration tracking
- Each iteration stored in numbered folder: `iteration-001/`, `iteration-002/`, etc.
- Each accepted proposal auto-commits with metrics in commit message
- Rollback works by copying instruction files from previous iteration folder (not git revert)

### Claude's Discretion
- Edit mechanism when user chooses "Edit" (could be $EDITOR, inline paste, etc.)
- Level of detail in iteration records (minimal vs full context with diffs)
- Proposal format and presentation in terminal

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-manual-improvement-loop*
*Context gathered: 2026-02-04*
