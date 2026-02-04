# Project Extractor Field Guide

**Version:** v1.1.0
**Last updated:** 2026-02-04

## Overview

This guide maps each ProjectInfo and EnvelopeInfo schema field to its source location in Title 24 compliance documents. Use this as a reference during extraction to know where to look for each field.

---

## ProjectInfo Fields

### run_title
**Type:** string (required)
**Description:** CBECC analysis run title (NOT the project name or address)

**CRITICAL DISTINCTION:**
- `run_title` = The analysis run title in CBECC software
- This is NOT the project name, address, or owner name
- If CBECC shows "Title 24 Analysis" as the run title, use that exact string

**Document sources:**
1. **CBECC-Res output:** Look for "Run Title:", "Analysis Title:", or header label (PRIMARY SOURCE)
2. **CF1R form:** May show run identifier
3. **NOT from:** Title block project name, address, or owner name

**Extraction tips:**
- Look specifically for CBECC analysis naming, not project identification
- Common values: "Title 24 Analysis", "Compliance Analysis", "Energy Analysis"
- If not explicitly found, check CBECC header for analysis identifier
- Do NOT substitute project address or building name

**Example values:**
- "Title 24 Analysis" (common default)
- "Compliance Run 1"
- "Energy Analysis"
- "T24 Analysis"

**Common mistakes to avoid:**
- Using address ("4720 Chamberlin Cir") as run_title - WRONG
- Using project name ("Smith ADU") as run_title - WRONG
- Using owner name - WRONG

---

### address
**Type:** string (required)
**Description:** Street address of the building

**Document sources:**
1. **Cover page:** Title block address field
2. **CBECC-Res output:** Project location section
3. **CF1R form:** "Project Address" or "Site Address" field
4. **Drawing title blocks:** Below project name

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
1. **Cover page:** Title block, usually with address
2. **CBECC-Res output:** Project location section
3. **CF1R form:** Address section
4. **Jurisdiction field:** Sometimes shown as "City of [Name]"

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
1. **CBECC-Res output:** Usually prominent near top, labeled "Climate Zone" or "CZ"
2. **CF1R form:** Header section, "Climate Zone: XX"
3. **Weather data section:** May reference "CZ 12" or similar

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
1. **CBECC-Res output:** May explicitly state "Fuel Type: All Electric"
2. **Equipment schedules:** Check HVAC and water heater fuel sources
3. **Mechanical schedules:** Heating and cooling equipment specifications
4. **Energy budget section:** May categorize by fuel type

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
1. **CBECC-Res output:** "Building Type" or "Dwelling Type" field
2. **CF1R form:** Building classification section
3. **Project description:** May state "single family dwelling" or "ADU"

**Extraction tips:**
- ADUs are typically "Single Family" (each unit is separate dwelling)
- "Multi Family" is for apartment buildings, duplexes, condos
- Look for explicit classification on CBECC or CF1R
- When in doubt for ADU projects, use "Single Family"

**Example values:**
- "Single Family" (most ADU projects)
- "Multi Family" (apartment buildings)

---

### dwelling_units
**Type:** integer >= 1 (required)
**Description:** Number of dwelling units in building

**Document sources:**
1. **CBECC-Res output:** "Number of Dwelling Units" field
2. **CF1R form:** Building description section
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
1. **CBECC-Res output:** "Number of Stories" field
2. **CF1R form:** Building description
3. **Elevation drawings:** Count floors visible in elevation
4. **Floor plans:** Multiple plan sheets indicate multiple stories

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
1. **CBECC-Res output:** "Number of Bedrooms" field
2. **CF1R form:** Building description
3. **Floor plans:** Count rooms labeled "Bedroom", "BR", "BD"
4. **Room schedule:** May list bedrooms

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
1. **CBECC-Res output:** "Conditioned Floor Area" or "CFA", prominently displayed
2. **CF1R form:** Envelope summary section
3. **Floor plans:** Area calculations, dimension annotations
4. **Area schedule:** Building area table

**Extraction tips:**
- Labeled "CFA", "Conditioned Floor Area", "Heated Floor Area"
- Units should be square feet (sf or ft²)
- Does NOT include garage, unconditioned porch, or attic
- CBECC value is most authoritative (calculated by software)
- Typical ADU range: 400-1200 sf

**Example values:**
- 800.0 sf
- 1200.0 sf
- 650.5 sf

**Cross-reference check:**
- Compare CBECC value with floor plan dimensions
- If discrepancy > 5%, note in confidence report

---

### window_area
**Type:** float >= 0 (required)
**Description:** Total window area in square feet

**Document sources:**
1. **Window schedule:** Total area at bottom of schedule
2. **CBECC-Res output:** Fenestration summary section
3. **CF1R form:** Window/glazing area field
4. **Door and window schedule:** Combined table with totals

**Extraction tips:**
- Look for "Total Glazing Area", "Total Window Area", "Fenestration Area"
- Units: square feet (sf or ft²)
- Sum of all windows and glazed doors
- May need to calculate from individual window areas if no total
- CBECC fenestration summary is most reliable

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
1. **CBECC-Res output:** "WWR" or "Window-to-Floor Ratio"
2. **CF1R form:** Fenestration percentage field
3. **Energy compliance summary:** Glazing percentage

**Extraction tips:**
- Labeled "WWR", "Window-to-Floor Ratio", "Glazing Ratio"
- Should be decimal 0.0-1.0 (15% = 0.15)
- Typical residential range: 0.12-0.25 (12%-25%)
- Can calculate if missing: window_area / conditioned_floor_area
- CBECC value preferred over manual calculation

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
1. **Wall schedule:** Total exterior wall area
2. **CBECC-Res output:** Envelope summary, "Exterior Wall Area"
3. **CF1R form:** Wall area field
4. **Envelope assembly table:** Wall type areas summed

**Extraction tips:**
- Look for "Exterior Wall Area", "Above-Grade Wall Area"
- Units: square feet (sf or ft²)
- Excludes interior walls and foundation walls (below grade)
- May be shown by wall type (north wall, south wall, etc.) - sum them
- CBECC envelope summary most reliable

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
1. **Window schedule:** U-factor column, area-weighted average at bottom
2. **CBECC-Res output:** Fenestration summary, "Average U-Factor"
3. **CF1R form:** Window performance section
4. **Product specifications:** Window manufacturer U-factor ratings

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
1. **CBECC-Res output:** "Front:" or "Front Orientation:" field
2. **Site plan:** North arrow with building orientation
3. **CF1R form:** Orientation field

**Extraction tips:**
- 0 = North, 90 = East, 180 = South, 270 = West
- CBECC shows this prominently for multi-orientation analysis
- May show "Front: 73°" meaning NE-facing

**Example values:**
- 0 (north-facing)
- 73 (NE-facing)
- 180 (south-facing)

---

### underground_wall_area
**Type:** float >= 0 (optional)
**Description:** Below-grade wall area in square feet

**Document sources:**
1. **CBECC-Res output:** Envelope summary, "Underground Wall Area"
2. **CF1R form:** Wall area section

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
1. **CBECC-Res output:** Envelope summary
2. **Foundation plan:** Slab perimeter area

**Extraction tips:**
- For homes entirely on slab: slab_floor_area ≈ conditioned_floor_area
- May be null if foundation type unclear

---

### exposed_slab_floor_area
**Type:** float >= 0 (optional)
**Description:** Exposed slab perimeter area in square feet

**Document sources:**
1. **CBECC-Res output:** "Exposed Slab" section
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
1. **CBECC-Res output:** Compliance summary, PV section
2. **CF1R form:** Solar/PV section

**Extraction tips:**
- true if building has or plans for solar PV
- May show as checkbox or Y/N

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
1. **CBECC-Res output:** HVAC section
2. **Mechanical schedule:** Zone control equipment

**Extraction tips:**
- true if multiple thermostats/zones
- false for single-zone systems (typical ADU)

---

### infiltration_ach50
**Type:** float > 0 (optional)
**Description:** Air changes per hour at 50 Pa (blower door test)

**Document sources:**
1. **CBECC-Res output:** Infiltration section
2. **CF1R form:** Air tightness

**Extraction tips:**
- Title 24 2022 requires ≤5 ACH50 for new construction
- Common values: 3-5 ACH50

---

### infiltration_cfm50
**Type:** float > 0 (optional)
**Description:** CFM at 50 Pa blower door pressure

**Extraction tips:**
- Calculated from ACH50 × Volume / 60
- May be shown directly in CBECC

---

### quality_insulation_installation
**Type:** boolean (optional)
**Description:** QII certification status

**Document sources:**
1. **CBECC-Res output:** QII checkbox
2. **CF1R form:** QII certification section

**Extraction tips:**
- true if QII certified
- false if standard installation (most projects)

---

## Extraction Best Practices

### Page Reading Order
1. Start with CBECC-Res pages (most standardized format)
2. Check CF1R forms for missing fields
3. Use schedules to fill remaining gaps
4. Reference drawings for counts (bedrooms, stories)

### Common Document Layouts

**CBECC-Res Output Page:**
- Header: Project name, address, climate zone
- Building Summary: Stories, bedrooms, dwelling units, fuel type
- Envelope Summary: CFA, wall area, window area, WWR
- Fenestration Details: U-factor, SHGC by window

**CF1R Form:**
- Top section: Project info, address, city, climate zone
- Middle section: Building type, area, stories
- Bottom section: Envelope compliance, U-factors

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
- Value from CBECC-Res or CF1R form
- Clearly legible, no ambiguity
- Cross-referenced across multiple pages with agreement

**Medium confidence indicators:**
- Value from schedule or drawing
- Legible but some interpretation needed
- Calculated from other fields

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
| run_id | string | CBECC header | null |
| run_title | string | CBECC "Run Title:" (NOT project name) | - |
| address | string | Cover, CBECC, CF1R | - |
| city | string | Cover, CBECC, CF1R | - |
| climate_zone | int 1-16 | CBECC, CF1R | - |
| fuel_type | enum | CBECC, equipment | - |
| house_type | enum | CBECC, CF1R | - |
| dwelling_units | int ≥1 | CBECC, CF1R | 1 |
| stories | int ≥1 | CBECC, elevations | - |
| bedrooms | int ≥0 | CBECC, floor plans | - |
| front_orientation | float 0-360 | CBECC "Front:" | null |
| conditioned_floor_area | float >0 | CBECC, CF1R | - |
| window_area | float ≥0 | Window schedule, CBECC | - |
| window_to_floor_ratio | float 0-1 | CBECC, calculate | - |
| exterior_wall_area | float ≥0 | Wall schedule, CBECC | - |
| fenestration_u_factor | float >0 | Window schedule, CBECC | null |
| underground_wall_area | float ≥0 | CBECC envelope | 0 |
| slab_floor_area | float ≥0 | CBECC envelope | null |
| exposed_slab_floor_area | float ≥0 | CBECC envelope | 0 |
| below_grade_floor_area | float ≥0 | CBECC envelope | 0 |
| exposed_below_grade_floor_area | float ≥0 | CBECC envelope | 0 |
| addition_conditioned_floor_area | float ≥0 | CBECC | 0 |
| pv_credit_available | boolean | CBECC compliance | null |
| pv_generation_max_credit | float ≥0 | CBECC PV section | null |
| credit_available_for_pv | float ≥0 | CBECC compliance | null |
| final_pv_credit | float ≥0 | CBECC compliance | null |
| zonal_control | boolean | CBECC HVAC | null |
| infiltration_ach50 | float >0 | CBECC infiltration | null |
| infiltration_cfm50 | float >0 | CBECC infiltration | null |
| quality_insulation_installation | boolean | CBECC, CF1R | null |

**Total fields:** 30 (ProjectInfo + EnvelopeInfo)

---

*End of Field Guide*
