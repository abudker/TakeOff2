# Windows Extractor Field Guide

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

This guide maps each WindowComponent schema field to its source location in Title 24 compliance documents. Use this as a reference during extraction to know where to look for each field.

---

## WindowComponent Fields

### name
**Type:** string (required)
**Description:** Window name/identifier

**Document sources:**
1. **Window schedule:** Mark or ID column (W1, W2, A, B)
2. **Floor plans:** Window callout marks
3. **CBECC-Res output:** Fenestration component names
4. **Door schedule:** For glazed doors (SGD1, D1)

**Common labels in documents:**
- "Mark", "ID", "Window", "Type"
- "W-1", "W1", "Window A", "WIN-1"
- "SGD", "SGD1" (sliding glass door)

**Extraction tips:**
- Use exact marks from schedule
- Consistent naming enables floor plan cross-reference
- Glazed doors use door marks (D1, SGD1)
- If no mark, construct: "Window 1", "Window 2"

**Example values:**
- "W1" (window type 1)
- "W2" (window type 2)
- "SGD1" (sliding glass door)
- "Window A" (letter designation)
- "Picture Window" (descriptive)

---

### wall
**Type:** string (optional but critical for linking)
**Description:** Parent wall name

**Document sources:**
1. **Window schedule:** Location or Wall column
2. **CBECC-Res output:** Parent wall reference
3. **Floor plans:** Window position on wall
4. **Inferred:** From azimuth/orientation match

**Common labels in documents:**
- "Location", "Wall", "Parent", "Orientation"
- "N Wall", "North", "Zone 1 - N Wall"

**Extraction tips:**
- CRITICAL: Must exactly match WallComponent.name
- If schedule shows "North", translate to wall name format
- If not explicit, infer from floor plan position
- Single-zone: use simple orientation names
- Multi-zone: include zone reference

**Example values:**
- "Zone 1 - N Wall" (multi-zone format)
- "North Wall" (single-zone simple)
- "N Wall" (abbreviated)
- "Living Room - West" (room-based)

**Linking strategy:**
1. Check schedule for explicit wall reference
2. Check CBECC for parent wall
3. Infer from azimuth (0=N, 90=E, 180=S, 270=W)
4. Match to wall names from zones-extractor

---

### status
**Type:** enum ["New", "Existing", "Altered"] (optional)
**Description:** Construction status

**Document sources:**
1. **Window schedule:** Status column
2. **CBECC-Res output:** Component status
3. **Project scope:** Infer from project type
4. **Notes:** "New windows" or "Replace existing"

**Common labels in documents:**
- "Status", "Condition", "Type"
- "New", "Exist", "Existing", "Replace"

**Extraction tips:**
- New construction: all windows "New"
- Alteration: may have mix of statuses
- Replacement windows: "New" (replacing existing)
- Window upgrade only: may be "Altered"

**Example values:**
- "New" (new construction, most common)
- "Existing" (unmodified existing window)
- "Altered" (upgraded existing window)

---

### azimuth
**Type:** float 0-360 degrees (optional)
**Description:** Orientation in degrees from true north

**Document sources:**
1. **CBECC-Res output:** Azimuth column in fenestration list
2. **Window schedule:** Orientation or Azimuth column
3. **Floor plans:** Building orientation + window position
4. **Inferred:** From wall orientation

**Common labels in documents:**
- "Azimuth", "Orientation", "Direction"
- "N", "S", "E", "W" (cardinal)
- Degrees: "0", "90", "180", "270"

**Extraction tips:**
- CBECC may show degrees directly
- Cardinal directions convert to degrees
- If only wall known, use wall orientation
- North = 0, East = 90, South = 180, West = 270

**Cardinal to degrees conversion:**
| Direction | Degrees | Solar Exposure |
|-----------|---------|----------------|
| N         | 0       | Minimal direct sun |
| NE        | 45      | Morning sun |
| E         | 90      | Strong morning sun |
| SE        | 135     | Morning/midday sun |
| S         | 180     | Maximum year-round |
| SW        | 225     | Afternoon/midday sun |
| W         | 270     | Strong afternoon sun |
| NW        | 315     | Afternoon sun |

**Example values:**
- 0.0 (north-facing)
- 90.0 (east-facing)
- 180.0 (south-facing, highest solar)
- 270.0 (west-facing)

---

### height
**Type:** float > 0 (optional)
**Description:** Window height in feet

**Document sources:**
1. **Window schedule:** Height or Size column
2. **Elevations:** Vertical window dimensions
3. **CBECC-Res output:** Fenestration dimensions
4. **Product specs:** Nominal sizes

**Common labels in documents:**
- "Height", "H", "HT"
- "3'x4'" format (width x height) - extract second value
- "36\"x48\"" in inches - convert to feet

**Extraction tips:**
- Convert inches to feet: 48" = 4 ft
- Schedule may show WxH or HxW - verify convention
- Standard residential: 3-6 ft tall
- Sliding doors: 6.67 ft (6'8") typical
- Clerestory/transom: 1-2 ft

**Example values:**
- 4.0 (standard 4-foot window)
- 5.0 (large window)
- 6.67 (sliding glass door, 6'8")
- 3.0 (smaller window)
- 2.0 (transom window)

**Common window heights:**
- Standard: 3', 4', 5' (36", 48", 60")
- Sliding doors: 6'8" (80")
- Picture windows: 4'-6'

---

### width
**Type:** float > 0 (optional)
**Description:** Window width in feet

**Document sources:**
1. **Window schedule:** Width or Size column
2. **Floor plans:** Horizontal window dimensions
3. **CBECC-Res output:** Fenestration dimensions
4. **Elevations:** Horizontal dimensions

**Common labels in documents:**
- "Width", "W", "WD"
- "3'x4'" format (width x height) - extract first value
- "36\"x48\"" in inches - convert to feet

**Extraction tips:**
- Convert inches to feet: 36" = 3 ft
- Width shown first in WxH format typically
- Standard residential: 2-8 ft wide
- Sliding doors: 5-12 ft wide
- Picture windows: 4-10 ft wide

**Example values:**
- 3.0 (standard 3-foot window)
- 4.0 (larger window)
- 6.0 (sliding glass door)
- 2.5 (narrow window)
- 8.0 (large picture window)

**Common window widths:**
- Standard: 2', 3', 4' (24", 36", 48")
- Sliding doors: 5', 6', 8' (60", 72", 96")
- Picture: 5'-10'

---

### multiplier
**Type:** integer >= 1 (optional)
**Description:** Number of identical windows

**Document sources:**
1. **Window schedule:** Quantity or Qty column
2. **Floor plans:** Count of same window mark
3. **CBECC-Res output:** Count per type

**Common labels in documents:**
- "Qty", "Quantity", "Count", "#"
- "2 ea", "x2", "(2)"

**Extraction tips:**
- Schedule shows quantity per type
- Multiplier=1 for unique windows
- Use multiplier to avoid duplicate entries
- Alternative: create N separate entries

**Example values:**
- 1 (single window of this type)
- 2 (two identical windows)
- 4 (four identical windows)

**When to use multiplier vs separate entries:**
- Same wall: use multiplier
- Different walls: separate entries needed
- Different orientations: separate entries needed

---

### area
**Type:** float >= 0 (optional)
**Description:** Window area in square feet

**Document sources:**
1. **Window schedule:** Area column (per unit or total)
2. **CBECC-Res output:** Fenestration area
3. **Calculated:** Height x Width x Multiplier

**Common labels in documents:**
- "Area (sf)", "Area", "Sq Ft", "SF"
- "Total Area" (may include multiplier)
- "Unit Area" (single window)

**Extraction tips:**
- Check if area is per-unit or total
- Per-unit: multiply by quantity for total
- Total: divide by quantity for per-unit
- Verify: height x width should match per-unit area

**Example values:**
- 12.0 (3' x 4' window)
- 24.0 (3' x 4' x 2 multiplier)
- 40.0 (6' x 6.67' sliding door)
- 20.0 (4' x 5' window)

**Calculation:**
```
area = height x width x multiplier
Example: 4 ft x 3 ft x 2 = 24 sf
```

---

### u_factor
**Type:** float > 0 (optional)
**Description:** Thermal transmittance (U-factor)

**Document sources:**
1. **Window schedule:** U-Factor or U-Value column
2. **CBECC-Res output:** Fenestration performance section
3. **Product specifications:** Manufacturer ratings
4. **CF1R form:** Fenestration requirements

**Common labels in documents:**
- "U-Factor", "U-Value", "Uw", "U"
- "Btu/(hr-sf-F)" units
- NFRC rating label reference

**Extraction tips:**
- Lower U-factor = better insulation
- Title 24 2022 prescriptive: U-0.30 max (most zones)
- High-performance: U-0.25 or lower
- Same U-factor often used for all windows
- Verify units (should be Btu/(hr-sf-F))

**Example values:**
- 0.30 (meets prescriptive, common)
- 0.28 (good performance)
- 0.25 (high performance)
- 0.32 (slightly above prescriptive)
- 0.22 (triple pane, very high performance)

**Typical ranges by glazing:**
| Glazing Type | U-Factor Range |
|--------------|----------------|
| Single pane | 0.90-1.10 |
| Double pane | 0.25-0.50 |
| Triple pane | 0.15-0.25 |
| Low-E double | 0.25-0.35 |

**California Title 24 requirements (2022):**
- Prescriptive max: U-0.30 (most zones)
- Performance path: varies by tradeoffs

---

### shgc
**Type:** float 0-1 (optional)
**Description:** Solar Heat Gain Coefficient

**Document sources:**
1. **Window schedule:** SHGC column
2. **CBECC-Res output:** Fenestration performance section
3. **Product specifications:** Manufacturer ratings
4. **CF1R form:** Fenestration requirements

**Common labels in documents:**
- "SHGC", "Solar Heat Gain", "SHG"
- Decimal value 0-1

**Extraction tips:**
- Lower SHGC = less solar heat gain
- Title 24 2022 prescriptive: SHGC 0.23-0.25 (varies by zone)
- Coastal zones (cool): SHGC 0.23 typical
- Inland zones (hot): SHGC 0.22 typical (reduce heat gain)
- North-facing may have higher SHGC allowed

**Example values:**
- 0.23 (meets prescriptive, coastal)
- 0.22 (hot climate compliance)
- 0.25 (slightly higher, acceptable)
- 0.30 (north-facing allowable)
- 0.18 (very low solar gain, hot climates)

**Typical ranges:**
| Climate | Typical SHGC |
|---------|--------------|
| Coastal (CZ 1-6) | 0.22-0.25 |
| Inland hot (CZ 10-15) | 0.20-0.23 |
| Mountain (CZ 16) | 0.25-0.30 |

**Orientation considerations:**
- South windows: lower SHGC beneficial (reduce overheating)
- North windows: higher SHGC acceptable (minimal sun)
- East/West windows: lower SHGC important (low-angle sun)

---

### exterior_shade
**Type:** string (optional)
**Description:** External shading description

**Document sources:**
1. **Window schedule:** Shading or Notes column
2. **CBECC-Res output:** Overhang/shading section
3. **Elevations:** Overhang depths shown
4. **Floor plans:** Covered areas/porches

**Common labels in documents:**
- "Shading", "Overhang", "Shade", "Exterior Shade"
- "OH", "PF" (projection factor)
- Depth in feet or inches

**Extraction tips:**
- Overhangs: depth measurement (e.g., "2ft overhang")
- Awnings: type and depth
- Porches: depth if covering window
- May show projection factor (depth/height ratio)
- No shading: null or empty

**Example values:**
- null (no exterior shading)
- "2ft overhang" (horizontal overhang)
- "4ft porch" (covered porch)
- "Awning" (retractable or fixed)
- "PF=0.5" (projection factor notation)
- "3ft overhang with 1ft offset" (detailed)

**Shading effectiveness:**
- South: overhangs very effective (blocks high summer sun)
- East/West: vertical fins more effective (low-angle sun)
- North: minimal benefit from shading

---

## Extraction Best Practices

### Page Reading Order
1. Start with window schedule (complete list)
2. Check CBECC fenestration section (performance values)
3. Use floor plans for counts and locations
4. Reference elevations for dimensions confirmation

### Common Document Layouts

**Window Schedule:**
```
| Mark | Size (WxH) | Qty | U-Factor | SHGC | Location | Notes |
|------|------------|-----|----------|------|----------|-------|
| W1   | 3'x4'      | 2   | 0.30     | 0.23 | North    | Fixed |
| W2   | 4'x5'      | 1   | 0.30     | 0.23 | South    | Operable |
| SGD  | 6'x6'8"    | 1   | 0.28     | 0.22 | West     | Sliding |
```

**CBECC Fenestration Section:**
- Component Name | Wall | Area | U-Factor | SHGC | Azimuth
- Totals row with aggregate values
- May group by wall orientation

**Floor Plan Window Callouts:**
- Window marks in circles or symbols
- Dimension strings nearby
- Reference to schedule
- Building north arrow

### Quality Checks

Before finalizing extraction:
- [ ] All windows have unique names
- [ ] Window areas sum to expected total
- [ ] U-factors in reasonable range (0.20-0.50)
- [ ] SHGC values in reasonable range (0.15-0.40)
- [ ] Heights and widths produce correct areas
- [ ] Multipliers match schedule quantities
- [ ] Wall references match extracted wall names
- [ ] Azimuths consistent with wall orientations

### Glazed Door Checklist

Include if fenestration:
- [ ] Sliding glass doors (always include)
- [ ] French doors with glazing (include)
- [ ] Entry doors with >50% glass (include)
- [ ] Sidelights next to doors (include)

Exclude:
- [ ] Solid wood/metal doors
- [ ] Doors with small vision panels only
- [ ] Garage doors (unless mostly glass)

---

## Field Summary Table

| Field | Type | Required | Sources | Default |
|-------|------|----------|---------|---------|
| name | string | Yes | Schedule mark | - |
| wall | string | Link | Schedule, inferred | - |
| status | enum | No | Schedule, project | "New" |
| azimuth | float | No | CBECC, schedule, inferred | Wall orientation |
| height | float | No | Schedule, CBECC | - |
| width | float | No | Schedule, CBECC | - |
| multiplier | int | No | Schedule quantity | 1 |
| area | float | No | Schedule, calculated | h x w x mult |
| u_factor | float | No | Schedule, CBECC | 0.30 |
| shgc | float | No | Schedule, CBECC | 0.23 |
| exterior_shade | string | No | Schedule, elevations | null |

**Total WindowComponent fields:** 11 (1 required + 10 optional)

---

## Common Extraction Scenarios

### Scenario 1: Complete Window Schedule
- All data available in schedule
- Extract directly, minimal inference
- High confidence extraction

### Scenario 2: Missing Performance Values
- Schedule has dimensions only
- Check CBECC for U-factor and SHGC
- If not found, use prescriptive defaults
- Medium confidence with note

### Scenario 3: Glazed Doors
- May be on door schedule, not window
- Look for SGD marks or "Sliding Glass"
- Include in windows array
- Note door designation

### Scenario 4: Multiple Same-Type Windows
- Schedule shows Qty > 1
- Use multiplier field
- Or create separate entries per wall
- Ensure total area is correct

### Scenario 5: Wall Assignment Ambiguous
- Schedule shows "Front" not cardinal
- Check front orientation in CBECC
- Convert to true azimuth
- Document inference in notes

---

*End of Field Guide*
