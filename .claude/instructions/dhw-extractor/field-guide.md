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
1. **Equipment schedule:** System designation (PRIMARY SOURCE)
2. **Plumbing plans:** System labels
3. **Floor plans:** Water heater location

**Extraction tips:**
- Use equipment schedule names (e.g., "DHW-1", "WH System")
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
- "Existing" (existing water heater being retained)
- "Altered" (existing equipment being modified)

---

### system_type
**Type:** string (optional)
**Description:** Water heating system configuration type

**Document sources:**
1. **Plumbing plans:** System layout (PRIMARY SOURCE)
2. **Equipment schedule:** System type column
3. **Specifications:** System configuration

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
1. **Equipment schedule:** Row identifier (WH-1, HPWH-1) (PRIMARY SOURCE)
2. **Plumbing plans:** Equipment tags and labels
3. **Model number:** May serve as identifier

**Extraction tips:**
- Use equipment schedule names (e.g., "WH-01", "HPWH-1")
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
1. **Equipment schedule:** Fuel column or type (PRIMARY SOURCE)
2. **Plumbing plans:** Equipment callout
3. **Model number:** May indicate fuel type

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
1. **Equipment schedule:** Type column (PRIMARY SOURCE)
2. **Plumbing plans:** Equipment callout
3. **Physical description:** "Tankless" or "Storage" noted

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
1. **Equipment schedule:** Capacity/Volume column (PRIMARY SOURCE)
2. **Model specifications:** Size in model number
3. **Plumbing plans:** Equipment callout with capacity

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
1. **Equipment schedule:** Efficiency column (PRIMARY SOURCE)
2. **AHRI certification:** Product efficiency rating
3. **Manufacturer specs:** Product data sheet

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
1. **Equipment schedule:** Input column (PRIMARY SOURCE)
2. **Model specifications:** Power rating
3. **Electrical panel schedule:** Circuit amperage (for electric)

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
1. **Equipment schedule:** Insulation column (PRIMARY SOURCE)
2. **Product specifications:** Tank R-value
3. **Manufacturer data sheet:** Insulation details

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
1. **Equipment schedule:** Blanket insulation column (PRIMARY SOURCE)
2. **Project specifications:** Added insulation details
3. **Energy notes:** Insulation requirements

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
1. **Product specifications:** Standby loss rating (PRIMARY SOURCE)
2. **AHRI data:** Standby performance
3. **Equipment schedule:** May show standby loss

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
1. **Plumbing plans:** Equipment location shown (PRIMARY SOURCE)
2. **Floor plans:** Water heater symbol and location
3. **Equipment schedule:** Location column

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
1. **Equipment schedule:** GPM column (PRIMARY SOURCE)
2. **Product specifications:** Max flow rate
3. **Plumbing plans:** Flow rate callout

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
1. **Equipment schedule:** FHR column (PRIMARY SOURCE)
2. **Product specifications:** First hour capacity
3. **AHRI certification:** FHR rating

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
1. **Product specifications:** RE rating (PRIMARY SOURCE)
2. **AHRI data:** Recovery efficiency
3. **Equipment schedule:** May show recovery efficiency

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
| WaterHeatingSystem | name | string | Equipment schedule | No |
| WaterHeatingSystem | status | enum | Project scope | Yes |
| WaterHeatingSystem | system_type | string | Plumbing plans | Yes |
| WaterHeatingSystem | water_heaters | List[WaterHeater] | Equipment schedule | No (but can be empty) |
| WaterHeater | name | string | Equipment schedule | No |
| WaterHeater | fuel | enum | Equipment schedule | Yes |
| WaterHeater | tank_type | enum | Equipment schedule | Yes |
| WaterHeater | volume | float | Equipment schedule | Yes |
| WaterHeater | energy_factor | float | Equipment schedule | Yes |
| WaterHeater | input_rating | float | Equipment schedule | Yes |
| WaterHeater | input_rating_units | string | Equipment schedule | Yes |
| WaterHeater | interior_insulation_r_value | float | Product specs | Yes |
| WaterHeater | exterior_insulation_r_value | float | Product specs | Yes |
| WaterHeater | standby_loss | float | Product specs | Yes |
| WaterHeater | tank_location | string | Plumbing plans | Yes |
| WaterHeater | rated_flow | float | Equipment schedule | Yes |
| WaterHeater | first_hour_rating | float | Equipment schedule | Yes |
| WaterHeater | recovery_efficiency | float | Product specs | Yes |

**Total fields:** 18 (3 required + 15 optional)

---

## Extraction Best Practices

### Page Reading Order
1. Start with Equipment schedules (water heater specs, efficiency)
2. Check Plumbing plans (system layout, equipment location)
3. Use Energy notes/specifications for missing values
4. Reference Floor plans for equipment locations

### Common Document Layouts

**Equipment Schedule:**
- Columns: Mark, Type, Model, Volume, EF/UEF, Input, Location
- One row per water heater
- May have manufacturer specifications

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
- Value from equipment schedule, clearly legible
- Cross-referenced across multiple pages with agreement
- Standard format with clear units

**Medium confidence indicators:**
- Value from plumbing plan callouts
- Legible but some interpretation needed
- Tank type inferred from efficiency

**Low confidence indicators:**
- Value inferred from system type or incomplete data
- Hand-written value, OCR uncertain
- Conflict between pages, used best judgment

Include specific notes for low-confidence fields so verifier can double-check.

---

*End of DHW Field Guide*
