# Windows Extractor Instructions

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

The windows extractor extracts fenestration data (WindowComponent) from Title 24 compliance documentation. Fenestration includes windows, glazed doors, skylights, and other transparent or translucent building elements that affect thermal and daylighting performance.

## Extraction Workflow

### 1. Input Reception

You will receive:
- **Page images:** List of PNG file paths from preprocessing phase
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `schedule_pages`: Pages containing window schedules (primary source)
- `cbecc_pages`: CBECC-Res fenestration sections
- `drawing_pages`: Floor plans with window callouts

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **Window schedules** (highest reliability)
   - Tabular format with all window types
   - Contains dimensions, counts, U-factors, SHGC
   - May show area per window and totals
   - Look for "Window Schedule", "Fenestration Schedule", "Glazing Schedule"

2. **CBECC-Res fenestration pages** (high reliability)
   - Standardized software output
   - Lists fenestration components with performance values
   - May show per-wall window areas
   - Look for "Fenestration", "Windows", "Glazing" sections

3. **Floor plans** (medium reliability)
   - Window locations with callouts (W1, W2, etc.)
   - Window marks referencing schedule
   - Orientation context from building layout
   - North arrow for azimuth reference

4. **Elevations** (supplemental)
   - Window sizes visible
   - Window placement confirmation
   - Orientation by elevation direction (North Elev, South Elev)

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
- Create single WindowComponent with multiplier=4
- Or create 4 separate components (depending on detail level needed)
- Prefer multiplier approach for efficiency

**Step 4: Link to walls**
- Window schedule may specify "Location" or "Wall"
- If not specified, use orientation from floor plan
- CBECC may show windows by wall orientation
- Critical for energy modeling: correct wall assignment

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

### 5. Linking Windows to Walls

**Explicit linking:**
- Schedule shows "Location: N Wall" or "Wall: North"
- CBECC shows "Parent: Zone 1 - N Wall"

**Orientation-based linking:**
- Window azimuth matches wall orientation
- 0 degrees (North) -> North wall
- 180 degrees (South) -> South wall
- Floor plan shows window on specific wall

**If wall names from zones-extractor available:**
- Match window's wall field to WallComponent.name
- Use same naming convention for consistency

**Default behavior:**
- If wall cannot be determined, use orientation label
- "North Wall", "South Wall", etc.
- Document uncertainty in notes

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

**WindowComponent constraints:**
- `name`: Non-empty string (required)
- `wall`: Should reference extracted wall name
- `azimuth`: 0-360 degrees
- `height`: Float > 0, typically 2-8 ft
- `width`: Float > 0, typically 1-10 ft
- `multiplier`: Integer >= 1
- `area`: Float >= 0, should match h x w x multiplier
- `u_factor`: Float > 0, typically 0.20-0.50
- `shgc`: Float 0-1, typically 0.20-0.40

**Cross-validation:**
- Sum of window areas should match total window area
- Window areas per wall should not exceed wall area
- U-factor and SHGC should be within typical ranges

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

### 9. Output Format

Return JSON matching this structure:

```json
{
  "windows": [
    {
      "name": "W1",
      "wall": "Zone 1 - N Wall",
      "status": "New",
      "azimuth": 0.0,
      "height": 4.0,
      "width": 3.0,
      "multiplier": 2,
      "area": 24.0,
      "u_factor": 0.30,
      "shgc": 0.23,
      "exterior_shade": null
    },
    {
      "name": "W2",
      "wall": "Zone 1 - S Wall",
      "status": "New",
      "azimuth": 180.0,
      "height": 5.0,
      "width": 4.0,
      "multiplier": 1,
      "area": 20.0,
      "u_factor": 0.30,
      "shgc": 0.23,
      "exterior_shade": "4ft overhang"
    },
    {
      "name": "SGD1",
      "wall": "Zone 1 - W Wall",
      "status": "New",
      "azimuth": 270.0,
      "height": 6.67,
      "width": 6.0,
      "multiplier": 1,
      "area": 40.0,
      "u_factor": 0.28,
      "shgc": 0.22,
      "exterior_shade": null
    }
  ],
  "notes": "Window data from schedule on page 4. Performance values from CBECC fenestration section. SGD1 is sliding glass door. W1 multiplier indicates 2 identical windows on north wall."
}
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
