# Orientation Extractor Instructions

**Version:** v2.0.0
**Last updated:** 2026-02-04

## Overview

The orientation extractor determines the building's front orientation from architectural plans. This is critical because:
- All wall azimuths depend on front_orientation
- Window azimuths must match their parent wall orientation
- Incorrect orientation cascades to 10+ field errors

## Key Output

```json
{
  "front_orientation": 73.0,
  "north_arrow_found": true,
  "north_arrow_page": 3,
  "front_direction": "ENE",
  "confidence": "high",
  "reasoning": "...",
  "notes": "..."
}
```

**front_orientation:** Degrees clockwise from true north (0-360) that the FRONT of the building faces.
- 0 = Front faces North
- 90 = Front faces East
- 180 = Front faces South
- 270 = Front faces West

## The Formula

```
front_orientation = (front_drawing_angle - north_arrow_angle + 360) % 360
```

Where:
- **north_arrow_angle**: Direction the north arrow points on the page (0° = up, clockwise positive)
- **front_drawing_angle**: Direction the building front faces on the page (0° = up, clockwise positive)

## Step-by-Step Process

### Step 1: Find the North Arrow

Search in this order:
1. **Site plan** (most reliable) - shows building footprint on lot
2. **Floor plan** - may have smaller north arrow
3. **Cover sheet** - may have vicinity map

Look for:
- Compass rose (star shape with N label)
- Simple arrow with "N" or "NORTH"
- Circle with arrow
- Text like "REFERENCE NORTH"

### Step 2: Measure North Arrow Angle

Determine what angle the north arrow points relative to the TOP of the page:

| North Arrow Points | north_arrow_angle |
|-------------------|-------------------|
| Straight UP | 0° |
| Upper-right (~45°) | 45° |
| RIGHT | 90° |
| Lower-right (~135°) | 135° |
| DOWN | 180° |
| Lower-left (~225°) | 225° |
| LEFT | 270° |
| Upper-left (~315°) | 315° |

**Most site plans have rotated north arrows** (10-45° off vertical). Do NOT assume north = up.

### Step 3: Identify the Building Front

**CRITICAL: Different rules for different building types!**

#### For Single-Family Homes:
- Front faces the **street**
- Find the street name on the site plan
- The facade facing the street is the front

#### For ADUs (Accessory Dwelling Units):
- Front faces the **entry/main house**, NOT the street
- ADUs are typically in backyards behind the main house
- The ADU entry faces toward the main house or the path from the main house
- Look for:
  - Entry door symbol on floor plan
  - Path/walkway from main house to ADU
  - "ENTRY" label on ADU floor plan

**How to identify an ADU:**
- Document title contains "ADU" or "Accessory Dwelling Unit"
- Site plan shows "Existing House" + smaller "ADU" or "Proposed ADU"
- Small building (400-1200 sq ft) behind larger main house

### Step 4: Measure Front Drawing Angle

**front_drawing_angle = direction you would WALK when exiting the front door**

Imagine standing at the front door, walking straight out. Which direction on the page are you walking?

| You Walk Toward | front_drawing_angle |
|-----------------|---------------------|
| TOP of page | 0° |
| Upper-right | 45° |
| RIGHT of page | 90° |
| Lower-right | 135° |
| BOTTOM of page | 180° |
| Lower-left | 225° |
| LEFT of page | 270° |
| Upper-left | 315° |

### Step 5: Calculate front_orientation

```
front_orientation = (front_drawing_angle - north_arrow_angle + 360) % 360
```

**Example 1: Chamberlin Circle (Single-Family)**
- North arrow points ~17° (slightly right of up)
- Front faces street on right side of drawing → front_drawing_angle ≈ 90°
- front_orientation = (90 - 17 + 360) % 360 = 73°

**Example 2: Lamb ADU**
- North arrow points ~22° (upper-right on drawing)
- ADU entry faces toward main house (upper-left on drawing) → front_drawing_angle ≈ 315°? No...
- Actually: entry faces toward access path from street, which is upper-right
- front_drawing_angle ≈ 44° (toward the path/access)
- front_orientation = (44 - 22 + 360) % 360 = 22°

**Example 3: Martinez ADU**
- North arrow points straight up → north_arrow_angle ≈ 0°
- ADU entry faces toward main house/Wyoming Street (left side of drawing)
- front_drawing_angle ≈ 284° (WNW direction on drawing)
- front_orientation = (284 - 0 + 360) % 360 = 284°

### Step 6: Sanity Check

| front_orientation | Building Front Faces |
|-------------------|---------------------|
| 0° | True North |
| 45° | Northeast |
| 90° | True East |
| 135° | Southeast |
| 180° | True South |
| 225° | Southwest |
| 270° | True West |
| 315° | Northwest |

**Warning signs your answer may be wrong:**
- Exactly 0°, 90°, 180°, or 270° (most buildings are rotated)
- You used elevation labels ("North Elevation") instead of measuring
- You measured street direction instead of perpendicular facing direction

## MANDATORY: Show Your Work

Your reasoning field MUST include:

```
north_arrow_angle = X° (describe where arrow points on page)
front_drawing_angle = Y° (describe where front faces on page)
Calculation: (Y - X + 360) % 360 = Z°
front_orientation = Z°
```

## Common Mistakes

### Mistake 1: Using Elevation Labels
❌ "South Elevation faces street, so front_orientation = 180°"
✓ Elevation labels are nominal, not true compass directions. Measure actual angles.

### Mistake 2: Assuming North = Up
❌ "North is up, street is on right, so front_orientation = 90°"
✓ Check the actual north arrow direction. It's often rotated 10-45°.

### Mistake 3: ADU Front = Street
❌ "Street is on the east, so ADU front_orientation = 90°"
✓ ADU fronts face the entry path toward the main house, not the street.

### Mistake 4: Measuring Street Direction
❌ "Street runs north-south, so front_orientation = 0° or 180°"
✓ Measure perpendicular outward from the front facade, not along the street.

## Output Format

```json
{
  "front_orientation": 73.0,
  "north_arrow_found": true,
  "north_arrow_page": 3,
  "front_direction": "ENE",
  "confidence": "high",
  "reasoning": "north_arrow_angle = 17° (points upper-right). front_drawing_angle = 90° (front faces right toward Chamberlin Cir). Calculation: (90 - 17 + 360) % 360 = 73°",
  "notes": "Single-family home. Front faces street."
}
```

## Confidence Levels

**High confidence:**
- Clear north arrow found
- Entry/front clearly identified
- Angles measured precisely (±5°)

**Medium confidence:**
- North arrow small/unclear
- Front inferred from entry door
- Angles estimated (±15°)

**Low confidence:**
- No north arrow found
- Multiple possible fronts
- Angles estimated (±30°)
