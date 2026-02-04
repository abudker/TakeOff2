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

### 4. Exterior Walls by Orientation - GROSS AREA ONLY

**IMPORTANT:** Extract GROSS wall area only. Do NOT calculate net wall area. Do NOT deduct window/door openings. The verifier compares against gross wall area values.

**Step 1: Create orientation sections**
Create entries for House - North, East, South, West based on true north.

**Step 2: Locate wall definitions**
- CBECC "Exterior Walls" or "Wall Components" section
- Wall schedules on schedule pages
- Each wall listed with orientation/azimuth and area

**Step 3: Group walls by cardinal orientation**
CBECC often lists walls by azimuth. Group them into cardinal directions:
- **North (N):** Azimuth 315-360° or 0-45°
- **East (E):** Azimuth 45-135°
- **South (S):** Azimuth 135-225°
- **West (W):** Azimuth 225-315°

**Step 4: Extract wall properties per orientation**
For each cardinal direction, extract:
- `gross_wall_area`: Total thermal boundary wall area (sq ft) - **DO NOT DEDUCT OPENINGS**
- `azimuth`: True azimuth in degrees (use midpoint if rotated)
- `construction_type`: e.g., "R-21 2x6 Wood Frame"
- `framing_factor`: Framing fraction (default 0.25 if not specified)
- `status`: New, Existing, or Altered
- `fenestration`: Leave empty - windows-extractor will populate this
- `opaque_doors`: Extract non-glazed doors in this wall with area

**Step 5: Handle rotated buildings**
If the building is not aligned to cardinal directions:
- Use the closest cardinal direction for each wall
- Set azimuth to the actual value from CBECC
- Example: Front = 45° (NE) → use "north" slot with azimuth = 45
- Add FLAG: "Building rotated, walls grouped to nearest cardinal direction"

**Step 6: Validate against plans**
If plans include opening-percentage or facade calculations:
- Do NOT use them for energy wall area unless they explicitly state "thermal boundary wall area"
- Add FLAG if you suspect the value includes non-thermal-boundary area

### 5. Naming Conventions

**Zone names (in thermal_boundary):**
- Use exact names from CBECC when available
- Common patterns: "Zone 1", "Conditioned Zone 1", "Living Zone"
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
- Prefer extracting from CBECC over leaving null
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
      "gross_wall_area": 136.0,
      "azimuth": 0.0,
      "construction_type": "R-21 2x6 Wood Frame",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": [
        {
          "name": "D1",
          "door_type": "Entry",
          "area": 19.0
        }
      ]
    },
    "east": {
      "gross_wall_area": 160.0,
      "azimuth": 90.0,
      "construction_type": "R-21 2x6 Wood Frame",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": []
    },
    "south": {
      "gross_wall_area": 136.0,
      "azimuth": 180.0,
      "construction_type": "R-21 2x6 Wood Frame",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": []
    },
    "west": {
      "gross_wall_area": 180.0,
      "azimuth": 270.0,
      "construction_type": "R-21 2x6 Wood Frame",
      "framing_factor": 0.25,
      "status": "New",
      "fenestration": [],
      "opaque_doors": []
    }
  },
  "thermal_boundary": {
    "conditioned_zones": [
      {
        "name": "Zone 1",
        "floor_area": 320.0,
        "ceiling_height": 8.0,
        "volume": 2560.0,
        "stories": 1,
        "exterior_wall_area": 612.0,
        "ceiling_below_attic_area": 320.0,
        "cathedral_ceiling_area": 0.0,
        "slab_floor_area": 320.0
      }
    ],
    "unconditioned_zones": [],
    "total_conditioned_floor_area": 320.0
  },
  "ceilings": [
    {
      "name": "Ceiling 1",
      "ceiling_type": "Below Attic",
      "zone": "Zone 1",
      "status": "New",
      "area": 320.0,
      "construction_type": "R-38 Roof Rafter"
    }
  ],
  "slab_floors": [
    {
      "name": "Slab 1",
      "zone": "Zone 1",
      "status": "New",
      "area": 320.0,
      "perimeter": 72.0,
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
      "reason": "Conditioned area from CBECC (320 sf). Computed footprint from dimensions is 340 sf (6.25% difference). Using CBECC value.",
      "source_page": 3
    },
    {
      "field_path": "slab_floors[0].edge_insulation_r_value",
      "severity": "medium",
      "reason": "Slab edge insulation not specified. Verify on foundation plan or energy notes.",
      "source_page": null
    }
  ],
  "notes": "Single zone ADU. Wall gross areas from CBECC page 3. Foundation type: slab-on-grade. Garage not modeled / not in scope per plans."
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
