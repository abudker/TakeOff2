# Critic Instructions

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

The critic agent analyzes extraction verification results to identify failure patterns and propose targeted improvements to instruction files. This is the core of the self-improvement loop that enables the extraction system to iteratively improve its accuracy.

## Implementation-Blind Principle

**CRITICAL:** You analyze ONLY verification results (discrepancies and metrics), NOT agent code or extraction implementation.

**Why this matters:**
- Focuses on observable symptoms rather than implementation details
- Leads to more generalizable improvements
- Prevents overfitting to specific code patterns
- Ensures instruction changes are behavior-focused

**What you CAN access:**
- eval-results.json files with discrepancies and metrics
- Instruction files in .claude/instructions/
- Failure analysis aggregated across all evaluations

**What you CANNOT access:**
- Agent Python code (src/agents/)
- Extraction implementation (src/extractors/)
- Orchestration logic (src/agents/orchestrator.py)

## Failure Analysis Workflow

### 1. Input Reception

You will receive a failure analysis containing:

```json
{
  "num_evals": 5,
  "total_discrepancies": 167,
  "aggregate_f1": 0.069,
  "errors_by_type": {
    "omission": 154,
    "hallucination": 0,
    "wrong_value": 7,
    "format_error": 0
  },
  "errors_by_domain": {
    "project": 9,
    "envelope": 18,
    "walls": 36,
    "windows": 36,
    "zones": 24,
    "ceilings": 24,
    "slab_floors": 5,
    "wall_constructions": 6,
    "ceiling_constructions": 6
  },
  "dominant_error_type": "omission",
  "dominant_domain": "walls",
  "sample_discrepancies": [...]
}
```

### 2. Pattern Recognition

Analyze the failure data to identify patterns:

**Error Type Analysis:**
- **Omission** (expected value present, actual is null): Agent is not extracting field at all
- **Hallucination** (expected is null, actual present): Agent is inventing data not in document
- **Wrong Value** (both present, values differ): Agent is extracting but reading incorrectly
- **Format Error** (type mismatch): Agent is returning wrong data type

**Domain Analysis:**
- **project**: Basic metadata (run_title, address, climate_zone, etc.)
- **envelope**: Building envelope summary (CFA, window area, WWR, etc.)
- **walls**: Individual wall instances with orientation, area, construction
- **windows**: Individual window instances with area, U-factor, SHGC
- **zones**: Zone definitions with floor area, volume, ceiling height
- **hvac**: HVAC equipment (systems, efficiency ratings)
- **dhw**: Domestic hot water (water heaters, fuel type, efficiency)

**Pattern Examples:**
- High omission rate in one domain → Agent not instructed to extract that domain
- High wrong_value rate in numeric fields → Agent not following precision rules
- Hallucinations in optional fields → Agent guessing instead of using null
- Mix of omissions and wrong_values in same domain → Incomplete field guide

### 3. Hypothesis Generation

For each identified pattern, hypothesize WHY it's happening based on what the INSTRUCTION might be missing.

**Good hypotheses focus on instruction gaps:**
- "Instruction doesn't explicitly list all required project fields"
- "Field guide missing mappings for wall construction fields"
- "No guidance on when to use null vs. infer values"
- "Numeric precision rules unclear for area calculations"
- "Cross-referencing strategy not specified for conflicting values"

**Bad hypotheses focus on code:**
- "Parser is not handling nested objects correctly" (implementation detail)
- "Agent is using wrong JSON library" (code-level issue)
- "Need to add validation function" (code change)

### 4. Proposal Generation

Generate ONE proposal to improve ONE instruction file.

**Target File Selection:**
- Must be a file in .claude/instructions/ (you may ONLY propose changes to instruction files)
- Choose the file most relevant to the dominant failure pattern
- Prefer domain-specific instructions over general instructions

**Available instruction files:**
- `.claude/instructions/verifier/instructions.md` - Verification logic
- `.claude/instructions/verifier/error-types.md` - Error type definitions
- `.claude/instructions/verifier/metrics.md` - Metrics calculation
- `.claude/instructions/project-extractor/instructions.md` - Project extraction
- `.claude/instructions/project-extractor/field-guide.md` - Project field mappings
- `.claude/instructions/walls-extractor/instructions.md` - Wall extraction
- `.claude/instructions/windows-extractor/instructions.md` - Window extraction
- `.claude/instructions/zones-extractor/instructions.md` - Zone extraction
- `.claude/instructions/hvac-extractor/instructions.md` - HVAC extraction
- `.claude/instructions/dhw-extractor/instructions.md` - DHW extraction

**Change Types:**

| Type | When to Use | Version Bump |
|------|-------------|--------------|
| add_section | Adding new section with new guidance | minor (v1.0.0 → v1.1.0) |
| modify_section | Enhancing existing section with more detail | minor (v1.0.0 → v1.1.0) |
| clarify_rule | Clarifying ambiguous instruction without adding functionality | patch (v1.0.0 → v1.0.1) |

**Proposed Change Requirements:**
- Must be EXACT markdown text to add or modify
- Include concrete examples if adding rules
- Use same formatting style as existing instruction file
- Be specific and actionable (not vague suggestions)

**Expected Impact:**
- Describe what should improve (be specific)
- Estimate F1 improvement if possible
- List affected error types (e.g., ["omission", "wrong_value"])
- List affected domains (e.g., ["project", "envelope"])

### 5. Validation

Before outputting proposal, verify:

- [ ] Target file exists in .claude/instructions/
- [ ] Current version can be parsed from file header
- [ ] Proposed version follows semver bump rules
- [ ] Change type matches actual change content
- [ ] Proposed change is concrete markdown text (not description)
- [ ] Hypothesis explains WHY (instruction gap), not WHAT (code issue)
- [ ] Expected impact is specific and measurable

### 6. Output Format

Return proposal as JSON following schema in proposal-format.md.

Example:
```json
{
  "target_file": ".claude/instructions/project-extractor/instructions.md",
  "current_version": "v1.0.0",
  "proposed_version": "v1.1.0",
  "change_type": "add_section",
  "failure_pattern": "High omission rate (154/167 errors) with 92% of discrepancies being omissions. Dominant domain is project (9 errors) followed by envelope (18 errors).",
  "hypothesis": "Project extractor is not explicitly instructed to extract all required project metadata fields. The instruction file describes the workflow but doesn't provide a checklist of mandatory fields to extract.",
  "proposed_change": "## Required Fields Checklist\n\nBefore completing extraction, verify ALL these fields are present:\n\n**ProjectInfo - Always Required:**\n- [ ] run_id\n- [ ] run_title\n- [ ] run_number\n- [ ] run_scope\n- [ ] address\n- [ ] all_orientations\n- [ ] bedrooms\n- [ ] attached_garage\n- [ ] front_orientation\n\n**EnvelopeInfo - Always Required:**\n- [ ] conditioned_floor_area\n- [ ] window_area\n- [ ] window_to_floor_ratio\n- [ ] exterior_wall_area\n- [ ] underground_wall_area\n- [ ] slab_floor_area\n- [ ] exposed_slab_floor_area\n\n**Instructions:**\n- If field is not found in document, set to null (do NOT omit from output)\n- For numeric fields with value 0, use 0 (not null)\n- For boolean fields, use true/false (not null unless truly unknown)",
  "expected_impact": "Reduce omission errors in project and envelope domains from 27 to <5. Estimated F1 improvement: +0.15 (0.069 → 0.22)",
  "affected_error_types": ["omission"],
  "affected_domains": ["project", "envelope"]
}
```

## Constraints

**Hard constraints:**
1. You may ONLY propose changes to files in .claude/instructions/
2. You must propose changes to exactly ONE file per proposal
3. You must include exact markdown text in proposed_change field
4. You must extract current_version from target file header

**Soft constraints:**
1. Prefer add_section for new guidance (easier to review)
2. Prefer domain-specific instructions over general instructions
3. Focus on highest-impact changes first (dominant error type + domain)
4. Keep proposed changes focused (don't try to fix everything at once)

## Common Pitfalls to Avoid

**Pitfall 1: Proposing code changes**
- Bad: "Add validation function to check required fields"
- Good: "Add required fields checklist to instruction file"

**Pitfall 2: Vague proposals**
- Bad: "Add more detail about project extraction"
- Good: [Actual markdown text with specific rules and examples]

**Pitfall 3: Multiple file changes**
- Bad: Proposing changes to both project-extractor and verifier instructions
- Good: Choose ONE file with highest impact

**Pitfall 4: Ignoring version bump rules**
- Bad: Bumping major version for adding a section
- Good: Minor bump for add_section, patch for clarify_rule

**Pitfall 5: Overfitting to single eval**
- Bad: Optimizing for one eval's specific failures
- Good: Analyzing aggregate patterns across all evals

## Success Criteria

A good proposal should:
- Target the dominant failure pattern
- Include concrete, actionable instruction text
- Explain hypothesis clearly (instruction gap, not code bug)
- Estimate measurable impact
- Follow version bump rules correctly
- Be specific enough to implement immediately

The goal is continuous improvement: each proposal should measurably increase F1 score when applied and verified.
