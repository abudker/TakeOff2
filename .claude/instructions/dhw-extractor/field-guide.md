# DHW Extractor Field Guide

**Version:** v1.0.0
**Last updated:** 2026-02-04

## Overview

This guide maps each WaterHeatingSystem and WaterHeater schema field to its source location in Title 24 compliance documents. Use this as a reference during extraction to know where to look for each field.

---

## WaterHeatingSystem Fields

### name
**Type:** string (required)
**Description:** Water heating system identifier

**Document sources:**
1. **CBECC-Res output:** "Water Heating" or "DHW System" section header
2. **Equipment schedule:** System designation
3. **CF1R-PLB:** System identifier
4. **Plumbing plans:** System labels

**Extraction tips:**
- Use CBECC name if available (e.g., "DHW System 1", "Water Heating")
- Equipment schedules may use "DHW-1", "WH System"
- For single water heater, system name often matches heater name
- Keep names consistent with water heater naming

**Example values:**
- "DHW System 1"
- "Water Heating - ADU"
- "Central DHW"

---

### status
**Type:** enum ["New", "Existing", "Altered"] (optional)
**Description:** Component status for additions/alterations

**Document sources:**
1. **CBECC-Res output:** Status column or notation
2. **CF1R form:** Component status section
3. **Equipment schedule:** Status column if present

**Extraction tips:**
- Default to "New" for new construction projects
- Look for "Existing" or "Altered" in addition/alteration projects
- Check run_scope from ProjectInfo for context
- If not specified, infer from project scope

**Example values:**
- "New" (typical for new construction)
- "Existing" (existing water heater being retained)
- "Altered" (existing equipment being modified)

---

### system_type
**Type:** string (optional)
**Description:** Water heating system configuration type

**Document sources:**
1. **CBECC-Res output:** System type or configuration
2. **CF1R-PLB:** System type field
3. **Plumbing plans:** System layout

**Extraction tips:**
- Common values:
  - "Central" - Single system serving whole building
  - "Point of use" - Small units at individual fixtures
  - "Distributed" - Multiple units throughout building
  - "Recirculation" - System with recirculating pump
- Most ADUs use "Central" with single water heater

**Example values:**
- "Central"
- "Point of use"
- "Distributed"

---

## WaterHeater Fields

### name
**Type:** string (required)
**Description:** Water heater identifier

**Document sources:**
1. **CBECC-Res output:** Water heater name in DHW section
2. **Equipment schedule:** Row identifier (WH-1, HPWH-1)
3. **Plumbing plans:** Equipment tags and labels
4. **Model number:** May serve as identifier

**Extraction tips:**
- Use CBECC name if available (e.g., "Water Heater 1")
- Equipment schedules use codes like "WH-01", "HPWH-1"
- For heat pump water heaters: "HPWH-1" or "Heat Pump WH"
- Keep names unique across all water heaters

**Example values:**
- "WH-1"
- "HPWH-1"
- "Water Heater - ADU"
- "Tankless WH"

---

### fuel
**Type:** enum ["Electric Resistance", "Natural Gas", "Heat Pump"] (optional)
**Description:** Water heater fuel/energy type

**Document sources:**
1. **CBECC-Res output:** "Fuel Type" or type designation
2. **Equipment schedule:** Fuel column
3. **CF1R-PLB:** Water heater type
4. **Model number:** May indicate fuel type

**Extraction tips:**
- "Electric Resistance" = Traditional electric tank
- "Natural Gas" = Gas-fired water heater
- "Heat Pump" = Heat pump water heater (HPWH)
- Electric resistance and heat pump both use electricity but are different technologies
- Heat pump is much more efficient (UEF > 2.0)

**Identifying from clues:**
- UEF > 1.5 = likely "Heat Pump"
- UEF 0.90-0.99 = likely "Electric Resistance"
- Input in Btuh and gas connection = "Natural Gas"
- "HPWH" or "Heat Pump" in name = "Heat Pump"

**California Title 24 context:**
- Heat pump water heaters required for new construction (2023+)
- Electric resistance being phased out for new buildings
- Gas water heaters still common in alterations

**Example values:**
- "Electric Resistance"
- "Natural Gas"
- "Heat Pump"

---

### tank_type
**Type:** enum ["Storage", "Tankless", "Heat Pump", "Instantaneous"] (optional)
**Description:** Water heater tank/system type

**Document sources:**
1. **CBECC-Res output:** Tank type or water heater type
2. **Equipment schedule:** Type column
3. **CF1R-PLB:** Water heater classification
4. **Physical description:** "Tankless" or "Storage" noted

**Extraction tips:**
- "Storage" = Traditional tank with stored hot water
- "Tankless" = On-demand heating, no storage tank
- "Heat Pump" = Uses heat pump technology (also has tank)
- "Instantaneous" = Similar to tankless
- Heat pump water heaters have tanks but use heat pump technology

**Type determination:**
- Has volume > 0 gallons = "Storage" or "Heat Pump"
- No volume + rated flow = "Tankless" or "Instantaneous"
- Heat pump tech + tank = "Heat Pump"

**Example values:**
- "Storage"
- "Tankless"
- "Heat Pump"
- "Instantaneous"

---

### volume
**Type:** float (optional)
**Description:** Tank volume in gallons

**Document sources:**
1. **CBECC-Res output:** "Tank Size" or "Volume"
2. **Equipment schedule:** Capacity/Volume column
3. **CF1R-PLB:** Tank volume field
4. **Model specifications:** Size in model number

**Extraction tips:**
- Units: gallons
- Storage tanks: typically 40-80 gallons residential
- Heat pump water heaters: typically 50-80 gallons
- Tankless: 0 or null (no storage tank)
- ADUs often use 40-50 gallon units

**Typical ranges:**
- Small residential: 30-40 gallons
- Medium residential: 40-50 gallons
- Large residential: 50-80 gallons
- Heat pump: 50-80 gallons (need larger tank)

**Example values:**
- 50.0 (50-gallon tank)
- 40.0 (40-gallon tank)
- 80.0 (large tank)
- null (tankless)

---

### energy_factor
**Type:** float (optional)
**Description:** Energy Factor (EF) or Uniform Energy Factor (UEF)

**Document sources:**
1. **CBECC-Res output:** "EF" or "UEF" in DHW section
2. **Equipment schedule:** Efficiency column
3. **CF1R-PLB:** Efficiency rating field
4. **AHRI certification:** Product efficiency rating

**Extraction tips:**
- UEF is current standard (2017+, replaces EF)
- Higher value = more efficient
- Record whichever value is shown (note EF vs UEF in notes)
- Heat pump water heaters have UEF > 1.0 (energy multiplier effect)
- Gas and electric resistance have UEF < 1.0

**Typical UEF ranges:**
- Electric resistance storage: 0.90-0.99
- Heat pump water heater: 2.0-4.0 (Title 24 requires ~2.0+)
- Gas storage: 0.58-0.70
- Gas tankless: 0.80-0.99
- Excellent heat pump: 3.5+

**California Title 24 minimums:**
- New construction requires high-efficiency water heating
- Heat pump water heaters typically required (2023+ code)
- Minimum UEF varies by tank size

**Example values:**
- 3.5 (excellent heat pump)
- 2.0 (standard heat pump, code minimum)
- 0.93 (electric resistance)
- 0.67 (gas storage)

---

### input_rating
**Type:** float (optional)
**Description:** Input power/capacity rating

**Document sources:**
1. **CBECC-Res output:** "Input Rating" or "Input Capacity"
2. **Equipment schedule:** Input column
3. **Model specifications:** Power rating
4. **Electrical panel schedule:** Circuit amperage (for electric)

**Extraction tips:**
- For electric: typically in watts or kW
- For gas: typically in Btuh (BTU per hour)
- Heat pump element: 4000-5000 watts typical
- Gas water heater: 30,000-75,000 Btuh typical
- Tankless gas: 100,000-200,000 Btuh
- Must specify input_rating_units

**Typical values:**
- Electric storage: 4500 watts
- Heat pump: 4500 watts (backup element)
- Gas storage: 40,000 Btuh
- Tankless gas: 150,000 Btuh

**Example values:**
- 4500 (watts, electric)
- 40000 (Btuh, gas)
- 199000 (Btuh, tankless)

---

### input_rating_units
**Type:** string (optional)
**Description:** Units for input_rating

**Document sources:**
Same as input_rating - units should be noted alongside value

**Extraction tips:**
- Common values:
  - "watts" (electric water heaters)
  - "kW" (kilowatts, electric)
  - "Btuh" (BTU per hour, gas)
  - "MBH" (thousands of Btuh)
- Standardize to lowercase: "watts", "Btuh", "kW"
- Must match input_rating value

**Example values:**
- "watts"
- "Btuh"
- "kW"

---

### interior_insulation_r_value
**Type:** float (optional)
**Description:** Interior tank insulation R-value

**Document sources:**
1. **CBECC-Res output:** Tank insulation field
2. **Equipment schedule:** Insulation column
3. **Product specifications:** Tank R-value
4. **Manufacturer data sheet:** Insulation details

**Extraction tips:**
- R-value measures thermal resistance of insulation
- Higher = better insulated, less standby loss
- Modern water heaters: R-12 to R-24
- Older/budget units: R-6 to R-10
- Heat pump tanks often well-insulated

**Typical values:**
- Budget units: R-6 to R-10
- Standard units: R-12 to R-16
- High-efficiency: R-16 to R-24

**Example values:**
- 16.0 (good insulation)
- 12.0 (standard)
- 24.0 (excellent)

---

### exterior_insulation_r_value
**Type:** float (optional)
**Description:** Added exterior blanket insulation R-value

**Document sources:**
1. **CBECC-Res output:** External insulation specification
2. **Equipment schedule:** Blanket insulation column
3. **Project specifications:** Added insulation details

**Extraction tips:**
- Additional blanket wrap added to tank
- Not always present (especially on new efficient units)
- Common for older tanks or cold locations
- Use null if no external blanket
- R-6 to R-11 typical for blankets

**Example values:**
- 6.0 (standard blanket)
- 11.0 (high R-value blanket)
- null (no blanket)

---

### standby_loss
**Type:** float (optional)
**Description:** Heat loss during standby (Btuh or %/hr)

**Document sources:**
1. **CBECC-Res output:** Standby loss specification
2. **Product specifications:** Standby loss rating
3. **AHRI data:** Standby performance

**Extraction tips:**
- Heat lost when water heater is idle
- May be in Btuh or as percentage per hour
- Lower = more efficient (better insulation)
- Modern units: 30-60 Btuh typical
- Poorly insulated: 100+ Btuh

**Example values:**
- 45.0 (Btuh, well-insulated)
- 80.0 (Btuh, standard)
- 2.5 (%/hr, percentage form)

---

### tank_location
**Type:** string (optional)
**Description:** Physical location of water heater

**Document sources:**
1. **CBECC-Res output:** Location field in DHW section
2. **Plumbing plans:** Equipment location shown
3. **CF1R-PLB:** Location specification
4. **Equipment schedule:** Location column

**Extraction tips:**
- Affects efficiency (conditioned space best for HPWH)
- Common locations:
  - "Garage" (common, unconditioned)
  - "Interior" (conditioned space)
  - "Exterior" (outside, worst for efficiency)
  - "Closet" (interior closet)
  - "Basement" (below-grade)
  - "Utility Room" (interior)
- Heat pump water heaters need air volume (not small closets)

**California Title 24 considerations:**
- Heat pump water heaters perform best in warm locations
- Garage location common but less efficient in cold weather
- Interior location helps efficiency but needs space for air circulation

**Example values:**
- "Garage"
- "Interior"
- "Exterior"
- "Utility Room"

---

### rated_flow
**Type:** float (optional)
**Description:** Rated flow in GPM (tankless units)

**Document sources:**
1. **CBECC-Res output:** Flow rate for tankless
2. **Equipment schedule:** GPM column
3. **Product specifications:** Max flow rate
4. **CF1R-PLB:** Flow capacity

**Extraction tips:**
- Only applicable to tankless/instantaneous units
- Units: GPM (gallons per minute)
- Typical residential: 5-10 GPM
- Higher = can serve more fixtures simultaneously
- null for storage tank water heaters

**Typical ranges:**
- Point of use tankless: 1-3 GPM
- Whole house tankless: 5-10 GPM
- High-capacity: 10+ GPM

**Example values:**
- 7.5 (whole house)
- 9.5 (high-capacity)
- null (storage tank)

---

### first_hour_rating
**Type:** float (optional)
**Description:** First hour delivery rating (gallons)

**Document sources:**
1. **CBECC-Res output:** "FHR" or "First Hour Rating"
2. **Equipment schedule:** FHR column
3. **Product specifications:** First hour capacity
4. **AHRI certification:** FHR rating

**Extraction tips:**
- How much hot water in first hour of use
- Storage tanks only (not tankless)
- Units: gallons
- Should be > tank volume (recovery adds water)
- Typical: 1.1-1.5x tank volume

**Typical ranges:**
- 50-gallon tank: 60-75 FHR
- 80-gallon tank: 80-100 FHR
- Heat pump: may be lower (slower recovery)

**Example values:**
- 67.0 (50-gallon tank)
- 90.0 (80-gallon tank)
- null (tankless)

---

### recovery_efficiency
**Type:** float (optional)
**Description:** Efficiency of heating water (recovery)

**Document sources:**
1. **CBECC-Res output:** Recovery efficiency field
2. **Product specifications:** RE rating
3. **AHRI data:** Recovery efficiency

**Extraction tips:**
- How efficiently input energy heats water
- Decimal (0.95 = 95% efficient)
- Electric resistance: ~0.98 (nearly 100%)
- Gas: 0.75-0.90 typically
- Heat pump: effectively > 1.0 (but uses COP instead)
- May not be listed for all units

**Typical values:**
- Electric resistance: 0.95-0.99
- Gas storage: 0.75-0.85
- Gas condensing: 0.90-0.95

**Example values:**
- 0.95 (electric)
- 0.80 (gas)
- 0.98 (high-efficiency)

---

## Field Summary Table

| Model | Field | Type | Sources | Can be null? |
|-------|-------|------|---------|--------------|
| WaterHeatingSystem | name | string | CBECC, schedule | No |
| WaterHeatingSystem | status | enum | CBECC, CF1R | Yes |
| WaterHeatingSystem | system_type | string | CBECC | Yes |
| WaterHeatingSystem | water_heaters | List[WaterHeater] | CBECC, schedule | No (but can be empty) |
| WaterHeater | name | string | CBECC, schedule | No |
| WaterHeater | fuel | enum | CBECC, schedule | Yes |
| WaterHeater | tank_type | enum | CBECC, schedule | Yes |
| WaterHeater | volume | float | CBECC, schedule | Yes |
| WaterHeater | energy_factor | float | CBECC, schedule | Yes |
| WaterHeater | input_rating | float | CBECC, schedule | Yes |
| WaterHeater | input_rating_units | string | CBECC, schedule | Yes |
| WaterHeater | interior_insulation_r_value | float | CBECC, specs | Yes |
| WaterHeater | exterior_insulation_r_value | float | CBECC, specs | Yes |
| WaterHeater | standby_loss | float | CBECC, specs | Yes |
| WaterHeater | tank_location | string | CBECC, plans | Yes |
| WaterHeater | rated_flow | float | CBECC, schedule | Yes |
| WaterHeater | first_hour_rating | float | CBECC, schedule | Yes |
| WaterHeater | recovery_efficiency | float | CBECC, specs | Yes |

**Total fields:** 18 (3 required + 15 optional)

---

## Extraction Best Practices

### Page Reading Order
1. Start with CBECC-Res DHW section (most standardized format)
2. Check CF1R-PLB forms for missing fields
3. Use equipment schedules to fill remaining gaps
4. Reference plumbing plans for location information

### Common Document Layouts

**CBECC-Res DHW Page:**
- Header: System name, type
- Water heater section: Name, fuel, tank type, volume
- Efficiency: EF/UEF, input rating
- Location: Tank location specification
- System configuration: Central, point of use, etc.

**Equipment Schedule:**
- Columns: Mark, Type, Model, Volume, EF/UEF, Input, Location
- One row per water heater
- May have manufacturer specifications

**CF1R-PLB Form:**
- Water heater type and fuel
- Efficiency rating (UEF)
- Tank specifications
- Compliance calculations

**Plumbing Plans:**
- Water heater symbol and label
- Location in building
- Piping connections

### Quality Checks

Before finalizing extraction:
- [ ] All water heaters have unique names
- [ ] fuel is valid enum value
- [ ] tank_type is valid enum value
- [ ] Efficiency ratings in reasonable ranges (0.5-4.5)
- [ ] volume in gallons (null for tankless)
- [ ] input_rating_units specified if input_rating provided
- [ ] rated_flow only for tankless (null for storage)
- [ ] first_hour_rating only for storage (null for tankless)
- [ ] status is valid (New, Existing, Altered)

### Confidence Scoring

Document extraction confidence in notes:

**High confidence indicators:**
- Value from CBECC-Res DHW section
- Clearly legible, no ambiguity
- Cross-referenced across multiple pages with agreement

**Medium confidence indicators:**
- Value from equipment schedule only
- Legible but some interpretation needed
- Tank type inferred from efficiency

**Low confidence indicators:**
- Value inferred from system type or incomplete data
- Hand-written value, OCR uncertain
- Conflict between pages, used best judgment

Include specific notes for low-confidence fields so verifier can double-check.

---

*End of DHW Field Guide*
