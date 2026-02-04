# Project Extractor Field Guide

**Version:** v1.1.0
**Last updated:** 2026-02-04

## Overview

This guide maps each ProjectInfo and EnvelopeInfo schema field to its source location in Title 24 compliance documents. Use this as a reference during extraction to know where to look for each field.

---

## ProjectInfo Fields

### run_title
**Type:** string (required)
**Description:** Project title / run identifier

**NOTE:** This is a CBECC software field. Without CBECC forms, use the project address as run_title.

**Document sources:**
1. **Title block:** Project name or address
2. **Cover page:** Project title

**Extraction tips:**
- Use the street address (e.g., "123 Main Street ADU") as the run_title
- This field is excluded from evaluation since CBECC will not be available

**Example values:**
- "123 Main Street ADU"
- "456 Oak Avenue"
- "789 Elm Court"

---

### address
**Type:** string (required)
**Description:** Street address of the building

**Document sources:**
1. **Cover page / Title block:** Address field (PRIMARY SOURCE)
2. **Drawing title blocks:** Below project name
3. **Site plan:** Property address annotation

**Extraction tips:**
- Include street number and name only (not city/state/zip)
- May be split across multiple lines in title block
- Watch for "Site Address" vs "Owner Address" - use site address

**Example values:**
- "123 Main Street"
- "456 Oak Avenue Unit B"
- "789 Elm Court"

---

### city
**Type:** string (required)
**Description:** City name

**Document sources:**
1. **Cover page / Title block:** Usually with address (PRIMARY SOURCE)
2. **Jurisdiction field:** Sometimes shown as "City of [Name]"
3. **Site plan:** Property location

**Extraction tips:**
- Extract city name only, no state or zip
- May appear as "City of Berkeley" - extract "Berkeley"
- Consistent across all document pages

**Example values:**
- "Berkeley"
- "Oakland"
- "San Francisco"

---

### climate_zone
**Type:** integer 1-16 (required)
**Description:** California climate zone

**Document sources:**
1. **Energy notes / Title block:** Climate zone often noted (PRIMARY SOURCE)
2. **Cover page:** May show "Climate Zone: XX" or "CZ XX"
3. **General notes:** Energy compliance notes often include climate zone

**Extraction tips:**
- Always shown as number 1-16 (California standard)
- Often abbreviated "CZ 12" or "Climate Zone 12"
- Extract numeric value only
- Should be consistent across all pages that show it
- Cannot infer from city (cities can span multiple zones)

**Example values:**
- 3 (Coastal Bay Area)
- 12 (Inland valleys)
- 16 (Mountain regions)

**Common zones by region:**
- San Francisco/Oakland: 3
- Berkeley/Alameda: 3
- Sacramento: 12
- San Jose: 4

---

### fuel_type
**Type:** enum ["All Electric", "Natural Gas", "Mixed"] (required)
**Description:** Primary fuel type for building systems

**Document sources:**
1. **Equipment schedules:** Check HVAC and water heater fuel sources (PRIMARY SOURCE)
2. **Mechanical schedules:** Heating and cooling equipment specifications
3. **Energy notes:** May explicitly state fuel type
4. **Plumbing plans:** Water heater type indicates fuel

**Extraction tips:**
- "All Electric": No gas service, all equipment is electric
- "Natural Gas": Gas furnace, gas water heater, or gas appliances present
- "Mixed": Both electric and gas equipment (e.g., gas furnace + electric AC)
- Infer from equipment if not explicitly stated:
  - "Heat pump" or "Electric resistance" → likely All Electric
  - "Gas furnace" or "Gas water heater" → Natural Gas or Mixed
- Title 24 increasingly requires all-electric for new ADUs

**Example interpretations:**
- Heat pump HVAC + electric water heater → "All Electric"
- Gas furnace + electric AC + gas water heater → "Mixed"
- Gas furnace + gas water heater, no AC → "Natural Gas"

---

### house_type
**Type:** enum ["Single Family", "Multi Family"] (required)
**Description:** Building type classification

**Document sources:**
1. **Cover page / Title block:** Project description (PRIMARY SOURCE)
2. **Project description:** May state "single family dwelling" or "ADU"
3. **General notes:** Building classification

**Extraction tips:**
- ADUs are typically "Single Family" (each unit is separate dwelling)
- "Multi Family" is for apartment buildings, duplexes, condos
- When in doubt for ADU projects, use "Single Family"

**Example values:**
- "Single Family" (most ADU projects)
- "Multi Family" (apartment buildings)

---

### dwelling_units
**Type:** integer >= 1 (required)
**Description:** Number of dwelling units in building

**Document sources:**
1. **Cover page / Title block:** Project description (PRIMARY SOURCE)
2. **Floor plans:** Count separate units
3. **Project description:** May state "1 DU" or "single unit"

**Extraction tips:**
- ADU projects are typically 1 unit
- Count separate units with their own kitchens/bathrooms
- Should match floor plan layout
- Typically 1 for single-family, > 1 for multi-family

**Example values:**
- 1 (typical for ADU)
- 2 (duplex)
- 4 (fourplex)

---

### stories
**Type:** integer >= 1 (required)
**Description:** Number of stories/floors

**Document sources:**
1. **Elevation drawings:** Count floors visible in elevation (PRIMARY SOURCE)
2. **Floor plans:** Multiple plan sheets indicate multiple stories
3. **Section drawings:** Clearly show story count
4. **Cover page:** Project description may state story count

**Extraction tips:**
- Count above-grade stories only (not basement unless finished)
- Look for "1 story", "2 story", "1.5 story" (with loft/attic)
- Cross-reference elevation drawing with CBECC value
- Partial second story (loft) may count as 1 or 2 stories depending on jurisdiction

**Example values:**
- 1 (single story)
- 2 (two story)

---

### bedrooms
**Type:** integer >= 0 (required)
**Description:** Number of bedrooms

**Document sources:**
1. **Floor plans:** Count rooms labeled "Bedroom", "BR", "BD" (PRIMARY SOURCE)
2. **Room schedule:** May list bedrooms
3. **Cover page:** Project description may state bedroom count

**Extraction tips:**
- Count only designated bedrooms (not dens, offices, or flex spaces)
- Cross-reference floor plan count with CBECC/CF1R value
- Studios may have 0 bedrooms (use 0, not null)
- Look for room labels: "Bedroom 1", "Master Bedroom", "BR"

**Example values:**
- 0 (studio)
- 1 (one-bedroom)
- 2 (two-bedroom)

---

## EnvelopeInfo Fields

### conditioned_floor_area
**Type:** float > 0 (required)
**Description:** Conditioned floor area in square feet (heated/cooled space)

**Document sources:**
1. **Floor plans:** Area calculations, dimension annotations (PRIMARY SOURCE)
2. **Area schedule:** Building area table
3. **Cover page / Title block:** May state total area
4. **Energy notes:** May show conditioned floor area

**Extraction tips:**
- Labeled "CFA", "Conditioned Floor Area", "Heated Floor Area", or just "Area"
- Units should be square feet (sf or ft²)
- Does NOT include garage, unconditioned porch, or attic
- Typical ADU range: 400-1200 sf

**Example values:**
- 800.0 sf
- 1200.0 sf
- 650.5 sf

**Cross-reference check:**
- Compare stated area with calculated floor plan dimensions
- If discrepancy > 5%, note in confidence report

---

### window_area
**Type:** float >= 0 (required)
**Description:** Total window area in square feet

**Document sources:**
1. **Window schedule:** Total area at bottom of schedule (PRIMARY SOURCE)
2. **Door and window schedule:** Combined table with totals
3. **Floor plans:** Window callouts with sizes
4. **Elevations:** Window dimensions visible

**Extraction tips:**
- Look for "Total Glazing Area", "Total Window Area", "Fenestration Area"
- Units: square feet (sf or ft²)
- Sum of all windows and glazed doors
- May need to calculate from individual window areas if no total

**Example values:**
- 120.0 sf
- 180.5 sf
- 95.0 sf

**Calculation if needed:**
- Sum areas from window schedule: Window A (20 sf) + Window B (30 sf) + ... = Total

---

### window_to_floor_ratio
**Type:** float 0.0-1.0 (required)
**Description:** Window-to-wall ratio or window-to-floor ratio (WWR/WFR)

**Document sources:**
1. **Calculated:** window_area / conditioned_floor_area (PRIMARY METHOD)
2. **Energy notes:** May show WWR or glazing percentage

**Extraction tips:**
- Labeled "WWR", "Window-to-Floor Ratio", "Glazing Ratio"
- Should be decimal 0.0-1.0 (15% = 0.15)
- Typical residential range: 0.12-0.25 (12%-25%)
- Usually calculated: window_area / conditioned_floor_area

**Example values:**
- 0.15 (15% glazing, common for energy efficient)
- 0.20 (20% glazing, typical residential)
- 0.10 (10% glazing, minimal windows)

**Calculation fallback:**
```
window_to_floor_ratio = window_area / conditioned_floor_area
Example: 120 sf / 800 sf = 0.15
```

---

### exterior_wall_area
**Type:** float >= 0 (required)
**Description:** Total exterior wall area in square feet

**Document sources:**
1. **Wall schedule:** Total exterior wall area (PRIMARY SOURCE)
2. **Calculated:** Perimeter x wall height from floor plans and sections
3. **Envelope assembly table:** Wall type areas summed

**Extraction tips:**
- Look for "Exterior Wall Area", "Above-Grade Wall Area"
- Units: square feet (sf or ft²)
- Excludes interior walls and foundation walls (below grade)
- May be shown by wall type (north wall, south wall, etc.) - sum them
- Can calculate from perimeter dimensions x ceiling height

**Example values:**
- 1200.0 sf
- 1800.0 sf
- 950.5 sf

**Calculation if needed:**
- Sum wall areas by orientation: North (300) + South (300) + East (250) + West (350) = 1200 sf

---

### fenestration_u_factor
**Type:** float > 0 or null (optional)
**Description:** Area-weighted average U-factor for all fenestration

**Document sources:**
1. **Window schedule:** U-factor column, area-weighted average at bottom (PRIMARY SOURCE)
2. **Product specifications:** Window manufacturer U-factor ratings
3. **Energy notes:** May show required or specified U-factor

**Extraction tips:**
- Labeled "U-Factor", "U-Value", "Overall U-Factor"
- Units: Btu/(hr·ft²·°F) - typically 0.20-0.45 for modern windows
- May be shown per window, need area-weighted average
- Can be null/missing if not specified
- Title 24 2022 prescriptive max: U-0.30 for most zones

**Example values:**
- 0.28 (good performance, common for Title 24 compliance)
- 0.32 (moderate performance)
- 0.25 (high performance, triple pane)
- null (if not specified in documents)

**Area-weighted calculation if needed:**
```
Sum of (window_area_i × u_factor_i) / total_window_area

Example:
Window A: 30 sf × 0.30 = 9.0
Window B: 40 sf × 0.25 = 10.0
Window C: 50 sf × 0.28 = 14.0
Total: 120 sf
Average U-Factor = (9.0 + 10.0 + 14.0) / 120 = 0.275
```

---

### front_orientation
**Type:** float 0-360 (optional)
**Description:** Front wall azimuth in degrees from true north

**Document sources:**
1. **Site plan:** North arrow with building orientation (PRIMARY SOURCE)
2. **Floor plan:** North arrow and building layout
3. **Elevations:** Direction labels (North Elev, South Elev) help confirm

**Extraction tips:**
- 0 = North, 90 = East, 180 = South, 270 = West
- Calculate from north arrow angle and building/street orientation
- See orientation-extractor instructions for detailed calculation method

**Example values:**
- 0 (north-facing)
- 73 (NE-facing)
- 180 (south-facing)

---

### underground_wall_area
**Type:** float >= 0 (optional)
**Description:** Below-grade wall area in square feet

**Document sources:**
1. **Foundation plan:** Below-grade wall details
2. **Section drawings:** Show below-grade conditions

**Extraction tips:**
- For slab-on-grade construction (no basement): use 0
- Only includes walls below grade level
- Common ADUs have 0 underground wall area

**Example values:**
- 0 (slab-on-grade, most ADUs)
- 200.0 (partial basement)

---

### slab_floor_area
**Type:** float >= 0 (optional)
**Description:** Slab-on-grade floor area in square feet

**Document sources:**
1. **Foundation plan:** Slab perimeter area (PRIMARY SOURCE)
2. **Floor plans:** Building footprint dimensions
3. **Section drawings:** Foundation type visible

**Extraction tips:**
- For homes entirely on slab: slab_floor_area ≈ conditioned_floor_area
- May be null if foundation type unclear

---

### exposed_slab_floor_area
**Type:** float >= 0 (optional)
**Description:** Exposed slab perimeter area in square feet

**Document sources:**
1. **Foundation plan:** Slab edge details
2. **Foundation details:** Slab edge exposure

**Extraction tips:**
- Perimeter slab area exposed to exterior
- Often calculated as perimeter × slab thickness
- Use 0 if slab is entirely under building

**Example values:**
- 64.0 (160 ft perimeter × 0.4 ft thickness)
- 0 (no perimeter exposure)

---

### below_grade_floor_area, exposed_below_grade_floor_area
**Type:** float >= 0 (optional each)
**Description:** Below-grade floor areas

**Extraction tips:**
- For slab-on-grade buildings: use 0 for both
- Only non-zero if building has basement
- Common for ADUs: both = 0

---

### addition_conditioned_floor_area
**Type:** float >= 0 (optional)
**Description:** Conditioned floor area of addition (for alteration projects)

**Extraction tips:**
- For new construction: use 0
- Only non-zero for "Addition" or "Alteration" project scope
- If run_scope = "Newly Constructed", use 0

---

### pv_credit_available
**Type:** boolean (optional)
**Description:** Whether PV credit is available for compliance

**Document sources:**
1. **Site plan:** PV panel layout if present
2. **Electrical plans:** Solar system specifications
3. **Energy notes:** Solar/PV requirements

**Extraction tips:**
- true if building has or plans for solar PV
- May show as checkbox or Y/N
- NOTE: This is often a compliance calculation field - use null if not shown

---

### pv_generation_max_credit, credit_available_for_pv, final_pv_credit
**Type:** float >= 0 (optional each)
**Description:** PV-related compliance credits

**Extraction tips:**
- These may all be 0 for projects without solar
- Use 0 (not null) if project has no PV but field is shown
- Use null only if PV section is entirely absent

---

### zonal_control
**Type:** boolean (optional)
**Description:** Whether HVAC uses zonal control

**Document sources:**
1. **Mechanical plans:** HVAC zone layout
2. **Equipment schedule:** Zone control equipment

**Extraction tips:**
- true if multiple thermostats/zones
- false for single-zone systems (typical ADU)
- NOTE: This is often a CBECC classification field - use null if not shown

---

### infiltration_ach50
**Type:** float > 0 (optional)
**Description:** Air changes per hour at 50 Pa (blower door test)

**Document sources:**
1. **Energy notes:** Air tightness requirements
2. **Testing results:** Blower door test (post-construction)

**Extraction tips:**
- Title 24 2022 requires ≤5 ACH50 for new construction
- Common values: 3-5 ACH50
- NOTE: This is a test result field - use null unless test results provided

---

### infiltration_cfm50
**Type:** float > 0 (optional)
**Description:** CFM at 50 Pa blower door pressure

**Extraction tips:**
- Calculated from ACH50 × Volume / 60
- NOTE: This is a test result field - use null unless test results provided

---

### quality_insulation_installation
**Type:** boolean (optional)
**Description:** QII certification status

**Document sources:**
1. **Energy notes:** QII certification requirements
2. **Specifications:** Insulation installation standards

**Extraction tips:**
- true if QII certified
- false if standard installation (most projects)
- NOTE: This is a certification field - use null if not specified

---

## Extraction Best Practices

### Page Reading Order
1. Start with Cover page / Title block (project info, address, climate zone)
2. Check Schedule pages (window, equipment, wall schedules for technical data)
3. Use Floor plans for room counts, areas, layout
4. Reference Elevations/Sections for story count, wall heights

### Common Document Layouts

**Cover Page / Title Block:**
- Project name, address, city
- Climate zone (often in energy notes)
- Project description (ADU, single-family, etc.)
- Architect/engineer information

**Floor Plan:**
- Room labels with names (Bedroom, Living Room, etc.)
- Area callouts or dimensions for calculating area
- Window and door marks referencing schedules
- North arrow for orientation

**Window Schedule:**
- Columns: Mark, Quantity, Width, Height, Area, U-Factor, SHGC
- Bottom row: Totals

**Floor Plan:**
- Title block: Project name, address, sheet title
- Rooms labeled with names (Bedroom, Living Room, etc.)
- Dimensions for area calculation

### Quality Checks

Before finalizing extraction:
- [ ] All required fields populated (no nulls except fenestration_u_factor)
- [ ] Climate zone in range 1-16
- [ ] Window-to-floor ratio < 1.0 and reasonable (typically 0.10-0.30)
- [ ] Conditioned floor area matches rough floor plan dimensions
- [ ] Bedroom count matches floor plan room labels
- [ ] Story count matches elevation drawing
- [ ] Fuel type matches equipment schedules
- [ ] All areas in square feet (check for unit conversions)

### Confidence Scoring

Document extraction confidence in notes:

**High confidence indicators:**
- Value from schedule or title block, clearly legible
- Cross-referenced across multiple pages with agreement
- Standard format with clear units

**Medium confidence indicators:**
- Value from floor plan annotation
- Legible but some interpretation needed
- Calculated from other fields (e.g., WWR from window_area / CFA)

**Low confidence indicators:**
- Hand-written value, OCR uncertain
- Ambiguous labels or units
- Conflict between pages, used best judgment
- Counted from floor plan (bedrooms, stories)

Include specific notes for low-confidence fields so verifier can double-check.

---

## Field Summary Table

| Field | Type | Sources | Default if Missing |
|-------|------|---------|-------------------|
| run_id | string | (CBECC only) | null |
| run_title | string | Use project address | address value |
| address | string | Cover, title block | - |
| city | string | Cover, title block | - |
| climate_zone | int 1-16 | Energy notes, cover | - |
| fuel_type | enum | Equipment schedules | - |
| house_type | enum | Cover, project description | - |
| dwelling_units | int ≥1 | Cover, floor plans | 1 |
| stories | int ≥1 | Elevations, floor plans | - |
| bedrooms | int ≥0 | Floor plans | - |
| front_orientation | float 0-360 | Site plan, north arrow | null |
| conditioned_floor_area | float >0 | Floor plans, area schedule | - |
| window_area | float ≥0 | Window schedule | - |
| window_to_floor_ratio | float 0-1 | Calculate from above | - |
| exterior_wall_area | float ≥0 | Wall schedule, calculated | - |
| fenestration_u_factor | float >0 | Window schedule | null |
| underground_wall_area | float ≥0 | Foundation plan | 0 |
| slab_floor_area | float ≥0 | Foundation plan | null |
| exposed_slab_floor_area | float ≥0 | Foundation details | 0 |
| below_grade_floor_area | float ≥0 | Foundation plan | 0 |
| exposed_below_grade_floor_area | float ≥0 | Foundation plan | 0 |
| addition_conditioned_floor_area | float ≥0 | Project scope | 0 |
| pv_credit_available | boolean | (CBECC calculation) | null |
| pv_generation_max_credit | float ≥0 | (CBECC calculation) | null |
| credit_available_for_pv | float ≥0 | (CBECC calculation) | null |
| final_pv_credit | float ≥0 | (CBECC calculation) | null |
| zonal_control | boolean | (CBECC classification) | null |
| infiltration_ach50 | float >0 | (Test result) | null |
| infiltration_cfm50 | float >0 | (Test result) | null |
| quality_insulation_installation | boolean | (Certification) | null |

**Total fields:** 30 (ProjectInfo + EnvelopeInfo)

---

*End of Field Guide*
