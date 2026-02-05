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

Search pages in this order:
1. Site plan (most reliable)
2. Floor plan
3. Cover sheet

**Measure the arrow angle:**
- Look at the ARROW HEAD (pointed tip)
- Which side of vertical does it lean?
  - Leans LEFT → `tilt_direction: "left"`, angle = 360 - magnitude (e.g., 20° left = 340°)
  - Leans RIGHT → `tilt_direction: "right"`, angle = magnitude (e.g., 20° right = 20°)
  - Straight UP → `tilt_direction: "vertical"`, angle = 0°

**If arrow looks nearly vertical:** Use angle = 0°. Don't over-analyze subtle tilts.

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

What direction does the front face ON THE PAGE?

| Front faces... | drawing_angle |
|----------------|---------------|
| TOP of page | 0° |
| Upper-right | 45° |
| RIGHT of page | 90° |
| Lower-right | 135° |
| BOTTOM of page | 180° |
| Lower-left | 225° |
| LEFT of page | 270° |
| Upper-left | 315° |

## Step 4: Calculate

```
front_orientation = (drawing_angle - north_arrow_angle + 360) % 360
```

## Confidence Levels

- **high:** Clear north arrow, obvious front direction, precise angles
- **medium:** Small/unclear arrow OR front inferred from context
- **low:** No north arrow OR multiple possible fronts
