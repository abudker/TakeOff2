# Zones Extractor Instructions

**Version:** v2.1.0
**Last updated:** 2026-02-04

## Core Rule

**All takeoffs must be based on the THERMAL BOUNDARY (conditioned vs outside/unconditioned), not overall facade area or parapet/architectural area.**

This means:
- Only include walls that form the thermal envelope (boundary between conditioned and exterior)
- Do NOT include parapets, screened porches, open patio walls, or architectural facade area outside the thermal boundary
- Garage walls are exterior walls of unconditioned space (separate from house walls)

## Overview

The zones extractor extracts **orientation-based** wall and thermal boundary data from Title 24 compliance documentation. This version outputs data in TakeoffSpec format, organizing walls by cardinal orientation (North/East/South/West) with fenestration nested under each wall.

**Key principles:**
- `house_walls`: GROSS wall area by orientation (North/East/South/West) - do NOT calculate net area
- `thermal_boundary`: Explicit separation of conditioned vs unconditioned zones
- `flags`: **MANDATORY** - Every uncertainty, assumption, or discrepancy MUST have a FLAG

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

1. **Floor plans** (highest reliability for zones)
   - Zone names from room labels
   - Area dimensions and callouts
   - Wall orientations from building layout
   - Window and door counts per wall
   - North arrow for orientation

2. **Schedule pages** (high reliability for construction)
   - Wall schedules listing construction assemblies
   - Room schedules with areas and heights
   - Assembly schedules with R-values and U-factors
   - Door schedules for opaque door areas

3. **Elevations/sections** (medium reliability)
   - Ceiling heights verification
   - Wall heights for area calculation
   - Roof configurations for cathedral ceilings

4. **Energy notes / General notes** (supplemental)
   - Insulation specifications
   - Construction type details
   - R-values and assembly descriptions

### 3. Zone Identification Strategy

**Step 1: Identify conditioned spaces from floor plan**
- Look for room labels (Living, Kitchen, Bedroom, Bathroom)
- Identify conditioned vs unconditioned areas (garage, storage)
- For simple buildings (ADUs), entire building may be one zone

**Step 2: Extract zone names**
- For ADU projects, use "ADU" as the zone name
- Standard naming: "Zone 1", "Living Zone", "Bedroom Zone"
- May be single zone for small buildings (entire ADU = one zone)
- Multi-zone for larger buildings with different HVAC areas

**Step 3: Classify zone types**
- **Conditioned:** Heated and/or cooled spaces (living areas, bedrooms)
- **Unconditioned:** Garages, storage, unfinished areas
- **Plenum:** Return air plenums (rare in residential)

**Step 4: Collect zone metrics**
- Floor area from floor plan area callouts or room schedule
  - **DO NOT include overhangs or exterior projections**
  - Use the CONDITIONED floor area (interior dimension)
  - If stated as "320 SF" on plans, use 320 - do not recalculate
- Ceiling height from section drawings (MANDATORY for accuracy):
  - Look for "Level 1" to "B.O. Roof" or "Ceiling" dimension on sections
  - ADU/small buildings typically have 8'-6" to 8'-8" ceilings (8.5 ft)
  - May show as "8'-7 1/2"" (convert to decimal: 8.625 ft ≈ 8.5)
  - For vaulted/cathedral ceilings, use average height
  - **If sections show ~8'-6" to 8'-8", use 8.5 ft**
  - Wall areas depend on ceiling height (area = perimeter x height)
- Volume (calculated: area x height)
- Wall area totals calculated from perimeter dimensions x ceiling height

### 4. Exterior Walls by Orientation - GROSS AREA ONLY

**IMPORTANT:** Extract GROSS wall area only. Do NOT calculate net wall area. Do NOT deduct window/door openings. The verifier compares against gross wall area values.

**Step 1: Create orientation sections**
Create entries for House - North, East, South, West based on true north.

**Step 2: Locate wall definitions**
- Floor plan with north arrow and wall dimensions
- Wall schedules on schedule pages
- Calculate wall area from perimeter dimensions x wall height

**Step 3: Group walls by cardinal orientation**
Use floor plan orientation and north arrow. Group walls into cardinal directions:
- **North (N):** Azimuth 315-360° or 0-45°
- **East (E):** Azimuth 45-135°
- **South (S):** Azimuth 135-225°
- **West (W):** Azimuth 225-315°

**Step 4: Extract wall properties per orientation**
For each cardinal direction, extract:
- `gross_wall_area`: Total thermal boundary wall area (sq ft) - **DO NOT DEDUCT OPENINGS**
- `azimuth`: True azimuth in degrees (ACTUAL orientation, not cardinal - see Step 5)
- `construction_type`: Use CBECC-style short form: "R-21 Wall" (not "R-21 2x6", "R-21 2x6 Wall", or "R-21 2x6 Wood Frame")
- `framing_factor`: Framing fraction (default 0.25 if not specified)
- `status`: New, Existing, or Altered
- `fenestration`: Leave empty - windows-extractor will populate this
- `opaque_doors`: Extract non-glazed doors in this wall with area

**Step 5: Handle rotated buildings**
If the building is not aligned to cardinal directions:
- Use the closest cardinal direction for the JSON key (north/east/south/west)
- **CRITICAL:** Set `azimuth` to the ACTUAL wall orientation, NOT cardinal
- Calculate actual azimuth from front_orientation: wall_azimuth = front_orientation + offset
  - North wall offset: -90° (or +270°)
  - East wall offset: 0° (faces same direction as front)
  - South wall offset: +90°
  - West wall offset: +180°
- Example: Front = 73° (NE facing)
  - "north" slot → azimuth = 73 - 90 = 343° (wrapping)
  - "east" slot → azimuth = 73°
  - "south" slot → azimuth = 73 + 90 = 163°
  - "west" slot → azimuth = 73 + 180 = 253°
- Add FLAG: "Building rotated {X}° from true north"

**Step 6: Validate against plans**
If plans include opening-percentage or facade calculations:
- Do NOT use them for energy wall area unless they explicitly state "thermal boundary wall area"
- Add FLAG if you suspect the value includes non-thermal-boundary area

### 5. Naming Conventions

**Zone names (in thermal_boundary):**
- **ADU projects:** Use "ADU" as the zone name (not "Zone 1")
- **Single-family homes:** Use descriptive name from plans or "Living Zone"
- **Multi-zone buildings:** Use room-based names like "Living Zone", "Bedroom Zone"
- Derive zone name from project type on title block when possible
- Keep consistent with other extractors for deduplication

**Orientation keys (in house_walls):**
- Use lowercase cardinal directions: `north`, `east`, `south`, `west`
- These are JSON keys, not names

**Door names (in opaque_doors):**
- Descriptive names: "Entry Door", "Garage Door", "Side Door"
- Or use door schedule marks: "D1", "D2"

**Consistency requirement:**
- Zone names in `thermal_boundary.conditioned_zones` must be unique
- The orchestrator transforms orientation keys to wall names (e.g., "north" → "N Wall")

### 6. Data Validation

Before returning extracted data, validate:

**OrientationWall constraints (house_walls.{direction}):**
- `gross_wall_area`: Float >= 0 (total thermal boundary wall area in sq ft)
- `azimuth`: Float 0-360 (0=N, 90=E, 180=S, 270=W)
- `construction_type`: Non-empty string if specified
- `fenestration`: Leave empty (windows-extractor populates)
- `opaque_doors`: List of non-glazed doors with name and area

**ConditionedZone constraints (thermal_boundary.conditioned_zones):**
- `name`: Non-empty string (required)
- `floor_area`: Float >= 0 (typically 200-5000 for residential)
- `ceiling_height`: Float > 0 (typically 8-12 ft)
- `volume`: Float >= 0 (should approximate area x height)
- `exterior_wall_area`: Float >= 0 (sum of wall areas)

**Conditioned Floor Area validation:**
- Use the plans' stated "Conditioned Area" if provided
- If you compute footprint from dimensions and it differs by >3% from stated area, add FLAG with both values
- The stated conditioned area takes precedence

**Foundation type:**
- Determine: slab-on-grade vs raised floor/crawlspace
- If unclear, add FLAG: "Verify foundation type"

**Cross-validation:**
- Sum of house_walls gross areas ≈ thermal_boundary zone exterior_wall_area
- Zone volume should be close to floor_area x ceiling_height
- total_conditioned_floor_area should match sum of zone floor_areas

**MANDATORY uncertainty flags:**
- Add a FLAG for every assumption, uncertainty, or discrepancy
- Add a FLAG for every value that differs from another source (e.g., CBECC vs schedule)
- Use severity levels: high (likely incorrect), medium (uncertain), low (minor)
- Every FLAG should describe: what is uncertain, where to verify (sheet/detail)

### 7. Handling Missing Data

**Required fields:**
- `name` for both zones and walls
- If missing, construct from context (e.g., "Zone 1" for single zone)

**Optional fields:**
- Most numeric fields can be null if not found
- Document missing fields in notes

**Inference when allowed:**
- Volume can be calculated: floor_area x ceiling_height
- Orientation can be derived from "North Wall" label (0 degrees)
- Status defaults to "New" if not specified

### 8. Output Format (TakeoffSpec)

Return JSON matching this **orientation-based** structure:

```json
{
  "house_walls": {
    "north": {
      "gross_wall_area": 150.0,
      "azimuth": 0.0,
      "construction_type": "R-21 Wall",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": [
        {
          "name": "D1",
          "door_type": "Entry",
          "area": 21.0
        }
      ]
    },
    "east": {
      "gross_wall_area": 180.0,
      "azimuth": 90.0,
      "construction_type": "R-21 Wall",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": []
    },
    "south": {
      "gross_wall_area": 150.0,
      "azimuth": 180.0,
      "construction_type": "R-21 Wall",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": []
    },
    "west": {
      "gross_wall_area": 180.0,
      "azimuth": 270.0,
      "construction_type": "R-21 Wall",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": []
    }
  },
  "thermal_boundary": {
    "conditioned_zones": [
      {
        "name": "ADU",
        "floor_area": 450.0,
        "ceiling_height": 8.5,
        "volume": 3825.0,
        "stories": 1,
        "exterior_wall_area": 660.0,
        "ceiling_below_attic_area": 450.0,
        "cathedral_ceiling_area": 0.0,
        "slab_floor_area": 450.0
      }
    ],
    "unconditioned_zones": [],
    "total_conditioned_floor_area": 450.0
  },
  "ceilings": [
    {
      "name": "Ceiling 1",
      "ceiling_type": "Below Attic",
      "zone": "ADU",
      "status": "New",
      "area": 450.0,
      "construction_type": "R-38 Roof Rafter"
    }
  ],
  "slab_floors": [
    {
      "name": "Slab 1",
      "zone": "ADU",
      "status": "New",
      "area": 450.0,
      "perimeter": 85.0,
      "edge_insulation_r_value": null,
      "carpeted_fraction": 0.8,
      "heated": false
    }
  ],
  "flags": [
    {
      "field_path": "house_walls.north.framing_factor",
      "severity": "low",
      "reason": "Framing factor not specified in plans, used standard 0.25. Verify on wall schedule.",
      "source_page": null
    },
    {
      "field_path": "thermal_boundary.conditioned_zones[0].floor_area",
      "severity": "medium",
      "reason": "Conditioned area from floor plan (450 sf). Computed footprint from dimensions is 460 sf (2.2% difference). Using stated value.",
      "source_page": 2
    },
    {
      "field_path": "slab_floors[0].edge_insulation_r_value",
      "severity": "medium",
      "reason": "Slab edge insulation not specified. Verify on foundation plan or energy notes.",
      "source_page": null
    }
  ],
  "notes": "Single zone ADU. Wall gross areas calculated from perimeter x ceiling height. Foundation type: slab-on-grade."
}
```

## Error Handling

### Common Extraction Issues

1. **Multiple zone naming schemes:**
   - Plans may use "Living Area" while schedules say "Zone 1"
   - For ADU projects, use "ADU" as the zone name
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

If orientation is relative to front, add front orientation offset.

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
- Zone data from floor plan area callouts
- Wall areas from wall schedule
- Clear numeric values with units

**Medium confidence:**
- Wall areas calculated from perimeter x height
- Orientations derived from cardinal labels
- Zone type inferred from room names

**Low confidence:**
- Values estimated from floor plan proportions
- Zones identified from room labels only
- Walls without explicit zone assignment

Example notes:
```
"Zone floor area from floor plan callout (high confidence). Wall areas calculated from perimeter x ceiling height (medium confidence). Framing factor assumed 0.25 (medium - not specified). Door areas from door schedule (high confidence)."
```

## Next Steps After Extraction

The extracted JSON will be:
1. Merged with project and envelope data from project-extractor
2. Combined with windows from windows-extractor
3. Assembled into complete BuildingSpec
4. Passed to verifier for comparison against ground truth
5. Used in self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all zone and wall fields.
