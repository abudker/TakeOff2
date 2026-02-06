# Orientation Extractor Instructions

**Version:** v2.8.0
**Last updated:** 2026-02-04

## Overview

The orientation extractor determines the building's front orientation from architectural plans. This is critical because:
- All wall azimuths depend on front_orientation
- Window azimuths must match their parent wall orientation
- Incorrect orientation cascades to 10+ field errors

## How to Read PDFs

Use the Read tool with the `pages` parameter to read PDF pages:

```
Read(file_path="/path/to/plans.pdf", pages="1-5")
```

- The `pages` parameter accepts ranges like "1-5" or comma-separated pages like "1,3,5"
- For orientation, focus on site plans and floor plans (typically early pages)
- Read all pages mentioned in the prompt to find north arrows and building footprints

## Key Output

```json
{
  "front_orientation": 155.0,
  "north_arrow_found": true,
  "north_arrow_page": 3,
  "front_direction": "SSE",
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

**IMPORTANT: Carefully identify which way the arrow points:**

**Step 1: Which side does the arrow TIP lean toward?**
Look at the arrowhead (the pointed end). Does it lean toward the LEFT side of the page or the RIGHT side?
- Tip leans LEFT → arrow points upper-left → angle is 315°-359° (NOT 1°-45°)
- Tip leans RIGHT → arrow points upper-right → angle is 1°-45°
- Tip points straight up → angle is 0°

**Step 2: Estimate the tilt magnitude**
How many degrees off vertical?
- **Nearly vertical** = If the tilt is barely perceptible, use 0°
- Slight tilt = 10°-15°
- Moderate tilt = 20°-30°
- Strong tilt = 30°-45°

**NOTE:** If the arrow looks "almost straight up" with only a tiny tilt, use 0°. Don't over-analyze subtle tilts.

**Step 3: Calculate final angle**
- Tip leans LEFT by X° → north_arrow_angle = 360° - X° (e.g., 20° left = 340°)
- Tip leans RIGHT by X° → north_arrow_angle = X° (e.g., 20° right = 20°)

**SANITY CHECK:** If you see a clear tilt but calculated 10°-30° (right), double-check that the arrow doesn't actually tilt left (330°-350°). However, some arrows point straight up (0°) - don't add tilt that isn't there.

**Most site plans have rotated north arrows** (10-45° off vertical). Do NOT assume north = up.

### Step 3: Identify the Building Front

**CRITICAL: Different rules for different building types!**

#### For Single-Family Homes:
- Front faces the **street**
- Find the street name on the site plan
- The facade facing the street is the front

#### For ADUs (Accessory Dwelling Units):
- Front faces the **entry door direction**, NOT the street
- ADUs are typically in backyards behind the main house

**Finding the ADU entry (in order of reliability):**
1. **Floor plan door schedule** - Find the main entry door (usually D-01 or D-1, labeled "ENTRY" or the first exterior door)
2. **Floor plan layout** - Entry is typically near Living Room or Kitchen, not Bedrooms
3. **Elevation labels** - The elevation showing the entry door indicates which nominal direction the front faces (then measure actual angle)
4. **Site plan** - Look for walkway/path to ADU (entry faces the access direction)

**CRITICAL:** The entry direction is where someone WALKS OUT of the front door, not where the main house is located. ADU entries often face toward the driveway or access path, which may be to the side of the main house.

**How to identify an ADU:**
- Document title contains "ADU" or "Accessory Dwelling Unit"
- Site plan shows "Existing House" + smaller "ADU" or "Proposed ADU"
- Small building (400-1200 sq ft) behind larger main house

### Step 4: Measure Front Drawing Angle

**front_drawing_angle = direction you would WALK when exiting the front door**

Imagine standing at the front door, walking straight out. Which direction on the page are you walking?

**For ADUs, use this method:**

**Method A: Use Elevation Labels (Most Reliable)**
1. Check the elevations sheet for which elevation shows the main entry door
2. **Finding the entry door on elevations:**
   - Look for a single 3'0" swing door (not 6'0"+ sliding glass doors)
   - Entry doors have steps or a landing; sliding doors lead to decks/patios
   - If unclear, the entry is usually on the same elevation as the walkway/path from parking
3. If "North Elevation" shows the entry → front faces nominal North
4. **CRITICAL: Buildings are often rotated on their lots!** The building's "North" side usually does NOT face page north.
5. On the site plan, find the ADU footprint and identify the edge that corresponds to the entry (by matching building shape)
6. Measure the angle THAT SPECIFIC EDGE faces on the site plan - this is front_drawing_angle
7. Don't assume building "North" = page north. Measure the actual edge direction.

**Method B: Match Floor Plan to Site Plan**
1. Find the entry door on the floor plan:
   - Look for "ENTRY" label or arrow pointing to entry
   - Or find door D-01/D-1 (usually the main entry)
   - Or find the door nearest the Living Room/Foyer
2. Note the building shape and which edge has the entry
3. On the site plan, find the ADU footprint and match the shape
4. Identify which edge on the site plan corresponds to the entry edge
5. Measure that edge's outward direction on the site plan

**CRITICAL:** Measure angles ON THE SITE PLAN, not on the floor plan. Floor plans are often rotated for presentation.

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

**Example 1: Single-Family Home with Rotated North**
- North arrow points ~25° (slightly right of up)
- Front faces street on bottom of drawing → front_drawing_angle ≈ 180°
- front_orientation = (180 - 25 + 360) % 360 = 155° (SSE)

**Example 2: ADU with South-Facing Entry**
- North arrow points ~300° (upper-left) on site plan
- "South Elevation" shows entry door with covered porch → front faces nominal South
- On site plan, find ADU and measure which edge corresponds to the south elevation
- That edge faces lower-right on the site plan → front_drawing_angle ≈ 135°
- front_orientation = (135 - 300 + 360) % 360 = 195° (SSW)

**Example 3: ADU with West-Facing Entry**
- North arrow points ~10° right of up → north_arrow_angle ≈ 10°
- ADU entry faces toward main house/access path (lower-left of drawing)
- front_drawing_angle ≈ 260° (WSW direction on drawing)
- front_orientation = (260 - 10 + 360) % 360 = 250° (WSW)

**Example 4: ADU with Entry Facing Upper-Left**
- North arrow points ~45° (upper-right)
- "West Elevation" shows entry with covered porch/overhang → front faces nominal West
- On site plan, the ADU's west edge faces UPPER-LEFT → front_drawing_angle ≈ 320°
- front_orientation = (320 - 45 + 360) % 360 = 275° (W)

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

### Mistake 5: Floor Plan Rotation
❌ "Entry is on right side of floor plan, so front faces right on site plan (90°)"
✓ Floor plans are often rotated for presentation. Match the building footprint shape to the site plan and measure on the site plan. The site plan shows true orientation.

## Output Format

```json
{
  "front_orientation": 155.0,
  "north_arrow_found": true,
  "north_arrow_page": 3,
  "front_direction": "SSE",
  "confidence": "high",
  "reasoning": "north_arrow_angle = 25° (points upper-right). front_drawing_angle = 180° (front faces bottom toward street). Calculation: (180 - 25 + 360) % 360 = 155°",
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
