# Project Extractor Instructions

**Version:** v2.1.0
**Last updated:** 2026-02-04

## Overview

The project extractor extracts building project metadata (TakeoffProjectInfo) and envelope characteristics from Title 24 compliance documentation. This is the first extraction domain, establishing project context for later zone, window, and HVAC extraction.

**Key responsibilities:**
1. Initialize and verify project basics (name, address, city, jurisdiction)
2. Determine orientation basis (north arrow, front orientation)
3. Capture basic thermal boundary context (conditioned floor area)
4. Add FLAGS for any missing or inconsistent values

## Extraction Workflow

### 1. Input Reception

You will receive:
- **Page images:** List of PNG file paths from preprocessing phase
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `schedule_pages`: Pages containing building component schedules
- `drawing_pages`: Floor plans, elevations, sections
- `other`: Cover pages, notes, specifications

**NOTE:** CBECC-Res compliance forms are NOT typically included in architectural plan sets. The source documents are architectural PDFs (floor plans, schedules, title blocks). Do not expect to find CBECC pages.

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **Title block / Cover page** (highest reliability for project info)
   - Project name, address, city
   - Architect/engineer information
   - Project number and date

2. **Schedule pages** (high reliability for building data)
   - Window schedules with U-factors and SHGC
   - Equipment schedules with HVAC and DHW specs
   - Door schedules with dimensions
   - Contains area calculations, U-factors, equipment types

3. **Floor plans** (medium reliability for dimensions/counts)
   - Room layout and labels
   - Bedroom count
   - Conditioned floor area (from area callouts)
   - Window and door locations

4. **Energy notes / General notes** (supplemental)
   - Climate zone references
   - Insulation specifications
   - Equipment specifications
   - May contain Title 24 compliance notes

### 3. Field Extraction Process

For each required field:

1. **Locate source:** Use field guide to identify which page types contain the field
2. **Extract value:** Read value from page image
3. **Validate format:** Ensure value matches schema constraints
4. **Record confidence:** Note if value is unclear or uncertain
5. **Handle duplicates:** If field appears on multiple pages, use this priority:
   - Title block value (highest priority for address/city/name)
   - Schedule page value (highest priority for technical data)
   - Floor plan value
   - Energy notes value (lowest priority)

### 4. Data Merging Strategy

When extracting from multiple pages:

1. **Start with empty data structure:**
   ```json
   {
     "project": {},
     "envelope": {}
   }
   ```

2. **Process pages in priority order** (title block → schedules → floor plans → notes)

3. **Merge values:** Later pages override earlier values for same field

4. **Track sources:** Note which page provided each field value

### 5. Orientation and Rotation Tracking

**Step 1: Find the Site Plan**
- Record the north arrow direction and any bearings
- Note if site plan shows true north or project north

**Step 2: Find the Floor Plan(s)**
- Confirm a north arrow exists and matches the Site Plan
- If floor plan north is missing or conflicts: use Site Plan north as governing and add FLAG

**Step 3: Determine front_orientation**
- Look for north arrow on site plan or floor plan
- Determine front of building from street orientation or main entry
- Example: "Front: 73°" means front wall faces NE (73 degrees clockwise from north)
- 0 = North, 90 = East, 180 = South, 270 = West
- This is CRITICAL for multi-orientation energy analysis

**Step 4: Add FLAG if orientation unclear**
- If north arrow missing: FLAG "North arrow not found on floor plan. Verify orientation."
- If conflict between site and floor plan: FLAG "Site plan and floor plan north arrows conflict."

### 6. Schema Validation

Before returning extracted data, validate against schemas:

**ProjectInfo constraints:**
- `run_id`: String identifier (often "User" or blank)
- `run_title`: The CBECC analysis run title, NOT the project name (e.g., "Title 24 Analysis")
- `address`: Non-empty string (include unit number if ADU)
- `city`: Non-empty string
- `climate_zone`: Integer 1-16 (California climate zones)
- `fuel_type`: One of ["All Electric", "Natural Gas", "Mixed"]
- `house_type`: One of ["Single Family", "Multi Family"]
- `dwelling_units`: Integer >= 1
- `stories`: Integer >= 1
- `bedrooms`: Integer >= 0
- `front_orientation`: Float 0-360 (degrees from true north)

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

**High confidence:** Field found on schedule or title block, clearly legible
**Medium confidence:** Field found on floor plan annotation, value is clear
**Low confidence:** Field found on hand-written drawing, OCR uncertain
**Inferred:** Value calculated from other fields (e.g., WWR from window_area / CFA)

Example notes:
```
"notes": "climate_zone=12 from energy notes (high confidence). fenestration_u_factor=0.32 area-weighted from window schedule (medium confidence). bedrooms=2 counted from floor plan (low confidence, verify)."
```

### 8. Output Format

Return JSON matching this structure:

```json
{
  "project": {
    "run_id": null,
    "run_title": "123 Example Street ADU",
    "address": "123 Example Street ADU",
    "city": "Sacramento",
    "climate_zone": 12,
    "fuel_type": "All Electric",
    "house_type": "Single Family",
    "dwelling_units": 1,
    "stories": 1,
    "bedrooms": 1,
    "front_orientation": 45
  },
  "envelope": {
    "conditioned_floor_area": 450.0,
    "window_area": 72.0,
    "window_to_floor_ratio": 0.16,
    "exterior_wall_area": 680.0,
    "slab_floor_area": 450.0,
    "fenestration_u_factor": 0.30,
    "underground_wall_area": 0,
    "exposed_slab_floor_area": 72.0,
    "below_grade_floor_area": 0,
    "exposed_below_grade_floor_area": 0,
    "addition_conditioned_floor_area": 0
  },
  "flags": [
    {
      "field_path": "project.front_orientation",
      "severity": "medium",
      "reason": "Front orientation calculated from site plan north arrow. Verify entry direction.",
      "source_page": 3
    }
  ],
  "notes": "Project values from title block and schedules. Front orientation = 45 degrees (NE facing). Slab-on-grade foundation."
}
```

## Error Handling

### Common Extraction Issues

1. **Illegible text:**
   - Try multiple page images (sometimes data appears on multiple pages)
   - Report as low confidence
   - Provide best-effort extraction with disclaimer

2. **Conflicting values:**
   - Use schedule value if available (most authoritative)
   - Note conflict in extraction notes
   - Example: "CFA shows 800 sf on floor plan but 825 sf on area schedule. Using schedule value 825 sf."

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

- **Conditioned Floor Area:** Should match between floor plan area callouts and area schedule
- **Window Area:** Should match between window schedule total and calculated sum
- **Climate Zone:** Should be consistent across energy notes and title block
- **Fuel Type:** Should align with equipment schedules (gas furnace → Natural Gas or Mixed)

If cross-reference reveals discrepancy, prefer schedule value and note discrepancy.

## Next Steps After Extraction

The extracted JSON will be:
1. Saved to iteration directory
2. Passed to verifier agent for comparison against ground truth
3. Used to generate discrepancy reports
4. Fed back into self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all fields.

## Special Extraction Rules

### Bedroom Counting

For Title 24 compliance, count bedrooms as follows:
- **Studio / 0-bedroom units:** Count as **1 bedroom** for energy calculations
  - ADUs with "Living/Sleeping" or combined spaces count as 1 bedroom
  - This matches CBECC's treatment of studio units
- **Rooms labeled "Office" or "Den":** Do NOT count as bedrooms
- **Rooms with closets that could be bedrooms:** Count if they have egress windows

### Front Orientation Calculation

The front_orientation is the azimuth angle (degrees clockwise from true north) that the front of the building faces.

**How to determine:**
1. Find the site plan with north arrow
2. Identify the building's front (usually faces the street or main entry)
3. Measure the angle from true north to the front direction
4. Example: If front faces NE at 73°, front_orientation = 73

**Common orientations:**
- 0° = North facing
- 45° = Northeast facing
- 90° = East facing
- 135° = Southeast facing
- 180° = South facing
- 270° = West facing

**If north arrow shows building is rotated:**
- The floor plan labels (N, E, S, W) are relative to the building
- You must calculate actual azimuth from north arrow

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
| bedrooms | integer | null | Bedroom count from floor plan. **Studio ADUs count as 1 bedroom** |
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
| underground_wall_area | float | **0** | Below-grade walls in sq ft. **USE 0 for slab-on-grade** |
| slab_floor_area | float | null | Slab-on-grade floor in sq ft |
| exposed_slab_floor_area | float | **0** | Perimeter slab exposure. **USE 0 if not specified** |
| below_grade_floor_area | float | **0** | Basement floor in sq ft. **USE 0 for slab-on-grade** |
| exposed_below_grade_floor_area | float | **0** | Basement perimeter. **USE 0 for slab-on-grade** |
| addition_conditioned_floor_area | float | **0** | Addition CFA. **USE 0 for new construction** |

### Non-Extractable Fields

The following fields CANNOT be extracted from architectural plans - they are CBECC software outputs, test results, or compliance calculations. Use the defaults shown:

**CBECC Metadata (software-generated):**
- `run_id` - Use `null` (CBECC software ID)
- `run_title` - Use the **project address** as the value
- `run_number` - Use `0` (CBECC iteration number)
- `run_scope` - Use `null` (CBECC scope classification)
- `standards_version` - Use `null` (Title 24 version from CBECC)
- `all_orientations` - Use `false` (CBECC rotation analysis flag)

**Test Results (require physical testing):**
- `infiltration_ach50` - Blower door test result
- `infiltration_cfm50` - Blower door test result

**Compliance Calculations (CBECC computes these):**
- `pv_credit_available` - Compliance calculation
- `pv_generation_max_credit` - Compliance calculation
- `credit_available_for_pv` - Compliance calculation
- `final_pv_credit` - Compliance calculation

**Software Classifications:**
- `zonal_control` - CBECC HVAC classification
- `quality_insulation_installation` - QII certification

### Default Values for Common Building Types

**Slab-on-grade new construction (most ADUs and single-story homes):**
- `underground_wall_area`: **0** (no basement walls)
- `below_grade_floor_area`: **0** (no basement)
- `exposed_below_grade_floor_area`: **0** (no basement)
- `addition_conditioned_floor_area`: **0** (new construction, not addition)
- `exposed_slab_floor_area`: **0** unless explicitly specified

**How to determine foundation type:**
- Look for "slab-on-grade", "SOG", or "concrete slab" in foundation notes
- If no basement shown on floor plan → slab-on-grade → use 0 for basement fields
- If unclear, check section drawings or foundation plan

### Critical Instructions

1. **Never omit an extractable field** - Include ALL extractable fields in your JSON output
2. **Use null for non-extractable fields** - The fields listed above should be `null`
3. **Use null for unknown values** - If an extractable field cannot be found, use `null` (not omission)
4. **Use 0 for zero values** - For basement/below-grade fields in slab-on-grade buildings, use `0` not `null`
5. **Use false for absent features** - For booleans like attached_garage, use `false` if no garage exists

### Where to Find Commonly Missed Fields

| Field | Primary Source | Secondary Source |
|-------|----------------|------------------|
| address | Title block | Cover page |
| city | Title block | Cover page |
| climate_zone | Energy notes | Title block |
| attached_garage | Floor plan | Title block notes |
| front_orientation | Site plan north arrow | Floor plan orientation |
| underground_wall_area | Usually 0 for slab-on-grade | Foundation notes |
| slab_floor_area | Floor plan area | Often = CFA for single-story |
| exposed_slab_floor_area | Foundation notes | Perimeter calculation |
| below_grade_floor_area | Usually 0 for no basement | Foundation notes |
| addition_conditioned_floor_area | Usually 0 for new construction | Project scope notes |
