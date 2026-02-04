# Windows Extractor Instructions

**Version:** v2.1.0
**Last updated:** 2026-02-04

## Core Rule

For each wall orientation, classify openings into two buckets (do not mix):
1. **Fenestration** (windows, sliders, glazed doors) → `house_walls.{orientation}.fenestration[]`
2. **Opaque exterior doors** → handled by zones-extractor

This extractor handles **Fenestration only**. Do NOT include opaque doors.

## Overview

The windows extractor extracts fenestration data **nested under parent wall orientations** from Title 24 compliance documentation. Fenestration includes windows, glazed doors (>50% glass), skylights, and other transparent/translucent building elements.

**Key principles:**
- Fenestration nested under `house_walls.{orientation}.fenestration[]` - matches CBECC structure
- Report per-opening: Tag/Mark, type, size (WxH), quantity, area
- Report orientation totals: TotalFenestrationArea per wall
- **MANDATORY FLAGS** for every uncertainty, assumption, or discrepancy

## Extraction Workflow

### 1. Input Reception

You will receive:
- **Page images:** List of PNG file paths from preprocessing phase
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `schedule_pages`: Pages containing window schedules (primary source)
- `drawing_pages`: Floor plans with window callouts, elevations
- `other`: Cover pages, notes, specifications

**NOTE:** CBECC-Res compliance forms are NOT typically included in architectural plan sets. The source documents are architectural PDFs (floor plans, schedules, title blocks). Do not expect to find CBECC pages.

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **Window schedules** (highest reliability)
   - Tabular format with all window types
   - Contains dimensions, counts, U-factors, SHGC
   - May show area per window and totals
   - Look for "Window Schedule", "Fenestration Schedule", "Glazing Schedule"

2. **Floor plans** (high reliability for location/orientation)
   - Window locations with callouts (W1, W2, etc.)
   - Window marks referencing schedule
   - Orientation context from building layout
   - North arrow for azimuth reference

3. **Elevations** (medium reliability)
   - Window sizes visible
   - Window placement confirmation
   - Orientation by elevation direction (North Elev, South Elev)

4. **Energy notes / Specifications** (supplemental)
   - U-factor and SHGC values
   - Product specifications
   - Compliance notes

### 3. Window Identification Strategy

**Step 1: Locate window schedule**
- Find "Window Schedule" or "Door & Window Schedule"
- Identify columns: Mark, Type, Size, Quantity, U-Factor, SHGC
- Note total row if present

**Step 2: Extract window types**
- Each row represents a window type
- Mark/ID column (W1, W2, A, B, etc.)
- Dimensions: Width x Height
- Quantity: How many of this type

**Step 3: Handle multipliers**
- Schedule may show "QTY: 4" meaning 4 identical windows
- Create single entry with multiplier=4
- Calculate AreaTotal = AreaPerUnit × multiplier

**Step 4: Handle schedule vs plan conflicts**
- If window/door schedule conflicts with plan callouts: **prefer the schedule dimensions**
- Add FLAG noting the discrepancy: "Schedule shows 3'x4', plan callout shows 3'x5'. Using schedule value."
- Schedule is typically more accurate for ordering/manufacturing

**Step 5: Link to walls**
- Window schedule may specify "Location" or "Wall"
- If not specified, use orientation from floor plan or CBECC parent
- Critical for energy modeling: correct wall assignment
- Add FLAG if wall assignment is uncertain

### 4. Performance Value Extraction

**U-Factor:**
- Thermal transmittance (lower is better)
- Title 24 typical: 0.25-0.35
- May be shown per window type or single value for all
- Look for "U-Factor", "U-Value", "Uw"

**SHGC (Solar Heat Gain Coefficient):**
- Solar energy transmittance (lower reduces heat gain)
- Title 24 typical: 0.22-0.25 for most zones
- May vary by orientation (south windows lower SHGC)
- Look for "SHGC", "Solar Heat Gain"

**Where to find:**
1. Window schedule columns
2. CBECC fenestration summary
3. Product specification notes
4. CF1R form fenestration section

### 5. Assigning Windows to Wall Orientations

**Step 1: Determine wall assignment from schedule or floor plan**
- Schedule may show "Location: N Wall" or "Wall: North"
- Floor plan shows window position on which exterior wall
- Match window to the wall it's physically located on

**Step 2: Calculate ACTUAL window azimuth for rotated buildings**
If the building has a front_orientation (e.g., 73° for NE-facing):
- Window azimuth = wall azimuth (from zones-extractor)
- **Do NOT use cardinal azimuths (0, 90, 180, 270) for rotated buildings**
- Example: Front = 73°
  - North wall windows → azimuth = 343° (73 - 90, wrapped)
  - East wall windows → azimuth = 73°
  - South wall windows → azimuth = 163° (73 + 90)
  - West wall windows → azimuth = 253° (73 + 180)

**Step 3: Place in correct orientation slot**
- Use cardinal direction as JSON key: `house_walls.{north|east|south|west}.fenestration[]`
- But set `azimuth` to the ACTUAL value (not cardinal)
- Example: Window on "North Wall" with building front at 73° →
  - Key: `house_walls.north.fenestration[]`
  - Azimuth: 343° (actual orientation)

**Step 4: Handle ambiguous assignments**
If orientation is unclear:
- Check floor plan for window locations relative to building perimeter
- Use elevation drawings to confirm wall orientation
- Add an uncertainty flag with severity "medium"

**Important:** The orchestrator merges fenestration into walls from zones-extractor. Your output should only include `house_walls.{orientation}.fenestration[]` arrays.

### 6. Naming Conventions

**Window names:**
- Use schedule mark: "W1", "W2", "Window A"
- Add orientation if helpful: "W1-North"
- Keep consistent with schedule references

**Wall references:**
- Must match wall names from zones-extractor
- Use orientation-based names: "Zone 1 - N Wall"
- Or cardinal: "North Wall"

**Consistency requirement:**
- WindowComponent.wall must match WallComponent.name
- Use identical strings for schema assembly

### 7. Data Validation

Before returning extracted data, validate:

**FenestrationEntry constraints:**
- `name`: Non-empty string (required)
- `fenestration_type`: "Window", "Sliding Glass Door", "French Door", etc.
- `height`: Float > 0, typically 2-8 ft
- `width`: Float > 0, typically 1-10 ft
- `multiplier`: Integer >= 1 (default 1)
- `area`: Float >= 0, should match h x w x multiplier
- `u_factor`: Float > 0, typically 0.20-0.50
- `shgc`: Float 0-1, typically 0.20-0.40
- `overhang_depth`: Float >= 0 if overhang exists

**Cross-validation:**
- Sum of fenestration areas per orientation should be reasonable for wall size
- U-factor and SHGC should be within Title 24 typical ranges
- All windows on same wall should have consistent performance values (usually same product)

**MANDATORY uncertainty flags:**
- Add FLAG if orientation assignment is uncertain
- Add FLAG if performance values are from defaults rather than spec
- Add FLAG if multiplier was inferred rather than explicitly stated
- Add FLAG if schedule conflicts with plan callouts (note which you used)
- Add FLAG for every assumption or uncertainty
- Every FLAG should describe: what is uncertain, where to verify (sheet/detail)

### 8. Handling Missing Data

**Required fields:**
- `name`: If missing, construct from position: "Window 1"

**Optional fields (can be null):**
- Performance values may not be specified
- Dimensions may need calculation from area
- Wall assignment may need inference

**Inference when allowed:**
- Area can be calculated: height x width x multiplier
- Azimuth from wall orientation
- Status from project scope

### 9. Output Format (TakeoffSpec)

Return JSON with fenestration **nested under wall orientations**:

```json
{
  "house_walls": {
    "north": {
      "fenestration": [
        {
          "name": "W1",
          "fenestration_type": "Window",
          "status": "New",
          "height": 4.0,
          "width": 3.0,
          "multiplier": 2,
          "area": 24.0,
          "u_factor": 0.30,
          "shgc": 0.23,
          "exterior_shade": null,
          "overhang_depth": null
        }
      ]
    },
    "east": {
      "fenestration": []
    },
    "south": {
      "fenestration": [
        {
          "name": "W2",
          "fenestration_type": "Window",
          "status": "New",
          "height": 5.0,
          "width": 4.0,
          "multiplier": 1,
          "area": 20.0,
          "u_factor": 0.30,
          "shgc": 0.23,
          "exterior_shade": "4ft overhang",
          "overhang_depth": 4.0
        }
      ]
    },
    "west": {
      "fenestration": [
        {
          "name": "SGD1",
          "fenestration_type": "Sliding Glass Door",
          "status": "New",
          "height": 6.67,
          "width": 6.0,
          "multiplier": 1,
          "area": 40.0,
          "u_factor": 0.28,
          "shgc": 0.22,
          "exterior_shade": null,
          "overhang_depth": null
        }
      ]
    }
  },
  "flags": [
    {
      "field_path": "house_walls.north.fenestration[0].u_factor",
      "severity": "medium",
      "reason": "U-factor from CBECC summary, not per-window specification",
      "source_page": 3
    }
  ],
  "notes": "Window data from schedule on page 4. Performance values from CBECC fenestration section. SGD1 is sliding glass door. W1 multiplier indicates 2 identical windows on north wall."
}
```

**Important:** Only include the `fenestration` array under each orientation. The zones-extractor populates wall geometry (gross_wall_area, azimuth, etc.). The orchestrator merges both outputs.
```

## Error Handling

### Common Extraction Issues

1. **Schedule vs CBECC mismatch:**
   - Window counts or areas may differ
   - Use schedule for individual window details
   - Use CBECC for totals and verification
   - Note discrepancy in extraction notes

2. **Missing performance values:**
   - Schedule may only show dimensions
   - Check CBECC for U-factor and SHGC
   - May need to use prescriptive defaults:
     - U-factor: 0.30 (Title 24 prescriptive)
     - SHGC: 0.23 (coastal zones), 0.25 (inland)

3. **Glazed doors confusion:**
   - Sliding glass doors count as windows for energy
   - French doors with glazing included
   - May be on door schedule or window schedule
   - Include if substantial glazing (>50% glass)

4. **Multiple window configurations:**
   - Same window type in different locations
   - May need separate entries per wall/orientation
   - Or single entry with multiplier

### Orientation Handling

**Azimuth values:**
- 0 = North (least solar gain in northern hemisphere)
- 90 = East (morning sun)
- 180 = South (maximum solar gain)
- 270 = West (afternoon sun)

**If front orientation specified:**
- CBECC may show orientations relative to front
- Add front orientation offset to get true azimuth
- Example: Front = 45 degrees (NE), "Front Wall" window azimuth = 45

**Cardinal direction conversion:**
- Same as wall orientation conversion
- N=0, NE=45, E=90, SE=135, S=180, SW=225, W=270, NW=315

## Cross-Referencing Strategy

To improve accuracy:

1. **Window area totals:**
   - Sum of individual window areas should match schedule total
   - Should match zone window area from zones-extractor
   - Should match EnvelopeInfo.window_area

2. **Window counts:**
   - Count from schedule should match floor plan
   - Multipliers should account for all instances

3. **Performance consistency:**
   - All windows same manufacturer often have same U-factor/SHGC
   - Different values may indicate different products
   - Verify against CBECC fenestration summary

4. **Wall area check:**
   - Total window area per wall should not exceed wall area
   - Typical residential: 10-30% of wall area is glazing

## Confidence Reporting

Include extraction notes with confidence levels:

**High confidence:**
- Complete window schedule with all columns
- CBECC fenestration section matches
- Clear marks and dimensions

**Medium confidence:**
- Missing performance values (used defaults)
- Wall assignment inferred from orientation
- Calculated area from dimensions

**Low confidence:**
- Window counts from floor plan only
- Performance values from general notes
- Ambiguous wall assignments

Example notes:
```
"3 window types from schedule (high confidence). U-factor 0.30 and SHGC 0.23 from CBECC for all windows (high confidence). Wall assignments inferred from floor plan orientation (medium confidence). SGD1 sliding glass door area calculated from 6'x6'8\" dims (medium confidence)."
```

## Glazed Door Handling

Include glazed doors that function as fenestration:

**Include:**
- Sliding glass doors (SGD)
- French doors with substantial glazing
- Entry doors with large glass panels
- Storefront glazing

**Exclude:**
- Solid doors with small vision panels
- Doors with <50% glazing
- Garage doors (unless mostly glass)

**Naming:**
- Use door schedule mark: "D1", "SGD1"
- Or descriptive: "Sliding Glass Door"
- Note in extraction notes that it's a door

## Next Steps After Extraction

The extracted JSON will be:
1. Merged with project, envelope, zones, and walls data
2. Windows linked to walls for complete model
3. Assembled into complete BuildingSpec
4. Passed to verifier for comparison against ground truth
5. Used in self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all window fields.
