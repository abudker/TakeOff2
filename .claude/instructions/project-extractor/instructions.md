# Project Extractor Instructions

**Version:** v2.0.0
**Last updated:** 2026-02-03

## Overview

The project extractor extracts building project metadata (TakeoffProjectInfo) and envelope characteristics from Title 24 compliance documentation. This is the first extraction domain, establishing project context for later zone, window, and HVAC extraction.

**Key addition in v2:** The project extractor now also captures basic thermal boundary information that helps other extractors understand the building's conditioned vs unconditioned spaces.

## Extraction Workflow

### 1. Input Reception

You will receive:
- **Page images:** List of PNG file paths from preprocessing phase
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `schedule_pages`: Pages containing building component schedules
- `cbecc_pages`: CBECC-Res software output pages
- `cf1r_pages`: CF1R compliance forms
- `drawings`: Floor plans, elevations, sections

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **CBECC-Res pages** (highest reliability)
   - Standardized software output format
   - Contains most ProjectInfo and EnvelopeInfo fields
   - Look for "CBECC-Res" header or software watermark

2. **CF1R forms** (high reliability)
   - Official compliance forms with structured fields
   - Contains climate zone, building type, envelope summary
   - Look for "CF1R" form number in header

3. **Schedule pages** (medium reliability)
   - Window schedules, wall schedules, equipment schedules
   - Contains area calculations, U-factors, equipment types
   - Cross-reference totals with CBECC data

4. **Title block / Cover page** (low reliability for most fields)
   - Project title, address, city
   - Basic project metadata only

### 3. Field Extraction Process

For each required field:

1. **Locate source:** Use field guide to identify which page types contain the field
2. **Extract value:** Read value from page image
3. **Validate format:** Ensure value matches schema constraints
4. **Record confidence:** Note if value is unclear or uncertain
5. **Handle duplicates:** If field appears on multiple pages, use this priority:
   - CBECC-Res page value (highest priority)
   - CF1R form value
   - Schedule page value
   - Title block value (lowest priority)

### 4. Data Merging Strategy

When extracting from multiple pages:

1. **Start with empty data structure:**
   ```json
   {
     "project": {},
     "envelope": {}
   }
   ```

2. **Process pages in priority order** (CBECC → CF1R → schedules → title)

3. **Merge values:** Later pages override earlier values for same field

4. **Track sources:** Note which page provided each field value

### 5. Schema Validation

Before returning extracted data, validate against schemas:

**ProjectInfo constraints:**
- `run_title`: Non-empty string
- `address`: Non-empty string
- `city`: Non-empty string
- `climate_zone`: Integer 1-16 (California climate zones)
- `fuel_type`: One of ["All Electric", "Natural Gas", "Mixed"]
- `house_type`: One of ["Single Family", "Multi Family"]
- `dwelling_units`: Integer >= 1
- `stories`: Integer >= 1
- `bedrooms`: Integer >= 0

**EnvelopeInfo constraints:**
- `conditioned_floor_area`: Float > 0
- `window_area`: Float >= 0
- `window_to_floor_ratio`: Float 0.0-1.0 (often 0.15-0.30 for residential)
- `exterior_wall_area`: Float >= 0
- `fenestration_u_factor`: Float > 0 or null (optional)

### 6. Handling Missing Data

**Required fields (cannot be null):**
- If field is missing from all pages: Report error with field name
- Do not guess or infer values
- Return error status with clear message

**Optional fields:**
- `fenestration_u_factor`: Can be null if not found
- Use `null` in JSON output

### 7. Confidence Reporting

Include an extraction `notes` field with:

**High confidence:** Field found on CBECC or CF1R page, clearly legible
**Medium confidence:** Field found on schedule page, value is clear
**Low confidence:** Field found on hand-written drawing, OCR uncertain
**Inferred:** Value calculated from other fields (e.g., WWR from window_area / CFA)

Example notes:
```
"notes": "climate_zone=12 from CBECC page (high confidence). fenestration_u_factor=0.32 area-weighted from window schedule (medium confidence). bedrooms=2 counted from floor plan (low confidence, verify)."
```

### 8. Output Format

Return JSON matching this structure:

```json
{
  "project": {
    "run_title": "Example ADU Project",
    "address": "123 Main Street",
    "city": "Berkeley",
    "climate_zone": 3,
    "fuel_type": "All Electric",
    "house_type": "Single Family",
    "dwelling_units": 1,
    "stories": 1,
    "bedrooms": 2
  },
  "envelope": {
    "conditioned_floor_area": 800.0,
    "window_area": 120.0,
    "window_to_floor_ratio": 0.15,
    "exterior_wall_area": 1200.0,
    "fenestration_u_factor": 0.30
  },
  "notes": "All values extracted from CBECC-Res page 3 with high confidence."
}
```

## Error Handling

### Common Extraction Issues

1. **Illegible text:**
   - Try multiple page images (sometimes data appears on multiple pages)
   - Report as low confidence
   - Provide best-effort extraction with disclaimer

2. **Conflicting values:**
   - Use CBECC value if available (most authoritative)
   - Note conflict in extraction notes
   - Example: "CFA shows 800 sf on floor plan but 825 sf on CBECC form. Using 825 sf."

3. **Missing pages:**
   - Check if DocumentMap indicates missing page types
   - Report which fields cannot be extracted due to missing pages

4. **Units mismatch:**
   - Convert to schema units (square feet for areas)
   - Note conversion in extraction notes

### Validation Failures

If extracted data fails schema validation:
1. Re-check source page
2. Verify value interpretation (e.g., reading "CZ 12" as climate_zone=12)
3. Check for unit conversion errors
4. If still invalid, report error with details

## Cross-Referencing Strategy

To improve accuracy, cross-reference values between pages:

- **Conditioned Floor Area:** Should match between CBECC form, floor plan area calculation, and wall schedule context
- **Window Area:** Should match between window schedule total and CBECC fenestration summary
- **Climate Zone:** Should be consistent across all forms
- **Fuel Type:** Should align with equipment schedules (gas furnace → Natural Gas or Mixed)

If cross-reference reveals discrepancy, prefer CBECC/CF1R value and note discrepancy.

## Next Steps After Extraction

The extracted JSON will be:
1. Saved to iteration directory
2. Passed to verifier agent for comparison against ground truth
3. Used to generate discrepancy reports
4. Fed back into self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all fields.

## Required Fields Checklist

Before completing extraction, verify ALL these fields are present in your output JSON. **Do NOT omit any field** - include all fields even if the value is null or zero.

### ProjectInfo - ALL Fields Required in Output

| Field | Type | If Not Found | Notes |
|-------|------|--------------|-------|
| run_id | string | null | Check CBECC header for "Run ID" or "User" |
| run_title | string | null | Project name from CBECC or title block |
| run_number | integer | 0 | Iteration number, usually 0 for initial run |
| run_scope | string | null | "Newly Constructed", "Addition", "Alteration" |
| address | string | null | Full street address |
| city | string | null | City name |
| climate_zone | integer | null | CZ 1-16 from CF1R or CBECC |
| fuel_type | enum | null | "All Electric", "Natural Gas", "Mixed" |
| house_type | enum | null | "Single Family" or "Multi Family" |
| dwelling_units | integer | 1 | Number of units (1 for typical SFR) |
| stories | integer | null | Number of above-grade stories |
| bedrooms | integer | null | Bedroom count from floor plan |
| all_orientations | boolean | false | Check CBECC settings for rotation analysis |
| attached_garage | boolean | false | Check floor plans for garage |
| front_orientation | float | null | Azimuth degrees 0-360 from CBECC or site plan |

### EnvelopeInfo - ALL Fields Required in Output

| Field | Type | If Not Found | Notes |
|-------|------|--------------|-------|
| conditioned_floor_area | float | null | CFA in sq ft from CBECC summary |
| window_area | float | null | Total fenestration area in sq ft |
| window_to_floor_ratio | float | null | WWR = window_area / CFA (0.0-1.0) |
| fenestration_u_factor | float | null | Area-weighted U-factor from CBECC |
| exterior_wall_area | float | null | Above-grade exterior walls in sq ft |
| underground_wall_area | float | 0 | Below-grade walls in sq ft (0 if none) |
| slab_floor_area | float | null | Slab-on-grade floor in sq ft |
| exposed_slab_floor_area | float | 0 | Perimeter slab exposure in sq ft |
| below_grade_floor_area | float | 0 | Basement floor in sq ft (0 if slab) |
| exposed_below_grade_floor_area | float | 0 | Basement perimeter exposure (0 if slab) |
| addition_conditioned_floor_area | float | 0 | Addition CFA (0 for new construction) |
| pv_credit_available | boolean | null | From CBECC compliance summary |
| pv_generation_max_credit | float | null | PV generation credit kWh |
| credit_available_for_pv | float | null | Compliance credit value |
| final_pv_credit | float | null | Final adjusted PV credit |
| zonal_control | boolean | null | HVAC zoning from equipment section |
| infiltration_ach50 | float | null | Air changes/hour at 50 Pa |
| infiltration_cfm50 | float | null | CFM at 50 Pa blower door |
| quality_insulation_installation | boolean | null | QII certification |

### Critical Instructions

1. **Never omit a field** - Include ALL fields listed above in your JSON output
2. **Use null for unknown values** - If a field cannot be found, use `null` (not omission)
3. **Use 0 for zero values** - For numeric fields that can be zero (basement areas for slab homes), use `0` not `null`
4. **Use false for absent features** - For booleans like attached_garage, use `false` if no garage exists
5. **Double-check before returning** - Verify your output JSON contains all 14 ProjectInfo fields and all 19 EnvelopeInfo fields

### Where to Find Commonly Missed Fields

| Field | Primary Source | Secondary Source |
|-------|----------------|------------------|
| run_id | CBECC header "Run ID:" or "User:" | First page header |
| run_number | CBECC header "Run #:" | Usually 0 |
| run_scope | CBECC "Scope:" field | CF1R project type |
| all_orientations | CBECC settings | Usually false |
| attached_garage | Floor plan | Title block notes |
| front_orientation | CBECC "Front:" field | Site plan north arrow |
| underground_wall_area | CBECC envelope summary | 0 for slab-on-grade |
| slab_floor_area | CBECC envelope summary | Often = CFA for single-story |
| exposed_slab_floor_area | CBECC envelope summary | Perimeter calculation |
| below_grade_floor_area | CBECC envelope summary | 0 for no basement |
| addition_conditioned_floor_area | CBECC summary | 0 for new construction |
