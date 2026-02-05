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
- **North arrow angle:** Use `north_arrow.angle` directly as the north arrow angle. Do NOT re-estimate visually.
  Only fall back to visual estimation if `north_arrow.confidence` is "none" (meaning CV could not detect the arrow).
- **Building rotation:** The `building_rotation.rotation_from_horizontal` tells you how the building sits on the page.
  This can help you estimate the drawing_angle more precisely.
- Record the CV values in your output JSON.

### Fallback (no CV hints)

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

If CV wall edges are provided, use them to determine the drawing_angle precisely:
- Find the wall edge that best matches the front/entry wall based on your Step 2 analysis
- The `perpendicular_angle` of that wall edge IS the drawing_angle
- This is more precise than visual estimation from the page direction table

### Fallback (no CV hints)

Estimate the direction the front faces on the page. Use cardinal directions: 0°=top, 90°=right, 180°=bottom, 270°=left. Interpolate for diagonals.

## Step 4: Calculate

```
front_orientation = (drawing_angle - north_arrow_angle + 360) % 360
```

## Confidence Levels

- **high:** Clear north arrow, obvious front direction, precise angles
- **medium:** Small/unclear arrow OR front inferred from context
- **low:** No north arrow OR multiple possible fronts
