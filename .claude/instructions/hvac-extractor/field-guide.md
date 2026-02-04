# HVAC Extractor Field Guide

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

This guide maps each HVACSystem, HeatPumpHeating, HeatPumpCooling, and DistributionSystem schema field to its source location in Title 24 compliance documents. Use this as a reference during extraction to know where to look for each field.

---

## HVACSystem Fields

### name
**Type:** string (required)
**Description:** HVAC system identifier

**Document sources:**
1. **Equipment schedule:** Row identifier (HP-1, RTU-1, AHU-1) (PRIMARY SOURCE)
2. **Mechanical plans:** Equipment tags and labels
3. **Floor plans:** HVAC equipment location and labels

**Extraction tips:**
- Use equipment schedule names (e.g., "HP-01", "RTU-1")
- Keep names consistent across heating/cooling/distribution
- For ductless: "Mini Split - [Area]" or "MSHP-1"

**Example values:**
- "HVAC System 1"
- "Heat Pump - Living Zone"
- "HP-01"
- "Ductless Mini Split"

---

### status
**Type:** enum ["New", "Existing", "Altered"] (optional)
**Description:** Component status for additions/alterations

**Document sources:**
1. **Project scope:** New construction vs alteration (PRIMARY SOURCE)
2. **Equipment schedule:** Status column if present
3. **General notes:** Scope of work

**Extraction tips:**
- Default to "New" for new construction projects
- Look for "Existing" or "Altered" in addition/alteration projects
- Check run_scope from ProjectInfo for context
- If not specified, infer from project scope

**Example values:**
- "New" (typical for new construction)
- "Existing" (existing equipment being retained)
- "Altered" (existing equipment being modified)

---

### system_type
**Type:** enum ["Heat Pump", "Furnace", "Split System", "Package Unit", "Ductless", "Other"]
**Description:** Primary HVAC system type

**Document sources:**
1. **Equipment schedule:** Type column or equipment description (PRIMARY SOURCE)
2. **Mechanical plans:** Equipment callouts
3. **Model number:** Can indicate type (e.g., XR15 = heat pump)
4. **Energy notes:** System type requirements

**Extraction tips:**
- Heat Pump: Provides both heating and cooling (air-source most common)
- Furnace: Gas or electric heating only (may have separate AC)
- Split System: Separate outdoor condenser and indoor air handler
- Package Unit: All-in-one rooftop or ground unit
- Ductless: Mini-split system (single or multi-zone)
- Use "Other" for unusual systems (geothermal, etc.)

**Determining type from clues:**
- "ASHP" = Air Source Heat Pump -> "Heat Pump"
- "Gas Furnace + AC" -> "Split System" or "Furnace" (depending on focus)
- "Packaged Heat Pump" -> "Package Unit" or "Heat Pump"
- "MSHP" or "Mini Split" -> "Ductless"
- "RTU" = Rooftop Unit -> "Package Unit"

**California Title 24 context:**
- Heat pumps required for most new residential (2023+ code)
- Ductless mini-splits popular for ADUs
- Gas furnaces still common in alterations

---

## HeatPumpHeating Fields

### system_type
**Type:** string (optional)
**Description:** Heating system sub-type

**Document sources:**
1. **Equipment schedule:** Heat pump model classification (PRIMARY SOURCE)
2. **Mechanical plans:** Equipment type designation
3. **Specifications:** Heating equipment type

**Extraction tips:**
- Match cooling system_type for heat pumps
- Common values: "SplitHeatPump", "PackagedHeatPump", "MSHP" (mini-split)
- For furnaces: "GasFurnace", "ElectricFurnace"
- CBECC may use abbreviations

**Example values:**
- "SplitHeatPump"
- "PackagedHeatPump"
- "MSHP" (Mini-Split Heat Pump)
- "GasFurnace"
- "ElectricResistance"

---

### hspf
**Type:** float (optional)
**Description:** Heating Seasonal Performance Factor

**Document sources:**
1. **Equipment schedule:** HSPF or HSPF2 column (PRIMARY SOURCE)
2. **Manufacturer specs:** Product data sheet
3. **Energy notes:** Efficiency requirements

**Extraction tips:**
- HSPF = Heating efficiency for heat pumps
- HSPF2 is newer standard (2023+), similar values
- Typical range: 8.0-10.0 for Title 24 compliance
- Higher = more efficient (minimum 8.8 HSPF2 for 2022 Title 24)
- Gas furnaces use AFUE instead (not HSPF)

**California Title 24 typical values:**
- Code minimum (2022): 8.8 HSPF2
- Good: 9.0-9.5 HSPF
- Excellent: 10.0+ HSPF

**Example values:**
- 9.5
- 8.8
- 10.2

---

### capacity_47
**Type:** float (optional)
**Description:** Heating capacity at 47F outdoor temperature (Btuh)

**Document sources:**
1. **Equipment schedule:** Heating capacity column (PRIMARY SOURCE)
2. **Manufacturer specs:** Rating at standard conditions
3. **Mechanical plans:** Equipment callout with capacity

**Extraction tips:**
- 47F is the standard rating point for heat pumps
- Units: Btuh (BTU per hour)
- If shown in tons, multiply by 12000 (1 ton = 12000 Btuh)
- Typical ADU range: 18,000-48,000 Btuh (1.5-4 tons)
- May be labeled "Nominal Heating Capacity"

**Unit conversions:**
- 1 ton = 12,000 Btuh
- 2 tons = 24,000 Btuh
- 3 tons = 36,000 Btuh

**Example values:**
- 36000 (3-ton system)
- 24000 (2-ton system)
- 48000 (4-ton system)

---

### capacity_17
**Type:** float (optional)
**Description:** Heating capacity at 17F outdoor temperature (Btuh)

**Document sources:**
1. **Equipment schedule:** Low temperature rating column (PRIMARY SOURCE)
2. **Manufacturer specs:** Cold climate rating
3. **Specifications:** Extended capacity data

**Extraction tips:**
- 17F is the cold temperature rating point
- Always less than capacity_47 (heat pump efficiency drops in cold)
- Typically 50-70% of capacity_47
- May not be listed for mild California climates
- Important for Climate Zone 16 (mountain areas)

**Typical relationship:**
- capacity_17 ~ 0.55-0.70 * capacity_47
- If missing, can estimate but note low confidence

**Example values:**
- 21000 (for 36000 Btuh @ 47F system)
- 14000 (for 24000 Btuh @ 47F system)

---

### auxiliary_heating_capacity
**Type:** float (optional)
**Description:** Backup electric strip heating capacity (Btuh)

**Document sources:**
1. **Equipment schedule:** Strip heat or electric backup rating (PRIMARY SOURCE)
2. **Model specifications:** Built-in backup heater size
3. **Electrical panel schedule:** Backup heater circuit

**Extraction tips:**
- Electric resistance backup for cold temperatures
- Common in heat pump systems for defrost and cold snaps
- Units: Btuh
- May also show in kW (multiply by 3412 for Btuh)
- Many California heat pumps have minimal or no aux heat (mild climate)

**Unit conversions:**
- 1 kW = 3,412 Btuh
- 5 kW = 17,060 Btuh
- 10 kW = 34,120 Btuh

**Example values:**
- 10000 (small backup)
- 17000 (5 kW strip)
- 0 or null (no auxiliary heat)

---

### ducted
**Type:** boolean (optional)
**Description:** Whether heating is delivered through ductwork

**Document sources:**
1. **Mechanical plans:** Presence of duct runs (PRIMARY SOURCE)
2. **Equipment schedule:** Ductless vs ducted notation
3. **System type:** Infer from equipment type

**Extraction tips:**
- true = Central ducted system
- false = Ductless (mini-split, baseboard)
- Infer from system_type if not explicit:
  - Mini-split, MSHP, Ductless = false
  - Split system, Package unit, Furnace = typically true

**Example values:**
- true (standard ducted system)
- false (mini-split or ductless)

---

## HeatPumpCooling Fields

### system_type
**Type:** string (optional)
**Description:** Cooling system sub-type

**Document sources:**
Same as HeatPumpHeating system_type

**Extraction tips:**
- Should match heating system_type for heat pumps
- For AC-only, may be "SplitAC", "PackagedAC"
- Common values match heating types

---

### seer2
**Type:** float (optional)
**Description:** Seasonal Energy Efficiency Ratio (new standard)

**Document sources:**
1. **Equipment schedule:** SEER2 column (or SEER for older docs) (PRIMARY SOURCE)
2. **AHRI certification:** Product efficiency rating
3. **Energy notes:** Efficiency requirements

**Extraction tips:**
- SEER2 is the current standard (2023+)
- Older documents may show SEER (SEER2 ~ SEER * 0.95)
- Typical range: 14-20 for Title 24 compliance
- Higher = more efficient (minimum 14.3 SEER2 for 2022 Title 24)
- SEER applies to split systems and packaged units

**California Title 24 typical values:**
- Code minimum (2022): 14.3 SEER2
- Good: 15-16 SEER2
- Excellent: 18+ SEER2

**Example values:**
- 16.0
- 14.5
- 20.0

---

### eer2
**Type:** float (optional)
**Description:** Energy Efficiency Ratio at 95F (new standard)

**Document sources:**
1. **Equipment schedule:** EER2 column (PRIMARY SOURCE)
2. **Manufacturer specs:** Product data sheet
3. **AHRI certification:** Efficiency rating

**Extraction tips:**
- EER2 is efficiency at peak conditions (95F)
- Used for compliance calculations
- Typical range: 9-16
- Relationship: EER2 ~ SEER2 * 0.75-0.85 approximately
- May not always be listed; estimate if needed

**California Title 24 typical values:**
- Minimum: ~11 EER2
- Good: 12-13 EER2
- Excellent: 14+ EER2

**Example values:**
- 12.5
- 11.0
- 13.8

---

### cfm_per_ton
**Type:** float (optional)
**Description:** Airflow per ton of cooling capacity

**Document sources:**
1. **Equipment schedule:** Airflow rating (PRIMARY SOURCE)
2. **Mechanical plans:** Airflow specifications
3. **Commissioning report:** Measured airflow (if available)

**Extraction tips:**
- CFM = Cubic Feet per Minute
- Standard design: 400 CFM/ton
- Acceptable range: 350-450 CFM/ton
- Lower values reduce efficiency, higher may cause issues
- May need to calculate: Total CFM / Tons

**Calculation if needed:**
- 1200 CFM for 3-ton system = 400 CFM/ton
- 1000 CFM for 2.5-ton system = 400 CFM/ton

**Example values:**
- 400 (standard)
- 350 (low, but acceptable)
- 450 (high airflow)

---

### ac_charge
**Type:** string (optional)
**Description:** Refrigerant charge verification status

**Document sources:**
1. **Equipment schedule:** Charge verification notes (PRIMARY SOURCE)
2. **Specifications:** Installation requirements
3. **Energy notes:** Verification requirements

**Extraction tips:**
- Title 24 requires charge verification for new systems
- Common values:
  - "Factory charge" (pre-charged unit)
  - "Field charge verified" (checked by technician)
  - "Weigh-in method" (measured refrigerant)
  - "Superheat/subcooling method" (temperature-based verification)
- Important for compliance credit

**Example values:**
- "Field charge verified"
- "Factory charge"
- "Weigh-in method"
- "Not verified"

---

### ducted
**Type:** boolean (optional)
**Description:** Whether cooling is delivered through ductwork

Same as HeatPumpHeating ducted field. Should match for heat pump systems.

---

## DistributionSystem Fields

### name
**Type:** string (required)
**Description:** Distribution system identifier

**Document sources:**
1. **Mechanical plans:** Duct system designation (PRIMARY SOURCE)
2. **Equipment schedule:** Distribution system name
3. **Floor plans:** Duct routing

**Extraction tips:**
- May match HVAC system name or be separate
- Common patterns: "Ducts - Zone 1", "Distribution 1", "DS-1"
- Use HVAC system name if not separately named

**Example values:**
- "Ducts - Living Zone"
- "Distribution System 1"
- "HP-1 Ducts"

---

### system_type
**Type:** string (optional)
**Description:** Duct location/configuration type

**Document sources:**
1. **Mechanical plans:** Duct routing through building (PRIMARY SOURCE)
2. **Section drawings:** Duct location visible
3. **Equipment schedule:** Distribution type notes

**Extraction tips:**
- Indicates where ducts are located
- Major impact on efficiency (conditioned space best)
- Common CBECC values:
  - "DuctsInConditioned" - Best (ducts in conditioned space)
  - "DuctsInAttic" - Unconditioned attic (common, less efficient)
  - "DuctsInGarage" - Unconditioned garage
  - "DuctsInAll" - Ducts throughout (mixed locations)
  - "Ductless" - No duct system (mini-splits)

**California Title 24 notes:**
- DuctsInConditioned gets compliance credit
- Attic ducts require higher insulation
- ADUs often have DuctsInConditioned (compact space)

**Example values:**
- "DuctsInConditioned"
- "DuctsInAttic"
- "DuctsInGarage"
- "Ductless"

---

### percent_leakage
**Type:** float (optional)
**Description:** Duct leakage as percentage of system airflow

**Document sources:**
1. **Duct test report:** Measured leakage (if available)
2. **Energy notes:** Leakage requirements
3. **Specifications:** Duct sealing standards

**Extraction tips:**
- Express as percentage (not decimal): 4% not 0.04
- Typical range: 4-15%
- Lower is better (less air loss)
- Title 24 2022 requires testing for credit
- Default assumptions: 6% verified, 15% unverified

**California Title 24 thresholds:**
- Excellent: <= 4%
- Good: 4-6%
- Acceptable: 6-10%
- Poor: > 10%

**Example values:**
- 4.0 (well-sealed, tested)
- 6.0 (standard verified)
- 15.0 (default unverified)

---

### insulation_r_value
**Type:** float (optional)
**Description:** Duct insulation R-value

**Document sources:**
1. **Mechanical specifications:** Duct insulation notes (PRIMARY SOURCE)
2. **Energy notes:** Insulation requirements
3. **Equipment schedule:** Duct insulation R-value

**Extraction tips:**
- R-value measures thermal resistance
- Higher = better insulation
- Title 24 minimum varies by duct location:
  - Ducts in unconditioned space: R-6 to R-8 required
  - Ducts in conditioned space: May be uninsulated
- Common values: R-4.2, R-6, R-8

**California Title 24 minimums:**
- Attic ducts: R-8
- Garage ducts: R-6
- Conditioned space: R-4.2 or none required

**Example values:**
- 6.0 (R-6)
- 8.0 (R-8)
- 4.2 (R-4.2 minimum)

---

### supply_area
**Type:** float (optional)
**Description:** Total supply duct surface area (sq ft)

**Document sources:**
1. **Mechanical calculations:** Duct surface area takeoff (PRIMARY SOURCE)
2. **Duct design report:** Supply system sizing
3. **Mechanical plans:** Duct dimensions for calculation

**Extraction tips:**
- Surface area of supply ducts (delivers conditioned air to rooms)
- Units: square feet
- Used for heat loss/gain calculations
- May need to calculate from duct dimensions
- Typical ADU: 100-300 sq ft supply duct area

**Example values:**
- 200.0 sq ft
- 150.0 sq ft
- 300.0 sq ft

---

### supply_diameter
**Type:** float (optional)
**Description:** Representative supply duct diameter (inches)

**Document sources:**
1. **Mechanical plans:** Duct sizing annotations (PRIMARY SOURCE)
2. **Equipment schedule:** Duct connections
3. **Duct layout drawings:** Size callouts

**Extraction tips:**
- Round duct diameter in inches
- For rectangular ducts, use equivalent diameter
- Typical residential: 6", 8", 10" branches; 10"-14" trunk
- May be weighted average if multiple sizes

**Common sizes:**
- Branch ducts: 6" or 8"
- Trunk lines: 10", 12", or 14"
- ADU supply: typically 6"-10"

**Example values:**
- 8.0 (8-inch typical)
- 10.0 (larger system)
- 6.0 (smaller branches)

---

### return_area
**Type:** float (optional)
**Description:** Total return duct surface area (sq ft)

**Document sources:**
1. **Mechanical calculations:** Return system takeoff (PRIMARY SOURCE)
2. **Duct design report:** Return sizing
3. **Mechanical plans:** Return duct dimensions

**Extraction tips:**
- Surface area of return ducts (brings air back to unit)
- Usually smaller than supply area
- Units: square feet
- Typical: 50-70% of supply area

**Example values:**
- 100.0 sq ft
- 75.0 sq ft
- 150.0 sq ft

---

### return_diameter
**Type:** float (optional)
**Description:** Representative return duct diameter (inches)

**Document sources:**
1. **Mechanical plans:** Return duct annotations (PRIMARY SOURCE)
2. **Equipment specifications:** Return plenum size
3. **Duct layout drawings:** Size callouts

**Extraction tips:**
- Return ducts are typically larger than supply (lower velocity)
- Typical residential: 12"-20" return
- May have single large return or multiple smaller returns
- ADU: typically 14"-18" return

**Common sizes:**
- Small system: 12"-14"
- Medium system: 14"-16"
- Large system: 16"-20"

**Example values:**
- 14.0 (14-inch)
- 16.0 (larger system)
- 12.0 (compact system)

---

### bypass_duct
**Type:** boolean (optional)
**Description:** Whether system has a bypass duct

**Document sources:**
1. **Mechanical plans:** Bypass duct shown (PRIMARY SOURCE)
2. **Equipment schedule:** Bypass damper noted
3. **Duct layout drawings:** Bypass routing

**Extraction tips:**
- Bypass ducts relieve pressure when zones close
- Common in zoned systems
- May be labeled "bypass damper" or "relief duct"
- If not mentioned, assume false

**Example values:**
- true (zoned system with bypass)
- false (no bypass, typical for single-zone)

---

## Field Summary Table

| Model | Field | Type | Sources | Can be null? |
|-------|-------|------|---------|--------------|
| HVACSystem | name | string | Equipment schedule | No |
| HVACSystem | status | enum | Project scope | Yes |
| HVACSystem | system_type | enum | Equipment schedule | Yes |
| HVACSystem | heating | HeatPumpHeating | Equipment schedule | Yes |
| HVACSystem | cooling | HeatPumpCooling | Equipment schedule | Yes |
| HVACSystem | distribution | DistributionSystem | Mechanical plans | Yes |
| HeatPumpHeating | system_type | string | Equipment schedule | Yes |
| HeatPumpHeating | hspf | float | Equipment schedule | Yes |
| HeatPumpHeating | capacity_47 | float | Equipment schedule | Yes |
| HeatPumpHeating | capacity_17 | float | Equipment schedule | Yes |
| HeatPumpHeating | auxiliary_heating_capacity | float | Equipment schedule | Yes |
| HeatPumpHeating | ducted | boolean | Mechanical plans | Yes |
| HeatPumpCooling | system_type | string | Equipment schedule | Yes |
| HeatPumpCooling | seer2 | float | Equipment schedule | Yes |
| HeatPumpCooling | eer2 | float | Equipment schedule | Yes |
| HeatPumpCooling | cfm_per_ton | float | Equipment schedule | Yes |
| HeatPumpCooling | ac_charge | string | Specifications | Yes |
| HeatPumpCooling | ducted | boolean | Mechanical plans | Yes |
| DistributionSystem | name | string | Mechanical plans | No |
| DistributionSystem | system_type | string | Mechanical plans | Yes |
| DistributionSystem | percent_leakage | float | Test results | Yes |
| DistributionSystem | insulation_r_value | float | Specifications | Yes |
| DistributionSystem | supply_area | float | Mechanical calcs | Yes |
| DistributionSystem | supply_diameter | float | Mechanical plans | Yes |
| DistributionSystem | return_area | float | Mechanical calcs | Yes |
| DistributionSystem | return_diameter | float | Mechanical plans | Yes |
| DistributionSystem | bypass_duct | boolean | Mechanical plans | Yes |

**Total fields:** 27 (2 required + 25 optional)

---

## Extraction Best Practices

### Page Reading Order
1. Start with Equipment schedules (system specs, efficiency ratings)
2. Check Mechanical plans (system layout, duct routing)
3. Use Energy notes/specifications for missing values
4. Reference Floor plans for equipment locations

### Common Document Layouts

**Equipment Schedule:**
- Columns: Mark, Type, Model, Capacity, SEER2, HSPF, Voltage
- One row per unit
- May have separate heating and cooling schedules

**Mechanical Plans:**
- Equipment locations and callouts
- Duct routing and sizing
- Zone connections
- System designations

### Quality Checks

Before finalizing extraction:
- [ ] All HVAC systems have unique names
- [ ] system_type is valid enum value
- [ ] Efficiency ratings in reasonable ranges (HSPF 7.5-13, SEER2 13-25)
- [ ] Capacities in Btuh (not tons)
- [ ] Duct leakage as percentage (not decimal)
- [ ] heating and cooling system_type match for heat pumps
- [ ] ducted field matches distribution system_type

### Confidence Scoring

Document extraction confidence in notes:

**High confidence indicators:**
- Value from equipment schedule, clearly legible
- Cross-referenced across multiple pages with agreement
- Standard format with clear units

**Medium confidence indicators:**
- Value from mechanical plan callouts
- Legible but some interpretation needed
- Unit conversion applied

**Low confidence indicators:**
- Inferred from system size or type
- Hand-written value, OCR uncertain
- Conflict between pages, used best judgment

Include specific notes for low-confidence fields so verifier can double-check.

---

*End of HVAC Field Guide*
