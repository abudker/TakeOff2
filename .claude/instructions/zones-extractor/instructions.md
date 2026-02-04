# Zones Extractor Instructions

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

The zones extractor extracts thermal zone data (ZoneInfo) and wall components (WallComponent) from Title 24 compliance documentation. Zones define the conditioned spaces in a building, while walls are the exterior envelope components associated with each zone.

## Extraction Workflow

### 1. Input Reception

You will receive:
- **Page images:** List of PNG file paths from preprocessing phase
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `cbecc_pages`: CBECC-Res software output pages (primary source)
- `schedule_pages`: Pages containing building component schedules
- `drawing_pages`: Floor plans, elevations, sections

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **CBECC-Res pages** (highest reliability)
   - Zone summary tables with area, volume, wall area totals
   - Zone definition lists with type (conditioned/unconditioned)
   - Wall component lists with construction types and orientations
   - Look for "Zone" or "Conditioned Zone" sections

2. **Schedule pages** (high reliability)
   - Wall schedules listing construction assemblies
   - Room schedules with areas and heights
   - Assembly schedules with R-values and U-factors
   - Cross-reference with CBECC totals

3. **Floor plans** (medium reliability)
   - Zone names from room labels
   - Area dimensions for verification
   - Wall orientations from building layout
   - Window and door counts per wall

4. **Elevations/sections** (supplemental)
   - Ceiling heights verification
   - Wall heights for area calculation
   - Roof configurations for cathedral ceilings

### 3. Zone Identification Strategy

**Step 1: Locate zone list**
- CBECC pages typically have a "Zones" or "Conditioned Zones" section
- Each zone listed with name, type, area, and associated components

**Step 2: Extract zone names**
- Standard naming: "Zone 1", "Living Zone", "Bedroom Zone"
- May be single zone for small buildings (entire ADU = one zone)
- Multi-zone for larger buildings with different HVAC areas

**Step 3: Classify zone types**
- **Conditioned:** Heated and/or cooled spaces (living areas, bedrooms)
- **Unconditioned:** Garages, storage, unfinished areas
- **Plenum:** Return air plenums (rare in residential)

**Step 4: Collect zone metrics**
- Floor area from CBECC zone summary
- Ceiling height from room schedules or CBECC
- Volume (often calculated: area x height)
- Wall area totals per zone

### 4. Wall Component Extraction

**Step 1: Locate wall definitions**
- CBECC "Exterior Walls" or "Wall Components" section
- Wall schedules on schedule pages
- Each wall listed with name, zone, orientation, area

**Step 2: Extract wall properties**
- Name/identifier (e.g., "N Wall", "Zone 1 - North Wall")
- Parent zone (critical for linking)
- Construction type (e.g., "R-21 Wood Frame Wall")
- Orientation in degrees (0=N, 90=E, 180=S, 270=W)
- Gross area (before window/door deductions)
- Window area in this wall
- Door area in this wall

**Step 3: Link walls to zones**
- Each wall must reference a valid zone name
- If zone not specified, infer from wall name (e.g., "Zone 1 - N Wall" -> Zone 1)
- If still unclear, use "Zone 1" as default for single-zone buildings

### 5. Naming Conventions

**Zone names:**
- Use exact names from CBECC when available
- Common patterns: "Zone 1", "Conditioned Zone 1", "Living Zone"
- Keep consistent with other extractors for deduplication

**Wall names:**
- Include zone reference if multi-zone: "Zone 1 - N Wall"
- Include orientation: "North Wall", "N Wall", "Wall N"
- Or use CBECC identifiers directly: "Wall-1", "ExtWall-N"

**Consistency requirement:**
- Wall.zone field must exactly match a ZoneInfo.name
- Use identical strings for later schema assembly

### 6. Data Validation

Before returning extracted data, validate:

**ZoneInfo constraints:**
- `name`: Non-empty string (required)
- `zone_type`: "Conditioned", "Unconditioned", or "Plenum"
- `floor_area`: Float >= 0 (typically 200-5000 for residential zones)
- `ceiling_height`: Float > 0 (typically 8-12 ft)
- `volume`: Float >= 0 (should approximate area x height)

**WallComponent constraints:**
- `name`: Non-empty string (required)
- `zone`: Must match an extracted zone name
- `orientation`: 0-360 degrees (0=N, 90=E, 180=S, 270=W)
- `area`: Float >= 0 (gross wall area in sf)
- `window_area`: Float >= 0 (should not exceed wall area)
- `door_area`: Float >= 0

**Cross-validation:**
- Sum of wall areas for a zone should approximate zone's exterior_wall_area
- Window areas in walls should sum to zone's total window area
- Zone volume should be close to floor_area x ceiling_height

### 7. Handling Missing Data

**Required fields:**
- `name` for both zones and walls
- If missing, construct from context (e.g., "Zone 1" for single zone)

**Optional fields:**
- Most numeric fields can be null if not found
- Prefer extracting from CBECC over leaving null
- Document missing fields in notes

**Inference when allowed:**
- Volume can be calculated: floor_area x ceiling_height
- Orientation can be derived from "North Wall" label (0 degrees)
- Status defaults to "New" if not specified

### 8. Output Format

Return JSON matching this structure:

```json
{
  "zones": [
    {
      "name": "Zone 1",
      "zone_type": "Conditioned",
      "status": "New",
      "floor_area": 800.0,
      "ceiling_height": 9.0,
      "stories": 1,
      "volume": 7200.0,
      "exterior_wall_area": 1100.0,
      "exterior_wall_door_area": 40.0,
      "ceiling_below_attic_area": 800.0,
      "cathedral_ceiling_area": 0.0,
      "slab_floor_area": 800.0
    }
  ],
  "walls": [
    {
      "name": "Zone 1 - N Wall",
      "zone": "Zone 1",
      "status": "New",
      "construction_type": "R-21 Wood Frame",
      "orientation": 0.0,
      "area": 280.0,
      "window_area": 40.0,
      "door_area": 0.0,
      "tilt": 90.0,
      "framing_factor": 0.25
    },
    {
      "name": "Zone 1 - S Wall",
      "zone": "Zone 1",
      "status": "New",
      "construction_type": "R-21 Wood Frame",
      "orientation": 180.0,
      "area": 280.0,
      "window_area": 60.0,
      "door_area": 21.0,
      "tilt": 90.0,
      "framing_factor": 0.25
    }
  ],
  "notes": "Single zone building. Zone data from CBECC page 3. Wall orientations derived from cardinal labels. Framing factor assumed 0.25 standard."
}
```

## Error Handling

### Common Extraction Issues

1. **Multiple zone naming schemes:**
   - CBECC may use "Conditioned Zone 1" while plans say "Living Area"
   - Use CBECC naming as authoritative
   - Note alternate names in extraction notes

2. **Wall-zone linking ambiguity:**
   - If walls don't specify zone, check wall names for clues
   - Single-zone buildings: assign all walls to primary zone
   - Multi-zone: may need to infer from floor plan layout

3. **Orientation format variations:**
   - Degrees: 0, 90, 180, 270
   - Cardinal: N, E, S, W (convert to degrees)
   - Azimuth: May be relative to front orientation

4. **Missing wall area breakdowns:**
   - If only gross exterior wall area given, may need to estimate per-wall
   - Use floor plan proportions as guide
   - Note estimation in confidence report

### Orientation Conversion

Convert cardinal directions to degrees:
- North (N): 0 degrees
- Northeast (NE): 45 degrees
- East (E): 90 degrees
- Southeast (SE): 135 degrees
- South (S): 180 degrees
- Southwest (SW): 225 degrees
- West (W): 270 degrees
- Northwest (NW): 315 degrees

If CBECC shows orientation relative to front, add front orientation offset.

## Cross-Referencing Strategy

To improve accuracy:

1. **Zone area validation:**
   - CBECC zone floor_area should match sum of room areas
   - Compare with conditioned_floor_area from EnvelopeInfo

2. **Wall area totals:**
   - Sum of individual wall areas should match zone exterior_wall_area
   - Sum of window_area across walls should match total window area

3. **Volume verification:**
   - Zone volume should approximate floor_area x avg_ceiling_height
   - Discrepancy may indicate vaulted ceilings or multi-story zone

4. **Construction type consistency:**
   - All walls in same zone typically have same construction
   - Different types may indicate additions or alterations

## Confidence Reporting

Include extraction notes with confidence levels:

**High confidence:**
- Zone data from CBECC zone summary table
- Wall data from CBECC wall component list
- Clear numeric values with units

**Medium confidence:**
- Wall areas calculated from dimensions
- Orientations derived from cardinal labels
- Zone type inferred from room names

**Low confidence:**
- Values estimated from floor plan proportions
- Zones identified from room labels only
- Walls without explicit zone assignment

Example notes:
```
"Zone 1 data from CBECC page 3 (high confidence). Wall areas from CBECC wall list (high confidence). Framing factor assumed 0.25 (medium - not specified). Door areas estimated from door schedule (medium)."
```

## Next Steps After Extraction

The extracted JSON will be:
1. Merged with project and envelope data from project-extractor
2. Combined with windows from windows-extractor
3. Assembled into complete BuildingSpec
4. Passed to verifier for comparison against ground truth
5. Used in self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all zone and wall fields.
