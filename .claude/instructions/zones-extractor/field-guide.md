# Zones Extractor Field Guide

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

This guide maps each ZoneInfo and WallComponent schema field to its source location in Title 24 compliance documents. Use this as a reference during extraction to know where to look for each field.

---

## ZoneInfo Fields

### name
**Type:** string (required)
**Description:** Zone name/identifier

**Document sources:**
1. **CBECC-Res output:** "Zones" or "Conditioned Zones" section, first column
2. **Room schedules:** Zone designation column
3. **Floor plans:** Area labels or zone boundary annotations
4. **HVAC schedules:** Zone assignment column

**Common labels in documents:**
- "Zone Name", "Zone", "Thermal Zone"
- "Conditioned Zone 1", "Zone 1", "Living Zone"

**Extraction tips:**
- CBECC names are authoritative - use exact spelling
- Single-zone buildings often just have "Zone 1" or "Conditioned Zone 1"
- Multi-zone buildings may name by function: "Living Zone", "Bedroom Zone"
- Garage zones typically named "Garage" or "Unconditioned Zone"

**Example values:**
- "Zone 1"
- "Conditioned Zone 1"
- "Living Area"
- "ADU Zone"

---

### zone_type
**Type:** enum ["Conditioned", "Unconditioned", "Plenum"] (optional)
**Description:** Thermal conditioning classification

**Document sources:**
1. **CBECC-Res output:** Zone type column or designation
2. **Room schedules:** Conditioning status column
3. **Mechanical schedules:** Served zone designations

**Common labels in documents:**
- "Type", "Zone Type", "Conditioning"
- "Cond.", "Uncond.", "Conditioned", "Unconditioned"

**Extraction tips:**
- Most residential zones are "Conditioned"
- Garages are typically "Unconditioned"
- "Plenum" is rare in residential (commercial return air plenums)
- If not explicitly stated, infer from HVAC service:
  - Has heating/cooling equipment serving it -> "Conditioned"
  - No HVAC service -> "Unconditioned"

**Example values:**
- "Conditioned" (living spaces, bedrooms, kitchens)
- "Unconditioned" (garages, storage, utility rooms)
- "Plenum" (return air spaces, rare)

---

### status
**Type:** enum ["New", "Existing", "Altered"] (optional)
**Description:** Construction status for Title 24 compliance

**Document sources:**
1. **CBECC-Res output:** Status column in zone list
2. **Project scope:** Addition vs new construction designation
3. **CF1R form:** Project type section

**Common labels in documents:**
- "Status", "Construction Status", "Component Status"
- "New", "Exist", "Alt", "Altered"

**Extraction tips:**
- New construction projects: All zones are "New"
- Addition projects: New zones are "New", existing are "Existing"
- Alteration projects: Modified zones are "Altered"
- Infer from project scope (RunScope) if not zone-specific:
  - "Newly Constructed" -> all zones "New"
  - "Addition" -> new zones "New"
  - "Alteration" -> modified zones "Altered"

**Example values:**
- "New" (new construction, additions)
- "Existing" (unmodified existing spaces)
- "Altered" (modifications to existing spaces)

---

### floor_area
**Type:** float >= 0 (optional)
**Description:** Zone floor area in square feet

**Document sources:**
1. **CBECC-Res output:** "Floor Area", "Zone Area" column in zone summary
2. **Room schedules:** Area column, sum rooms in zone
3. **Floor plans:** Area calculations, dimension annotations
4. **CF1R form:** Zone area breakdown

**Common labels in documents:**
- "Floor Area (sf)", "Area", "Zone Area", "CFA"
- "Sq Ft", "SF", "ft2"

**Extraction tips:**
- Use CBECC value as authoritative (calculated by software)
- Units should be square feet
- For multi-zone, each zone has separate floor area
- Sum of zone floor areas should approximate total CFA
- Typical residential zone: 200-3000 sf

**Example values:**
- 800.0 (small ADU, single zone)
- 1500.0 (larger home zone)
- 450.0 (bedroom zone in multi-zone building)

**Typical ranges:**
- ADU single zone: 400-1200 sf
- Single family zone: 1000-3000 sf
- Bedroom zone: 150-500 sf

---

### ceiling_height
**Type:** float > 0 (optional)
**Description:** Ceiling height in feet

**Document sources:**
1. **CBECC-Res output:** "Ceiling Height" or "Height" in zone data
2. **Room schedules:** Height column
3. **Wall schedules:** Wall height (implies ceiling height)
4. **Section drawings:** Vertical dimensions

**Common labels in documents:**
- "Ceiling Height", "Clg Ht", "Height", "Room Height"
- "FT", "ft", "feet"

**Extraction tips:**
- Standard residential: 8 ft (most common)
- Modern/high-end: 9 ft or 10 ft ceilings
- Check for vaulted/cathedral sections (variable height)
- If variable height, CBECC may show average
- Typical range: 7.5-12 ft for residential

**Example values:**
- 8.0 (standard ceiling)
- 9.0 (9-foot ceiling)
- 10.0 (high ceiling)
- 12.0 (great room with vaulted)

---

### stories
**Type:** integer >= 1 (optional)
**Description:** Number of stories within the zone

**Document sources:**
1. **CBECC-Res output:** "Stories" or "Number of Stories" in zone data
2. **Floor plans:** Multiple floor plan sheets for same zone
3. **Section drawings:** Floor count visible

**Common labels in documents:**
- "Stories", "Floors", "Number of Stories"

**Extraction tips:**
- Single-story zone: 1 (most ADUs)
- Two-story zone: 2 (loft spaces, multi-floor zones)
- Each zone tracks its own story count
- Zone may span multiple floors (open floor plan with 2-story volume)

**Example values:**
- 1 (single story, most common)
- 2 (two-story zone, great room with loft)

---

### volume
**Type:** float >= 0 (optional)
**Description:** Zone volume in cubic feet

**Document sources:**
1. **CBECC-Res output:** "Volume" column in zone summary
2. **Calculated:** floor_area x ceiling_height

**Common labels in documents:**
- "Volume (cf)", "Vol", "Zone Volume"
- "Cu Ft", "CF", "ft3"

**Extraction tips:**
- CBECC usually calculates this automatically
- If not shown, calculate: floor_area x ceiling_height
- Vaulted ceilings may have higher volume than simple calculation
- Used for infiltration calculations

**Example values:**
- 7200.0 (800 sf x 9 ft)
- 6400.0 (800 sf x 8 ft)
- 12000.0 (1200 sf x 10 ft)

**Calculation:**
```
volume = floor_area x ceiling_height
Example: 800 sf x 9 ft = 7200 cf
```

---

### exterior_wall_area
**Type:** float >= 0 (optional)
**Description:** Total exterior wall area for the zone in square feet

**Document sources:**
1. **CBECC-Res output:** "Ext Wall Area" in zone summary
2. **Wall schedules:** Sum of wall areas assigned to zone
3. **Calculated:** Perimeter x height

**Common labels in documents:**
- "Exterior Wall Area", "Ext Wall", "Wall Area"
- "Above Grade Wall Area"

**Extraction tips:**
- Sum of all exterior walls belonging to this zone
- Does not include interior walls or below-grade walls
- Should match sum of individual WallComponent areas for zone
- Includes gross area (before window/door deductions)

**Example values:**
- 1100.0 (small single-story zone)
- 1800.0 (larger zone)
- 2400.0 (two-story zone)

---

### exterior_wall_door_area
**Type:** float >= 0 (optional)
**Description:** Total door area in exterior walls of this zone

**Document sources:**
1. **CBECC-Res output:** "Door Area" in zone summary
2. **Door schedules:** Sum of exterior door areas for zone
3. **Floor plans:** Count and size of exterior doors

**Common labels in documents:**
- "Door Area", "Ext Door Area", "Exterior Door Area"

**Extraction tips:**
- Only exterior doors (not interior doors)
- Typical exterior door: 3' x 6'8" = ~20 sf
- Sliding glass doors: 5' x 6'8" = ~33 sf per panel
- Sum all exterior door areas for the zone

**Example values:**
- 21.0 (single 3x7 door)
- 40.0 (two standard doors)
- 66.0 (sliding glass door)

---

### ceiling_below_attic_area
**Type:** float >= 0 (optional)
**Description:** Ceiling area below attic space in square feet

**Document sources:**
1. **CBECC-Res output:** "Ceiling Below Attic" in zone summary
2. **Ceiling schedules:** Attic ceiling assembly areas
3. **Roof/ceiling plans:** Area with attic above

**Common labels in documents:**
- "Ceiling Below Attic", "Attic Ceiling", "Flat Ceiling Area"
- "Ceiling (Attic Above)"

**Extraction tips:**
- Flat or low-slope ceiling with attic space above
- Does not include cathedral/vaulted sections
- Often equals floor_area for single-story with attic
- Zero for buildings without attic (slab on grade with flat roof)

**Example values:**
- 800.0 (full attic above single-story)
- 600.0 (partial attic)
- 0.0 (no attic, cathedral ceiling throughout)

---

### cathedral_ceiling_area
**Type:** float >= 0 (optional)
**Description:** Cathedral/vaulted ceiling area in square feet

**Document sources:**
1. **CBECC-Res output:** "Cathedral Ceiling" in zone summary
2. **Ceiling schedules:** Vaulted ceiling assembly areas
3. **Section drawings:** Areas with exposed roof structure

**Common labels in documents:**
- "Cathedral Ceiling", "Vaulted Ceiling", "Exposed Ceiling"
- "Roof/Ceiling Combined"

**Extraction tips:**
- Ceiling directly under roof (no attic space)
- Common in great rooms, A-frame designs
- Zero for standard flat ceiling buildings
- May have different insulation requirements than attic ceiling

**Example values:**
- 0.0 (standard flat ceiling, most common)
- 200.0 (great room vaulted section)
- 800.0 (entire building is cathedral)

---

### slab_floor_area
**Type:** float >= 0 (optional)
**Description:** Slab-on-grade floor area in square feet

**Document sources:**
1. **CBECC-Res output:** "Slab Floor" in zone summary
2. **Foundation plans:** Slab area dimensions
3. **Floor schedules:** Slab assembly areas

**Common labels in documents:**
- "Slab Floor Area", "Slab on Grade", "SOG Area"
- "Concrete Slab Floor"

**Extraction tips:**
- Concrete floor in contact with ground
- Common for single-story, garages, additions
- Zero for raised floor or basement foundations
- Often equals floor_area for slab-on-grade buildings

**Example values:**
- 800.0 (entire zone on slab)
- 0.0 (raised floor foundation)
- 400.0 (partial slab)

---

### exterior_floor_area
**Type:** float >= 0 (optional)
**Description:** Floor area exposed to exterior in square feet

**Document sources:**
1. **CBECC-Res output:** "Exterior Floor" or "Raised Floor" in zone summary
2. **Foundation plans:** Raised floor areas
3. **Floor schedules:** Floor over unconditioned space

**Common labels in documents:**
- "Exterior Floor", "Raised Floor", "Floor Over Unconditioned"
- "Cantilever Floor"

**Extraction tips:**
- Floor exposed to outdoor air (cantilever, over open crawl)
- Typically zero for slab-on-grade
- May apply to second floor over garage
- Requires different insulation than slab

**Example values:**
- 0.0 (slab on grade, most common)
- 100.0 (bay window cantilever)
- 400.0 (room over unconditioned garage)

---

## WallComponent Fields

### name
**Type:** string (required)
**Description:** Wall name/identifier

**Document sources:**
1. **CBECC-Res output:** Wall list, name/ID column
2. **Wall schedules:** Wall mark or identifier column
3. **Floor plans:** Wall callout labels

**Common labels in documents:**
- "Wall Name", "Wall ID", "Mark", "Wall"
- "N Wall", "Wall-1", "ExtWall-N"

**Extraction tips:**
- Use CBECC identifiers when available
- Include orientation in name: "N Wall", "Zone 1 - South"
- Include zone reference for multi-zone: "Zone 1 - N Wall"
- Keep names consistent for deduplication

**Example values:**
- "N Wall" (north wall, single zone)
- "Zone 1 - N Wall" (north wall, multi-zone)
- "Wall-1" (CBECC identifier)
- "ExtWall-North" (explicit exterior north)

---

### zone
**Type:** string (required for linking)
**Description:** Parent zone name

**Document sources:**
1. **CBECC-Res output:** Zone column in wall list
2. **Wall schedules:** Zone assignment column
3. **Inferred:** From wall name if zone not explicit

**Common labels in documents:**
- "Zone", "Parent Zone", "Assigned Zone"

**Extraction tips:**
- CRITICAL: Must exactly match a ZoneInfo.name
- If not specified, infer from wall name pattern
- Single-zone buildings: all walls belong to primary zone
- Multi-zone: check floor plan for wall-zone boundaries

**Example values:**
- "Zone 1" (must match extracted zone name exactly)
- "Living Zone"
- "Conditioned Zone 1"

---

### status
**Type:** enum ["New", "Existing", "Altered"] (optional)
**Description:** Construction status

**Document sources:**
1. **CBECC-Res output:** Status column in wall list
2. **Wall schedules:** Construction status
3. **Project scope:** Infer from project type

**Common labels in documents:**
- "Status", "Construction Status"
- "New", "Exist", "Alt"

**Extraction tips:**
- Same logic as zone status
- New construction: all walls "New"
- Addition: new walls "New", existing unchanged
- Alteration: modified walls "Altered"

**Example values:**
- "New"
- "Existing"
- "Altered"

---

### construction_type
**Type:** string (optional)
**Description:** Wall construction assembly type

**Document sources:**
1. **CBECC-Res output:** "Construction" or "Assembly" column
2. **Wall schedules:** Wall type or assembly column
3. **Construction details:** Wall section details

**Common labels in documents:**
- "Construction Type", "Wall Type", "Assembly"
- "R-21 Wall", "2x6 @ 16 o.c.", "Wood Frame Wall"

**Extraction tips:**
- Often includes R-value: "R-21 Wood Frame"
- May reference assembly library: "Wall Type A"
- Common residential: "R-21 Wood Frame", "R-13 2x4"
- High performance: "R-38 Advanced Frame"

**Example values:**
- "R-21 Wood Frame Wall"
- "R-13 2x4 Stud Wall"
- "WoodFramedWall-R21"
- "2x6 @ 24 o.c. R-21 Cavity"

---

### orientation
**Type:** float 0-360 degrees (optional)
**Description:** Wall orientation in degrees from true north

**Document sources:**
1. **CBECC-Res output:** "Orientation" or "Azimuth" column
2. **Floor plans:** Building layout with north arrow
3. **Inferred:** From cardinal direction in wall name

**Common labels in documents:**
- "Orientation (deg)", "Azimuth", "Direction"
- "N", "S", "E", "W" (cardinal directions)

**Extraction tips:**
- 0 = North, 90 = East, 180 = South, 270 = West
- CBECC may show degrees or cardinal
- Convert cardinal to degrees if needed
- If front orientation specified, walls may be relative

**Cardinal to degrees conversion:**
| Direction | Degrees |
|-----------|---------|
| N         | 0       |
| NE        | 45      |
| E         | 90      |
| SE        | 135     |
| S         | 180     |
| SW        | 225     |
| W         | 270     |
| NW        | 315     |

**Example values:**
- 0.0 (north-facing)
- 90.0 (east-facing)
- 180.0 (south-facing)
- 270.0 (west-facing)

---

### area
**Type:** float >= 0 (optional)
**Description:** Gross wall area in square feet

**Document sources:**
1. **CBECC-Res output:** "Area" column in wall list
2. **Wall schedules:** Gross area column
3. **Calculated:** Length x height from plans

**Common labels in documents:**
- "Area (sf)", "Gross Area", "Wall Area"
- "Sq Ft", "SF"

**Extraction tips:**
- Gross area before window/door deductions
- Net area = Gross - windows - doors
- Sum of wall areas should match zone exterior_wall_area
- Typical residential wall: 100-500 sf

**Example values:**
- 280.0 (30' x 9.33' wall)
- 320.0 (40' x 8' wall)
- 180.0 (20' x 9' wall)

**Calculation if needed:**
```
wall_area = wall_length x wall_height
Example: 30 ft x 9.33 ft = 280 sf
```

---

### window_area
**Type:** float >= 0 (optional)
**Description:** Window area in this wall in square feet

**Document sources:**
1. **CBECC-Res output:** Window area column per wall
2. **Window schedules:** Windows by wall or orientation
3. **Floor plans:** Window marks and sizes per wall

**Common labels in documents:**
- "Window Area", "Glazing Area", "Fenestration"
- "Win Area", "Windows"

**Extraction tips:**
- Sum of all windows in this wall
- Should not exceed gross wall area
- Cross-reference with window schedule
- May need to sum from individual windows

**Example values:**
- 40.0 (two medium windows)
- 60.0 (large picture window)
- 0.0 (no windows in wall)

---

### door_area
**Type:** float >= 0 (optional)
**Description:** Door area in this wall in square feet

**Document sources:**
1. **CBECC-Res output:** Door area column per wall
2. **Door schedules:** Doors by wall or location
3. **Floor plans:** Door marks and sizes per wall

**Common labels in documents:**
- "Door Area", "Ext Door Area"
- "Door", "Entry"

**Extraction tips:**
- Only exterior doors (not interior)
- Standard door: ~21 sf (3' x 7')
- Sliding glass: ~33 sf per panel
- Should match door schedule totals

**Example values:**
- 0.0 (no exterior door in wall)
- 21.0 (single standard door)
- 42.0 (double door or two singles)
- 66.0 (6' sliding glass door)

---

### tilt
**Type:** float (optional)
**Description:** Wall tilt angle from vertical in degrees

**Document sources:**
1. **CBECC-Res output:** "Tilt" column if non-standard
2. **Elevations:** Sloped wall detail

**Common labels in documents:**
- "Tilt (deg)", "Tilt Angle", "Wall Tilt"

**Extraction tips:**
- 90 degrees = vertical (standard wall)
- < 90 = wall leans inward (rare)
- > 90 = wall leans outward (rare)
- Almost always 90 for residential walls
- Non-90 only for specialized designs

**Example values:**
- 90.0 (vertical wall, standard)
- 80.0 (sloped wall, uncommon)

---

### framing_factor
**Type:** float 0-1 (optional)
**Description:** Fraction of wall area that is framing

**Document sources:**
1. **CBECC-Res output:** "Framing Factor" or "FF" column
2. **Construction details:** Framing assumptions
3. **Default:** 0.25 for standard wood frame

**Common labels in documents:**
- "Framing Factor", "FF", "Frame Fraction"
- May not be shown (use default)

**Extraction tips:**
- Standard wood frame: 0.25 (25% framing)
- Advanced framing: 0.15-0.20
- Steel stud: 0.02-0.05
- If not specified, use 0.25 as default
- Affects U-value calculations

**Example values:**
- 0.25 (standard wood frame, most common)
- 0.15 (advanced framing)
- 0.23 (typical 2x6 @ 24" o.c.)

---

## Extraction Best Practices

### Page Reading Order
1. Start with CBECC-Res pages (zone summaries most complete)
2. Check wall schedules for component details
3. Use floor plans for verification
4. Reference elevations for heights

### Common Document Layouts

**CBECC-Res Zone Summary:**
- Zone name | Type | Floor Area | Height | Volume | Ext Wall Area
- Row per zone with all metrics
- Totals row at bottom

**CBECC-Res Wall List:**
- Wall Name | Zone | Construction | Orientation | Area | Window | Door
- Row per wall component
- Grouped by zone or orientation

**Wall Schedule:**
- Mark | Type | Construction | R-Value | Area | Notes
- Row per wall type
- May show area per orientation

**Floor Plan:**
- Building outline with dimensions
- Room labels with areas
- Window and door symbols
- North arrow for orientation

### Quality Checks

Before finalizing extraction:
- [ ] All zones have unique names
- [ ] All walls reference valid zone names
- [ ] Sum of wall areas approximates zone exterior_wall_area
- [ ] Orientations are valid (0-360 degrees)
- [ ] Window areas don't exceed wall areas
- [ ] Volume approximates floor_area x ceiling_height
- [ ] Single-story zones have stories = 1

---

## Field Summary Table

### ZoneInfo Fields

| Field | Type | Required | Sources | Default |
|-------|------|----------|---------|---------|
| name | string | Yes | CBECC, schedules | - |
| zone_type | enum | No | CBECC, inference | "Conditioned" |
| status | enum | No | CBECC, project scope | "New" |
| floor_area | float | No | CBECC, plans | - |
| ceiling_height | float | No | CBECC, schedules | 8.0 |
| stories | int | No | CBECC, plans | 1 |
| volume | float | No | CBECC, calculated | area x height |
| exterior_wall_area | float | No | CBECC, wall sum | - |
| exterior_wall_door_area | float | No | CBECC, door schedule | - |
| ceiling_below_attic_area | float | No | CBECC | - |
| cathedral_ceiling_area | float | No | CBECC | 0.0 |
| slab_floor_area | float | No | CBECC, foundation | - |
| exterior_floor_area | float | No | CBECC | 0.0 |

**Total ZoneInfo fields:** 13 (1 required + 12 optional)

### WallComponent Fields

| Field | Type | Required | Sources | Default |
|-------|------|----------|---------|---------|
| name | string | Yes | CBECC, wall schedule | - |
| zone | string | Link | CBECC, inferred | - |
| status | enum | No | CBECC, project scope | "New" |
| construction_type | string | No | CBECC, wall schedule | - |
| orientation | float | No | CBECC, cardinal | - |
| area | float | No | CBECC, wall schedule | - |
| window_area | float | No | CBECC, windows | 0.0 |
| door_area | float | No | CBECC, doors | 0.0 |
| tilt | float | No | CBECC | 90.0 |
| framing_factor | float | No | CBECC, default | 0.25 |

**Total WallComponent fields:** 10 (1 required + 9 optional)

---

*End of Field Guide*
