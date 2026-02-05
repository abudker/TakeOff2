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

### Using CV Hints (if provided)

If the prompt includes CV wall edge measurements:
- The `wall_edges` list contains measured wall angles from the site plan
- After identifying which wall is the entry wall (using spatial reasoning from Step 1), match it to a CV wall edge:
  - Match by position ("top", "right", "bottom", "left") relative to your entry wall identification
  - Use the matched edge's `perpendicular_angle` as a reference for `entry_drawing_angle`
- Verify the CV angle matches your spatial analysis — if it seems inconsistent with where the entry actually faces, use your own measurement instead

### Visual Estimation (no CV hints or CV seems wrong)

On the SITE PLAN, find the building footprint and identify which wall is the entry wall.

**How to identify the entry wall on the site plan:**

**For single-family homes:** The entry wall faces the STREET. Find the street name label and identify the wall closest to it.

**For ADUs:** The entry wall faces the MAIN HOUSE. Find the existing house on the site plan and identify the ADU wall closest to it.

**Cross-check:** If there's a walkway or path drawn from the street/house to the building, it connects to the entry wall.

Trace the entry wall edge, measure its angle from horizontal, then determine the perpendicular outward direction. See direction reference: 0°=top, 90°=right, 180°=bottom, 270°=left.

## Step 3: Measure North Arrow

### Using CV Hints

If CV north arrow angle is provided with confidence != "none", use it as a reference.
Verify it matches what you see visually — if inconsistent, use your own estimate.

### Visual Estimation

Estimate visually — left-of-vertical = 360° - tilt, right = tilt, vertical = 0°.

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
