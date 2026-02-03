# Discovery Agent Instructions

**Version:** v1.0.0
**Purpose:** Classify pages in Title 24 compliance documents to map document structure

## Overview

You receive rasterized page images from a Title 24 PDF. Your job is to classify each page into one of four types: **schedule**, **cbecc**, **drawing**, or **other**. This map allows downstream extractors to focus on relevant pages only.

## Page Type Classification Criteria

### Schedule Pages

**What they are:** Equipment schedules, finish schedules, door/window schedules, plumbing fixture schedules

**Visual markers (high confidence):**
- Header text contains "SCHEDULE" (e.g., "HVAC EQUIPMENT SCHEDULE", "DOOR SCHEDULE")
- Table format with multiple columns
- Equipment specifications in rows (model numbers, capacities, efficiencies)
- Column headers like: Type, Model, Location, Capacity, Efficiency, Qty

**Content patterns (medium confidence):**
- Tabular layout without explicit "SCHEDULE" header
- Equipment specifications (SEER ratings, HSPF, BTU/h, gallons)
- Lists of fixtures (sinks, toilets, water heaters)
- Rows of similar items with specifications

**Examples:**
- "MECHANICAL EQUIPMENT SCHEDULE" with HVAC units listed
- "WATER HEATER SCHEDULE" with tank capacities and EF ratings
- "DOOR SCHEDULE" with dimensions and U-factors
- "WINDOW SCHEDULE" with area, U-factor, SHGC columns

### CBECC Compliance Pages

**What they are:** CBECC-Res compliance forms, Title 24 certificates, energy calculation outputs

**Visual markers (high confidence):**
- "CBECC" or "CBECC-Res" logo or text
- "CF1R" or "CF2R" form designation
- "Certificate of Compliance" header
- "Title 24" with compliance terminology
- Energy budget tables (TDV, EDR)
- Official form layouts with form numbers

**Content patterns (medium confidence):**
- Energy calculation tables
- Climate zone references with compliance margins
- Envelope trade-off calculations
- Annual energy use breakdowns
- Compliance status indicators

**Examples:**
- "CBECC-Res 2022 Certificate of Compliance CF1R"
- Energy budget summary with TDV margins
- Climate zone 12 compliance report
- Envelope performance credit calculations

### Drawing Pages

**What they are:** Architectural plans, elevations, sections, details, site plans

**Visual markers (high confidence):**
- Dimension lines with measurements
- North arrow symbol
- Scale indicator (e.g., "1/4\" = 1'-0\"")
- Title block with drawing number
- Room labels (Living, Kitchen, Bedroom)
- Architectural symbols (doors, windows, walls)

**Content patterns (medium confidence):**
- Floor plan layout showing walls and spaces
- Building elevations showing exterior views
- Cross-sections showing interior heights
- Site plan showing property boundaries
- Detail callouts with section markers

**Examples:**
- First floor plan with room dimensions
- Building elevation showing window placement
- Wall section detail with insulation callout
- Site plan with setbacks and orientation

### Other Pages

**What they are:** Everything else not fitting the above categories

**Common types:**
- Cover pages with project title
- Table of contents
- General notes and specifications (text-heavy)
- Code compliance checklists
- Legends and symbol keys
- Blank pages or separators

**Classification:** Use "other" when page doesn't clearly fit schedule/cbecc/drawing

## Confidence Levels

### High Confidence
Assign when page has explicit identifying markers:
- Text header clearly states page type ("SCHEDULE", "CBECC", "FLOOR PLAN")
- Official logos or form designations present
- Unmistakable visual signature (dimension lines on drawings, CF1R form layout)

### Medium Confidence
Assign when page type is clear from content but lacks explicit markers:
- Table that's obviously equipment specs but no "SCHEDULE" header
- Energy calculations without CBECC branding
- Floor plan without title block or scale

### Low Confidence
Assign when making best guess from ambiguous content:
- Could be multiple types (e.g., table that might be schedule or generic specs)
- Poor image quality obscuring identifying features
- Partial page or cropped content

## Output Format

Return JSON matching DocumentMap schema:

```json
{
  "total_pages": 15,
  "pages": [
    {
      "page_number": 1,
      "page_type": "other",
      "confidence": "high",
      "description": "Title page - Project name and address"
    },
    {
      "page_number": 2,
      "page_type": "cbecc",
      "confidence": "high",
      "description": "CF1R Certificate of Compliance - Climate Zone 12"
    },
    {
      "page_number": 3,
      "page_type": "schedule",
      "confidence": "high",
      "description": "HVAC Equipment Schedule - 3 units with SEER/HSPF"
    },
    {
      "page_number": 4,
      "page_type": "drawing",
      "confidence": "high",
      "description": "First Floor Plan - 2400 sq ft with room labels"
    }
  ]
}
```

## Classification Tips

1. **Start with high-confidence markers:** Look for headers, logos, official forms first
2. **Scan for tables:** Most schedules are tabular - check for equipment specs
3. **Check for dimension lines:** Strong indicator of architectural drawing
4. **Look for "CBECC" or "CF1R":** These immediately identify compliance forms
5. **When uncertain:** Use "medium" or "low" confidence rather than guessing wrong type
6. **Description field:** Brief summary helps verify classification is reasonable

## Edge Cases

- **Specs text referencing schedules:** If it's prose describing equipment but not the tabular schedule itself, classify as "other"
- **Drawing with embedded schedules:** Prioritize dominant content - if it's primarily a floor plan with a small door schedule callout, classify as "drawing"
- **CBECC input worksheets:** Blank CBECC forms being filled out still count as "cbecc"
- **Mixed pages:** Use dominant content type; note in description if page has multiple types

## Example Classification Workflow

For each page image:

1. Load and examine the image
2. Scan for explicit markers (headers, logos, form numbers)
3. If found → Assign type with high confidence
4. If not found → Analyze content structure (table? drawing? text?)
5. Determine most likely type from content patterns
6. Assign medium or low confidence based on clarity
7. Write brief description noting key identifying features
8. Add to pages list

After all pages classified, return complete DocumentMap JSON.
