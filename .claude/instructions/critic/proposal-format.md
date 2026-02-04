# Proposal Format

**Version:** v1.0.0
**Last updated:** 2026-02-04

## JSON Schema

Proposals must follow this JSON structure:

```json
{
  "target_file": "string (path to instruction file)",
  "current_version": "string (semver, e.g., v1.0.0)",
  "proposed_version": "string (semver, e.g., v1.1.0)",
  "change_type": "string (add_section | modify_section | clarify_rule)",
  "failure_pattern": "string (description of what went wrong)",
  "hypothesis": "string (why it went wrong - instruction gap)",
  "proposed_change": "string (exact markdown text to add/modify)",
  "expected_impact": "string (what should improve)",
  "affected_error_types": ["array of strings (omission, hallucination, wrong_value, format_error)"],
  "affected_domains": ["array of strings (project, envelope, walls, windows, etc.)"],
  "estimated_f1_delta": "float (optional, estimated F1 improvement)"
}
```

## Field Descriptions

### target_file
- **Type:** String
- **Required:** Yes
- **Description:** Path to the instruction file to modify
- **Must be:** A file in `.claude/instructions/`
- **Example:** `.claude/instructions/project-extractor/instructions.md`

### current_version
- **Type:** String (semver)
- **Required:** Yes
- **Description:** Current version extracted from target file header
- **Format:** `vMAJOR.MINOR.PATCH` (e.g., `v1.0.0`)
- **How to find:** Look for `**Version:** v1.0.0` in file header

### proposed_version
- **Type:** String (semver)
- **Required:** Yes
- **Description:** New version after applying change
- **Format:** `vMAJOR.MINOR.PATCH`
- **Bump rules:**
  - add_section → minor bump (v1.0.0 → v1.1.0)
  - modify_section → minor bump (v1.0.0 → v1.1.0)
  - clarify_rule → patch bump (v1.0.0 → v1.0.1)

### change_type
- **Type:** String (enum)
- **Required:** Yes
- **Description:** Type of change being proposed
- **Valid values:**
  - `add_section`: Adding new section with new guidance
  - `modify_section`: Enhancing existing section
  - `clarify_rule`: Clarifying ambiguous instruction
- **Example:** `add_section`

### failure_pattern
- **Type:** String
- **Required:** Yes
- **Description:** Clear description of what went wrong in verification
- **Should include:**
  - Error counts and percentages
  - Dominant error type
  - Dominant domain
  - Specific examples if relevant
- **Example:** `High omission rate (154/167 errors, 92%) with dominant domain being project (9 errors) and envelope (18 errors). Fields like run_id, run_number, and run_scope consistently omitted.`

### hypothesis
- **Type:** String
- **Required:** Yes
- **Description:** Why the failure occurred (focusing on instruction gap, not code)
- **Should explain:** What is missing or unclear in the instruction that led to the error
- **Good example:** `Extractor is not explicitly instructed to extract all required project metadata fields. The instruction describes workflow but lacks a mandatory fields checklist.`
- **Bad example:** `Parser is not handling nested objects correctly.` (this is code-level)

### proposed_change
- **Type:** String (markdown)
- **Required:** Yes
- **Description:** Exact markdown text to add or modify
- **Must be:** Complete, well-formatted markdown (not a description of what to add)
- **Should include:**
  - Section header (## or ###)
  - Clear instructions
  - Examples if helpful
  - Bullet points or checklists for clarity
- **See examples below for format**

### expected_impact
- **Type:** String
- **Required:** Yes
- **Description:** Specific description of what should improve
- **Should include:**
  - Which error types should decrease
  - Which domains should improve
  - Estimated magnitude of improvement
- **Example:** `Reduce omission errors in project and envelope domains from 27 to <5. Estimated F1 improvement from 0.069 to 0.22 (+0.15).`

### affected_error_types
- **Type:** Array of strings
- **Required:** Yes
- **Description:** Which error types this change targets
- **Valid values:** `omission`, `hallucination`, `wrong_value`, `format_error`
- **Example:** `["omission"]` or `["omission", "wrong_value"]`

### affected_domains
- **Type:** Array of strings
- **Required:** Yes
- **Description:** Which domains this change targets
- **Valid values:** `project`, `envelope`, `walls`, `windows`, `zones`, `hvac`, `dhw`, `ceilings`, `slab_floors`, `wall_constructions`, `ceiling_constructions`
- **Example:** `["project", "envelope"]`

### estimated_f1_delta
- **Type:** Float
- **Required:** No (optional)
- **Description:** Estimated F1 score improvement
- **Format:** Decimal (e.g., `0.15` for +15 percentage points)
- **Example:** `0.15` (meaning F1 should increase by ~0.15)

## Example Proposals

### Example 1: Adding Required Fields Checklist

```json
{
  "target_file": ".claude/instructions/project-extractor/instructions.md",
  "current_version": "v1.0.0",
  "proposed_version": "v1.1.0",
  "change_type": "add_section",
  "failure_pattern": "High omission rate (154/167 errors, 92%). Project domain has 9 omitted fields including run_id, run_number, run_scope. Envelope domain has 18 omitted fields including underground_wall_area, slab_floor_area, pv_credit fields.",
  "hypothesis": "Project extractor instruction file describes the extraction workflow but does not explicitly list all required fields with a checklist. Agent is only extracting obvious fields it encounters, not systematically checking for all mandatory fields.",
  "proposed_change": "## Required Fields Checklist\n\nBefore completing extraction, verify ALL these fields are present in your output:\n\n**ProjectInfo - Always Required:**\n- [ ] run_id (check CBECC header)\n- [ ] run_title (project name)\n- [ ] run_number (iteration number, typically 0)\n- [ ] run_scope (typically \"Newly Constructed\" for new buildings)\n- [ ] address\n- [ ] city\n- [ ] climate_zone (CZ 1-16)\n- [ ] fuel_type (All Electric, Natural Gas, or Mixed)\n- [ ] house_type (Single Family or Multi Family)\n- [ ] dwelling_units (integer ≥ 1)\n- [ ] stories (integer ≥ 1)\n- [ ] bedrooms (integer ≥ 0)\n- [ ] all_orientations (boolean, check CBECC settings)\n- [ ] attached_garage (boolean, check floor plans)\n- [ ] front_orientation (azimuth degrees, 0-360)\n\n**EnvelopeInfo - Always Required:**\n- [ ] conditioned_floor_area (CFA in sq ft)\n- [ ] window_area (total fenestration in sq ft)\n- [ ] window_to_floor_ratio (WWR, 0.0-1.0)\n- [ ] exterior_wall_area (above grade walls in sq ft)\n- [ ] underground_wall_area (below grade walls in sq ft, 0 if none)\n- [ ] slab_floor_area (slab-on-grade in sq ft)\n- [ ] exposed_slab_floor_area (perimeter exposure in sq ft)\n- [ ] below_grade_floor_area (basement floor in sq ft, 0 if none)\n- [ ] exposed_below_grade_floor_area (basement perimeter in sq ft, 0 if none)\n- [ ] addition_conditioned_floor_area (addition CFA in sq ft, 0 if new construction)\n- [ ] pv_credit_available (boolean, check CBECC compliance)\n- [ ] pv_generation_max_credit (kWh, from PV calculations)\n- [ ] credit_available_for_pv (compliance credit value)\n- [ ] final_pv_credit (final credit after adjustments)\n- [ ] zonal_control (boolean, check HVAC zoning)\n- [ ] infiltration_ach50 (air changes per hour at 50 Pa)\n- [ ] infiltration_cfm50 (CFM at 50 Pa)\n- [ ] quality_insulation_installation (boolean, QII certification)\n\n**Important Instructions:**\n- If field not found in document: use `null` for optional fields, `0` for numeric fields that can be zero\n- Do NOT omit fields from output JSON - include all fields even if value is null\n- For boolean fields: use `true`/`false`, not null (unless truly unknown)\n- Cross-reference CBECC pages with CF1R forms for validation",
  "expected_impact": "Reduce omission errors in project domain from 9 to <2 and envelope domain from 18 to <3. Expected F1 improvement from 0.069 to approximately 0.22 (+0.15).",
  "affected_error_types": ["omission"],
  "affected_domains": ["project", "envelope"],
  "estimated_f1_delta": 0.15
}
```

### Example 2: Clarifying Numeric Precision Rules

```json
{
  "target_file": ".claude/instructions/project-extractor/instructions.md",
  "current_version": "v1.0.0",
  "proposed_version": "v1.0.1",
  "change_type": "clarify_rule",
  "failure_pattern": "Wrong value errors (7 occurrences) in numeric fields like conditioned_floor_area (expected 320, got 450.0), window_area (expected 64, got 68.0), window_to_floor_ratio (expected 0.2, got 0.151).",
  "hypothesis": "Instructions do not specify precision requirements and tolerance thresholds for numeric fields. Agent is extracting values but not following established tolerance rules (1% for areas, 0.5% for ratios).",
  "proposed_change": "## Numeric Field Precision\n\nWhen extracting numeric values, follow these precision rules:\n\n**Area Fields (square feet):**\n- Round to nearest integer for areas > 10 sq ft\n- Use 1 decimal place for areas < 10 sq ft\n- Examples: 320 (not 320.0), 68.5 (not 68.53)\n\n**Ratio Fields:**\n- Use 3 decimal places maximum\n- Example: 0.200 (not 0.20 or 0.2)\n\n**Tolerance Awareness:**\n- Small differences (<1% for areas, <0.5% for ratios) may come from rounding in CBECC vs. manual calculation\n- When values conflict between pages, prefer CBECC value (most authoritative)\n- Document discrepancies in notes field\n\n**Examples:**\n- Floor area: 320 sq ft (CBECC) vs 319.8 sq ft (floor plan) → Use 320\n- WWR: 0.200 (calculated) vs 0.199 (CBECC) → Use 0.200 (CBECC authority)",
  "expected_impact": "Reduce wrong_value errors in numeric fields from 7 to <2. Improve precision consistency across extractions.",
  "affected_error_types": ["wrong_value"],
  "affected_domains": ["envelope"],
  "estimated_f1_delta": 0.03
}
```

### Example 3: Modifying Cross-Reference Strategy

```json
{
  "target_file": ".claude/instructions/project-extractor/instructions.md",
  "current_version": "v1.1.0",
  "proposed_version": "v1.2.0",
  "change_type": "modify_section",
  "failure_pattern": "Wrong value errors occurring when same field appears on multiple pages with different values. Examples: address punctuation differences, area calculation discrepancies.",
  "hypothesis": "Cross-referencing strategy section exists but lacks clear priority rules for resolving conflicts. Agent is inconsistently choosing which source to use when values differ.",
  "proposed_change": "## Cross-Referencing Strategy\n\nTo improve accuracy, cross-reference values between pages using this priority hierarchy:\n\n**Source Priority (highest to lowest):**\n1. **CBECC-Res output pages** - Software-calculated, most authoritative\n2. **CF1R compliance forms** - Official forms, high reliability\n3. **Schedule pages** - Structured tables, medium reliability\n4. **Title block / drawings** - Informal notes, lowest reliability\n\n**Conflict Resolution Rules:**\n- If values differ, ALWAYS prefer higher-priority source\n- Document conflict in notes field with both values\n- Example note: \"CFA: 320 sf (CBECC) vs 319 sf (floor plan). Using CBECC value.\"\n\n**Specific Field Guidance:**\n\n| Field | Primary Source | Secondary Source | Conflict Rule |\n|-------|----------------|------------------|---------------|\n| conditioned_floor_area | CBECC summary | Floor plan area calc | CBECC wins |\n| window_area | CBECC fenestration | Window schedule total | CBECC wins |\n| climate_zone | CF1R form | Title block | CF1R wins |\n| fuel_type | Equipment schedule | CF1R form | Equipment wins (actual installed) |\n| address | Title block | CBECC header | Prefer most complete (with punctuation) |\n\n**Validation Checks:**\n- Window area should equal sum of individual window areas (within 1%)\n- Exterior wall area should match sum of individual wall areas (within 1%)\n- WWR should equal window_area / conditioned_floor_area (within 0.5%)\n- If validation fails, re-check sources and document discrepancy",
  "expected_impact": "Reduce wrong_value errors from inconsistent source selection. Improve extraction consistency across evaluations.",
  "affected_error_types": ["wrong_value"],
  "affected_domains": ["project", "envelope"],
  "estimated_f1_delta": 0.05
}
```

## Validation Checklist

Before submitting a proposal, verify:

- [ ] All required fields are present
- [ ] target_file is a valid path in .claude/instructions/
- [ ] current_version matches file header
- [ ] proposed_version follows bump rules for change_type
- [ ] failure_pattern includes specific data (counts, percentages)
- [ ] hypothesis explains instruction gap (not code issue)
- [ ] proposed_change is complete markdown (not description)
- [ ] expected_impact is specific and measurable
- [ ] affected_error_types contains valid values
- [ ] affected_domains contains valid values
- [ ] JSON is valid and parseable
