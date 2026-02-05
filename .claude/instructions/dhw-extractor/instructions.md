# DHW Extractor Instructions

**Version:** v1.1.0
**Last updated:** 2026-02-04

## Overview

The DHW (Domestic Hot Water) extractor extracts water heating system data from Title 24 compliance documentation. Water heating systems include storage tank water heaters, tankless (on-demand) units, and heat pump water heaters, which are increasingly common for Title 24 compliance.

## How to Read PDFs

Use the Read tool with the `pages` parameter to read PDF pages:

```
Read(file_path="/path/to/plans.pdf", pages="1-10")
```

- The `pages` parameter accepts ranges like "1-10" or comma-separated pages like "1,3,5"
- Maximum 20 pages per Read call - for larger PDFs, make multiple calls
- Each page will be displayed visually for extraction

## Extraction Workflow

### 1. Input Reception

You will receive:
- **PDF paths:** Paths to source PDFs with relevant page numbers
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `schedule_pages`: Equipment schedules (water heater schedules)
- `drawing_pages`: Plumbing plans
- `other`: Cover pages, notes, specifications

**NOTE:** CBECC-Res compliance forms are NOT typically included in architectural plan sets. The source documents are architectural PDFs (floor plans, schedules, title blocks). Do not expect to find CBECC pages.

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **Equipment Schedules** (highest reliability)
   - Water Heater Schedule
   - Contains model numbers, capacities, efficiency ratings
   - May have manufacturer specifications
   - Look for "Water Heater Schedule", "Plumbing Equipment Schedule"

2. **Plumbing Plans** (high reliability)
   - Water heater location
   - Piping configuration
   - Equipment callouts with specifications
   - Multiple water heater arrangements

3. **Energy notes / Specifications** (medium reliability)
   - UEF/EF efficiency ratings
   - Tank specifications
   - Compliance notes

4. **Floor plans** (supplemental)
   - Water heater location
   - Utility room identification

### 3. Water Heater Identification

Identify all water heaters in the document:

1. **Look for water heater names:**
   - Equipment schedules use names like "WH-1", "WH-01", "HPWH-1"
   - Plumbing plans may show callouts with designations
   - Standardize to consistent naming

2. **Identify water heater type:**
   - Storage (traditional tank water heater)
   - Tankless (on-demand, instantaneous)
   - Heat Pump (HPWH, most efficient)
   - Instantaneous (similar to tankless)

3. **Fuel identification:**
   - Electric Resistance (traditional electric)
   - Natural Gas
   - Heat Pump (uses ambient heat + electricity)

### 4. Performance Data Extraction

For each water heater, extract performance specifications:

**Energy Efficiency:**
- Energy Factor (EF) or Uniform Energy Factor (UEF)
  - UEF is the current standard (replaces EF)
  - Higher = more efficient
  - Storage electric: 0.90-0.95 UEF
  - Heat pump: 2.0-4.0 UEF (very efficient)
  - Gas storage: 0.60-0.70 UEF

**Capacity and Input:**
- Tank volume in gallons (storage types)
- Input rating (heating power)
- Input rating units (watts, Btuh, kW)
- First hour rating (how much hot water in first hour)
- Rated flow (GPM for tankless)
- Recovery efficiency (how efficiently it heats water)

**Insulation:**
- Interior insulation R-value
- Exterior blanket insulation R-value (if added)
- Standby loss (heat lost when idle)

### 5. Installation Details

Extract installation specifications:

**Tank Location:**
- Garage
- Interior (conditioned space)
- Exterior
- Closet
- Basement

Location affects efficiency and compliance (conditioned space is best for heat pump water heaters).

### 6. System Grouping

Group water heaters into systems:

1. **Single water heater system:**
   - Most common for ADUs
   - One WaterHeatingSystem with one WaterHeater

2. **Multiple water heater system:**
   - Multiple units serving one building
   - May have primary + backup configuration
   - Create one WaterHeatingSystem with multiple WaterHeaters in array

3. **Point-of-use systems:**
   - Small tankless units at specific fixtures
   - May be separate systems or part of central system

### 7. Naming Conventions for Deduplication

Use consistent naming across extraction:

- **System name:** Use equipment schedule system name
- **Water heater name:** Use identifier from schedule (WH-1, HPWH-1)
- **Format:** "[Type] - [Location/Zone]" if creating names

Examples:
- System: "DHW System 1"
- Water heater: "WH-1", "HPWH-Living", "Tankless-Bath"

### 8. JSON Output Format

Return JSON matching this structure:

```json
{
  "water_heating_systems": [
    {
      "name": "DHW System 1",
      "status": "New",
      "system_type": "Central",
      "water_heaters": [
        {
          "name": "WH-1",
          "fuel": "Heat Pump",
          "tank_type": "Heat Pump",
          "volume": 50.0,
          "energy_factor": 3.5,
          "input_rating": 4500,
          "input_rating_units": "watts",
          "interior_insulation_r_value": 16.0,
          "exterior_insulation_r_value": null,
          "standby_loss": 45.0,
          "tank_location": "Garage",
          "rated_flow": null,
          "first_hour_rating": 67.0,
          "recovery_efficiency": 0.95
        }
      ]
    }
  ],
  "notes": "Single heat pump water heater extracted from equipment schedule (high confidence). UEF=3.5 from equipment schedule. Location=Garage from plumbing plan."
}
```

## Error Handling

### Common Extraction Issues

1. **EF vs UEF confusion:**
   - UEF is current standard (2017+)
   - EF was previous standard (similar but not identical)
   - Note which standard is shown
   - Prefer UEF if both present

2. **Tank type ambiguity:**
   - "Electric" could be resistance or heat pump
   - Check efficiency: UEF > 1.5 = likely heat pump
   - Look for "HPWH" or "Heat Pump Water Heater" labels

3. **Tankless sizing:**
   - No volume (0 or null)
   - Has rated flow (GPM)
   - Input rating typically high (100,000+ Btuh for gas)

4. **Missing fields:**
   - Many fields are optional
   - Use null for genuinely missing data
   - Don't guess or infer critical values

5. **Conflicting values:**
   - Use equipment schedule value (most authoritative)
   - Note conflict in extraction notes
   - Example: "UEF shows 3.2 on plumbing plan but 3.5 on schedule. Using schedule value 3.5."

### Validation Checks

Before returning extracted data:
- [ ] Each water heater has unique name
- [ ] fuel is valid: "Electric Resistance", "Natural Gas", "Heat Pump"
- [ ] tank_type is valid: "Storage", "Tankless", "Heat Pump", "Instantaneous"
- [ ] Efficiency ratings in reasonable ranges:
  - Electric resistance storage: 0.90-0.99 UEF
  - Heat pump: 1.5-4.5 UEF
  - Gas storage: 0.50-0.80 UEF
  - Tankless gas: 0.75-0.99 UEF
- [ ] volume in gallons (0 or null for tankless)
- [ ] input_rating_units specified if input_rating provided
- [ ] status is valid (New, Existing, Altered)

## Cross-Referencing Strategy

To improve accuracy, cross-reference values between pages:

- **Efficiency rating:** Equipment schedule values are authoritative
- **Tank volume:** Should match between schedule and plumbing plan
- **Fuel type:** Should align with input rating units (watts = electric, Btuh often = gas)
- **Location:** Cross-reference plumbing plan with schedules

If cross-reference reveals discrepancy, prefer equipment schedule value and note discrepancy.

## Confidence Reporting

Include extraction `notes` with confidence indicators:

**High confidence:** Value from equipment schedule, clearly legible
**Medium confidence:** Value from plumbing plan callouts, value is clear
**Low confidence:** Value inferred from system type or incomplete data

Example notes:
```
"notes": "HPWH-1 extracted from equipment schedule (high confidence). UEF=3.5 from schedule. Volume=50 gal from schedule (high confidence). Tank location=Garage from plumbing plan (medium confidence). First hour rating estimated from capacity (low confidence)."
```

## Next Steps After Extraction

The extracted JSON will be:
1. Saved to iteration directory
2. Passed to verifier agent for comparison against ground truth
3. Used to generate discrepancy reports
4. Fed back into self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all DHW fields.
