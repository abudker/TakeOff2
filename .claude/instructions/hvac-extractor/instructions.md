# HVAC Extractor Instructions

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

The HVAC extractor extracts heating, ventilation, and air conditioning system data from Title 24 compliance documentation. HVAC systems include heat pumps, furnaces, air conditioners, package units, and ductless mini-splits, along with their distribution systems (ductwork).

## Extraction Workflow

### 1. Input Reception

You will receive:
- **Page images:** List of PNG file paths from preprocessing phase
- **DocumentMap JSON:** Document structure analysis from discovery phase

The DocumentMap identifies key page categories:
- `schedule_pages`: Equipment schedules (RTU, heat pump, furnace schedules)
- `drawing_pages`: Mechanical plans, one-line diagrams
- `other`: Cover pages, notes, specifications

**NOTE:** CBECC-Res compliance forms are NOT typically included in architectural plan sets. The source documents are architectural PDFs (floor plans, schedules, title blocks). Do not expect to find CBECC pages.

### 2. Page Prioritization

Focus extraction efforts on these page types (in order of reliability):

1. **Equipment Schedules** (highest reliability)
   - RTU Schedule, Heat Pump Schedule, Furnace Schedule
   - Contains model numbers, capacities, efficiency ratings
   - May have manufacturer specifications
   - Look for "HVAC Equipment Schedule", "Mechanical Schedule"

2. **Mechanical Plans / One-Line Diagrams** (high reliability)
   - System layouts and zone connections
   - Equipment locations
   - Duct routing information
   - Equipment callouts with specifications

3. **Energy notes / Specifications** (medium reliability)
   - HSPF, SEER2 efficiency ratings
   - System type requirements
   - Compliance notes

4. **Floor plans** (supplemental)
   - Equipment locations
   - Zone assignments
   - Duct routing visibility

### 3. System Identification

Identify all HVAC systems in the document:

1. **Look for system names:**
   - Equipment schedules use names like "HP-1", "RTU-1", "AHU-1"
   - Mechanical plans may show callouts with system designations
   - Standardize to consistent naming

2. **Identify system type:**
   - Heat Pump (air-source, most common for residential)
   - Furnace (gas or electric)
   - Split System (separate outdoor condenser and indoor air handler)
   - Package Unit (all-in-one rooftop or ground unit)
   - Ductless (mini-split, often multi-zone)

3. **Zone assignments:**
   - Note which zones each system serves
   - Some buildings have multiple systems serving different areas
   - Check mechanical plans or notes for zone assignments

### 4. Heating System Extraction

For each HVAC system, extract heating performance data:

**Heat Pump Heating:**
- System type (SplitHeatPump, PackagedHeatPump, MSHP)
- HSPF or HSPF2 rating (typical 8-10 for Title 24 compliance)
- Capacity at 47F (standard rating point) in Btuh
- Capacity at 17F (cold temperature rating) in Btuh
- Auxiliary heating capacity (backup electric strip) in Btuh
- Ducted vs ductless

**Furnace Heating:**
- Fuel type (gas, electric)
- AFUE rating (typical 80-98%)
- Input and output capacity in Btuh
- May not have heat pump fields (use null)

### 5. Cooling System Extraction

For each HVAC system, extract cooling performance data:

**Air Conditioner / Heat Pump Cooling:**
- System type (matches heating for heat pumps)
- SEER2 rating (new standard, typical 14-20)
- EER2 rating (at 95F, for compliance)
- CFM per ton (airflow per ton cooling, typical 350-450)
- AC charge verification status (Factory charge, Field charge verified, etc.)
- Ducted vs ductless

**Note on SEER vs SEER2:**
- SEER2 is the new standard (2023+)
- Older documents may show SEER (convert: SEER2 ~ SEER * 0.95)
- Prefer SEER2 if both shown

### 6. Distribution System Extraction

For each HVAC system, extract duct/distribution data:

**Duct System Properties:**
- System name (matches HVAC system name or "Ducts - Zone 1")
- Duct location type:
  - DuctsInAll (ducts in all zones)
  - DuctsInConditioned (ducts only in conditioned space - best)
  - DuctsInAttic (unconditioned attic)
  - DuctsInGarage (garage)
- Duct leakage percentage (typical 4-15%, lower is better)
- Duct insulation R-value (R-6 to R-8 typical)
- Supply duct area (sq ft) and diameter (inches)
- Return duct area (sq ft) and diameter (inches)
- Bypass duct present (for certain systems)

**For Ductless Systems:**
- Distribution may be null or minimal
- Mini-splits have no ductwork
- Note "Ductless" in system type

### 7. Linking HVAC to Zones

Connect systems to thermal zones:

1. **CBECC zone assignments:**
   - Look for "Zone: Living Zone" or "Serves: Zone 1"
   - Multiple zones may share one system
   - Or multiple systems may serve one zone (zoned system)

2. **Equipment schedule notes:**
   - May indicate "Serves: All Conditioned" or specific areas

3. **Mechanical plans:**
   - Show duct runs to different rooms/zones

### 8. Naming Conventions for Deduplication

Use consistent naming across extraction:

- **Primary name:** Use CBECC system name if available
- **Fallback:** Equipment schedule designation (HP-1, RTU-1)
- **Format:** "[Type] - [Zone/Area]" if creating names

Examples:
- "Heat Pump - Living Zone"
- "HP-1"
- "HVAC System 1"
- "Mini Split - Bedrooms"

### 9. JSON Output Format

Return JSON matching this structure:

```json
{
  "hvac_systems": [
    {
      "name": "Heat Pump - Living Zone",
      "status": "New",
      "system_type": "Heat Pump",
      "heating": {
        "system_type": "SplitHeatPump",
        "hspf": 9.5,
        "capacity_47": 36000,
        "capacity_17": 21000,
        "auxiliary_heating_capacity": 10000,
        "ducted": true
      },
      "cooling": {
        "system_type": "SplitHeatPump",
        "seer2": 16.0,
        "eer2": 12.5,
        "cfm_per_ton": 400,
        "ac_charge": "Field charge verified",
        "ducted": true
      },
      "distribution": {
        "name": "Ducts - Living Zone",
        "system_type": "DuctsInConditioned",
        "percent_leakage": 4.0,
        "insulation_r_value": 6.0,
        "supply_area": 200.0,
        "supply_diameter": 8.0,
        "return_area": 100.0,
        "return_diameter": 14.0,
        "bypass_duct": false
      }
    }
  ],
  "notes": "Single heat pump system extracted from CBECC mechanical summary (high confidence). SEER2=16.0 and HSPF=9.5 from equipment schedule. Duct leakage 4% from compliance form."
}
```

## Error Handling

### Common Extraction Issues

1. **Multiple systems:**
   - Create separate HVACSystem objects for each
   - Ensure unique names
   - Don't merge different systems

2. **Missing heating or cooling:**
   - Heat-only systems: cooling = null
   - Cool-only systems: heating = null
   - Note in extraction notes

3. **SEER vs SEER2 confusion:**
   - Check document date for standard version
   - 2022+ Title 24 uses SEER2
   - Note if conversion was applied

4. **Ductless systems:**
   - distribution may be null
   - system_type = "Ductless"
   - May have multiple indoor units (capacity adds up)

5. **Conflicting values:**
   - Use CBECC value if available (most authoritative)
   - Note conflict in extraction notes
   - Example: "SEER2 shows 15 on schedule but 16 on CBECC. Using 16."

### Validation Checks

Before returning extracted data:
- [ ] Each system has unique name
- [ ] system_type is valid enum (Heat Pump, Furnace, Split System, Package Unit, Ductless, Other)
- [ ] Efficiency ratings in reasonable ranges:
  - HSPF: 7.5-13
  - SEER2: 13-25
  - EER2: 9-20
  - CFM/ton: 300-500
- [ ] Capacities in Btuh (not tons - multiply tons by 12000)
- [ ] Duct leakage as percentage (4-15% typical, not decimal)
- [ ] status is valid (New, Existing, Altered)

## Cross-Referencing Strategy

To improve accuracy, cross-reference values between pages:

- **Capacity:** Should match between CBECC, equipment schedule, and mechanical plan
- **Efficiency ratings:** CBECC should match equipment schedule
- **Duct leakage:** CBECC compliance section should match CF1R
- **System type:** Should be consistent across all references

If cross-reference reveals discrepancy, prefer CBECC value and note discrepancy.

## Confidence Reporting

Include extraction `notes` with confidence indicators:

**High confidence:** Value from CBECC mechanical summary, clearly legible
**Medium confidence:** Value from equipment schedule, value is clear
**Low confidence:** Value inferred from mechanical plan or incomplete data

Example notes:
```
"notes": "HP-1 extracted from CBECC page 5 (high confidence). SEER2=16.0 from CBECC. HSPF=9.5 area-weighted from schedule (medium confidence). Duct leakage 4% from CF1R-MCH (high confidence). Auxiliary heating capacity estimated from system size (low confidence, verify)."
```

## Next Steps After Extraction

The extracted JSON will be:
1. Saved to iteration directory
2. Passed to verifier agent for comparison against ground truth
3. Used to generate discrepancy reports
4. Fed back into self-improvement loop

Extraction accuracy target: F1 >= 0.90 across all HVAC fields.
