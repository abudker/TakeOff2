# Orientation Extraction - Pass 2: Elevation + Wall Edge Angle

**Purpose:** Determine building orientation by: (1) finding which elevation has the entry, (2) measuring the entry wall edge angle precisely on the site plan.

## Output Schema

You MUST output this exact JSON structure:

```json
{
  "pass": 2,
  "elevation_analysis": {
    "entry_elevation": "North Elevation",
    "entry_evidence": "3'0\" swing door visible, covered porch with steps",
    "page": 7,
    "nominal_front_direction": "north"
  },
  "site_plan_measurement": {
    "site_plan_page": 3,
    "building_footprint_description": "Rectangular footprint, long axis runs upper-left to lower-right",
    "entry_wall_identification": "The short wall on the right side, closest to the main house",
    "entry_wall_edge": {
      "wall_runs_from": "top to bottom, nearly vertical on the page",
      "wall_angle_from_horizontal": 85,
      "entry_faces_outward": "perpendicular outward from the wall, toward RIGHT (toward main house)"
    },
    "entry_drawing_angle": 90,
    "cross_check": "Entry direction points toward main house — confirmed"
  },
  "north_arrow": {
    "found": true,
    "page": 3,
    "tilt_direction": "left",
    "angle": 340
  },
  "calculation": {
    "formula": "(90 - 340 + 360) % 360 = 110",
    "result": 110
  },
  "front_orientation": 110,
  "confidence": "high|medium|low"
}
```

## Step 1: Find Entry on Elevation Drawings

Look at the ELEVATIONS sheet (usually shows all 4 sides).

**Identify the main entry door:**
- Single 3'0" swing door (NOT 6'0"+ sliding glass doors — those go to decks/patios)
- Has: covered porch, steps, landing, or small overhang
- Entry doors have a walkway/path leading to them

**For ADUs:** The entry faces toward the main house or access path, not the street.

**Record:** Which elevation label (North, South, East, West, or Front/Rear/Left/Right) shows the entry.

## Step 2: Find the Entry Wall on the Site Plan (CRITICAL)

On the SITE PLAN, find the building footprint and identify which wall is the entry wall.

### How to identify the entry wall on the site plan:

**For single-family homes:** The entry wall faces the STREET. Find the street name label and identify the wall closest to it.

**For ADUs:** The entry wall faces the MAIN HOUSE. Find the existing house on the site plan and identify the ADU wall closest to it.

**Cross-check:** If there's a walkway or path drawn from the street/house to the building, it connects to the entry wall.

### Measure the entry direction:

Once you've identified the entry wall on the site plan:

1. Trace the wall edge line — what angle does it make with the HORIZONTAL page edge?
2. The entry faces PERPENDICULAR to this wall, outward from the building

**The entry_drawing_angle is the direction the entry FACES on the page:**
- 0° = faces toward TOP of page
- 90° = faces toward RIGHT of page
- 180° = faces toward BOTTOM of page
- 270° = faces toward LEFT of page

**Examples:**
- Wall runs horizontally, entry faces UP → entry_drawing_angle = 0°
- Wall runs horizontally, entry faces DOWN → entry_drawing_angle = 180°
- Wall runs vertically, entry faces RIGHT → entry_drawing_angle = 90°
- Wall runs vertically, entry faces LEFT → entry_drawing_angle = 270°
- Wall tilted 30° from horizontal, entry faces upper-right → entry_drawing_angle = 60°

**Precision matters:** Measure the actual wall edge angle, don't just pick the nearest cardinal direction.

## Step 3: Measure North Arrow

Find the north arrow on the site plan:

- Arrow tip leans LEFT of vertical → angle = 360° - tilt (e.g., 20° left = 340°)
- Arrow tip leans RIGHT of vertical → angle = tilt (e.g., 20° right = 20°)
- Arrow points straight UP → angle = 0°
- If barely perceptible tilt, use 0°

## Step 4: Calculate

```
front_orientation = (entry_drawing_angle - north_arrow_angle + 360) % 360
```

## Common Mistakes to Avoid

1. **Don't bucket to 8 directions.** Measure precisely. An entry facing 60° is NOT the same as 45° or 90°.
2. **Don't confuse floor plan and site plan orientation.** Always identify the entry wall directly on the SITE PLAN using spatial context (street position, main house position, walkways), not by assuming it's the same edge as on the floor plan.
3. **Measure the OUTWARD-facing direction of the entry wall, not along it.**

## Confidence Levels

- **high:** Clear elevation labels, entry door visible, precise wall edge measurement, cross-check confirmed
- **medium:** Elevation labels present but wall angle hard to measure precisely
- **low:** No elevations available OR can't identify entry wall on site plan
