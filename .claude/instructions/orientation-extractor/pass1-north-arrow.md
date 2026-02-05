# Orientation Extraction - Pass 1: North Arrow + Street Direction

**Purpose:** Determine building orientation using north arrow and street/entry direction.

## Output Schema

You MUST output this exact JSON structure:

```json
{
  "pass": 1,
  "north_arrow": {
    "found": true,
    "page": 3,
    "description": "Compass rose in lower-right of site plan",
    "tilt_direction": "left|right|vertical",
    "tilt_magnitude": 20,
    "angle": 340
  },
  "front_identification": {
    "building_type": "adu|single_family",
    "method": "street_facing|entry_door|elevation_label",
    "description": "Front faces Canterbury Rd on the east side",
    "drawing_direction": "right",
    "drawing_angle": 90
  },
  "calculation": {
    "formula": "(90 - 340 + 360) % 360 = 110",
    "result": 110
  },
  "front_orientation": 110,
  "confidence": "high|medium|low"
}
```

## Step 1: Find North Arrow

### Using CV Hints (if provided)

If the prompt includes a "CV SENSOR MEASUREMENTS" section:
- **North arrow angle:** Use `north_arrow.angle` as a starting reference. Verify it matches what you see visually — if the CV angle seems inconsistent with the visual north arrow direction, use your own visual estimate instead.
  Ignore if `north_arrow.confidence` is "none".
- **Building rotation:** The `building_rotation.rotation_from_horizontal` can help estimate drawing_angle, but verify against what you see on the site plan.
- Record the CV values in your output JSON.

### Visual Estimation

Search pages in this order:
1. Site plan (most reliable)
2. Floor plan
3. Cover sheet

Estimate visually — see the direction table in Step 3.

## Step 2: Identify Building Front

**For Single-Family Homes:**
- Front faces the STREET
- Find street name on site plan
- The facade facing the street is the front

**For ADUs:**
- Front faces the ENTRY DOOR direction
- Find entry door on floor plan or elevation
- Entry faces toward access path, NOT necessarily the street

## Step 3: Measure Front Drawing Angle

### Using CV Wall Edge Hints

If CV wall edges are provided, use them as a reference for drawing_angle:
- Find the wall edge that best matches the front/entry wall based on your Step 2 analysis
- The `perpendicular_angle` of that wall edge is a reference for the drawing_angle
- Verify this matches your visual analysis — if it seems inconsistent with where the front actually faces, use your own visual estimate

### Visual Estimation

Estimate the direction the front faces on the page. Use cardinal directions: 0°=top, 90°=right, 180°=bottom, 270°=left. Interpolate for diagonals.

## Step 4: Calculate

```
front_orientation = (drawing_angle - north_arrow_angle + 360) % 360
```

## Confidence Levels

- **high:** Clear north arrow, obvious front direction, precise angles
- **medium:** Small/unclear arrow OR front inferred from context
- **low:** No north arrow OR multiple possible fronts
