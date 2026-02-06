"""Pydantic models for building specification extraction output.

Comprehensive schema covering all fields needed for EnergyPlus modeling
from California Title 24 compliance documents.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class FuelType(str, Enum):
    ALL_ELECTRIC = "All Electric"
    NATURAL_GAS = "Natural Gas"
    MIXED = "Mixed"


class HouseType(str, Enum):
    SINGLE_FAMILY = "Single Family"
    MULTI_FAMILY = "Multi Family"
    ADU = "ADU"


class RunScope(str, Enum):
    NEWLY_CONSTRUCTED = "Newly Constructed"
    ADDITION = "Addition"
    ALTERATION = "Alteration"
    ADDITION_ALTERATION = "Addition and Alteration"


class ComponentStatus(str, Enum):
    NEW = "New"
    EXISTING = "Existing"
    ALTERED = "Altered"


class ZoneType(str, Enum):
    CONDITIONED = "Conditioned"
    UNCONDITIONED = "Unconditioned"
    PLENUM = "Plenum"


class HVACSystemType(str, Enum):
    HEAT_PUMP = "Heat Pump"
    FURNACE = "Furnace"
    SPLIT_SYSTEM = "Split System"
    PACKAGE_UNIT = "Package Unit"
    DUCTLESS = "Ductless"
    OTHER = "Other"


class WaterHeaterType(str, Enum):
    STORAGE = "Storage"
    TANKLESS = "Tankless"
    HEAT_PUMP = "Heat Pump"
    INSTANTANEOUS = "Instantaneous"


class WaterHeaterFuel(str, Enum):
    ELECTRIC = "Electric Resistance"
    GAS = "Natural Gas"
    HEAT_PUMP = "Heat Pump"


# ============================================================================
# Project Info
# ============================================================================

class ProjectInfo(BaseModel):
    """Project metadata and basic building info."""
    # Identification
    run_id: Optional[str] = Field(default=None, description="Run ID")
    run_title: Optional[str] = Field(default=None, description="Project/run title")
    run_number: Optional[int] = Field(default=None, description="Run number")
    run_scope: Optional[str] = Field(default=None, description="Newly Constructed, Addition, etc.")

    # Location
    address: Optional[str] = Field(default=None, description="Street address")
    city: Optional[str] = Field(default=None, description="City name")
    climate_zone: Optional[int] = Field(default=None, ge=1, le=16, description="CA climate zone 1-16")

    # Building characteristics
    standards_version: Optional[str] = Field(default=None, description="Title 24 standards version")
    all_orientations: Optional[bool] = Field(default=None, description="All orientations analysis")
    fuel_type: Optional[str] = Field(default=None, description="All Electric, Natural Gas, Mixed")
    house_type: Optional[str] = Field(default=None, description="Single Family, Multi Family, ADU")
    dwelling_units: Optional[int] = Field(default=None, ge=1, description="Number of dwelling units")
    stories: Optional[int] = Field(default=None, ge=1, description="Number of stories")
    bedrooms: Optional[int] = Field(default=None, ge=0, description="Number of bedrooms")
    attached_garage: Optional[bool] = Field(default=None, description="Has attached garage")
    front_orientation: Optional[float] = Field(default=None, description="Front orientation in degrees")
    orientation_confidence: Optional[str] = Field(default=None, description="Orientation extraction confidence: high/medium/low")
    orientation_verification: Optional[str] = Field(default=None, description="Two-pass verification result: agreement/side_front_confusion/front_back_confusion/disagreement")


# ============================================================================
# Envelope Aggregate Metrics
# ============================================================================

class EnvelopeInfo(BaseModel):
    """Building envelope aggregate data."""
    # Floor areas
    conditioned_floor_area: Optional[float] = Field(default=None, gt=0, description="CFA in sq ft")
    addition_conditioned_floor_area: Optional[float] = Field(default=0.0, ge=0, description="Addition CFA sq ft")

    # Window/glazing
    window_area: Optional[float] = Field(default=None, ge=0, description="Total window area sq ft")
    window_to_floor_ratio: Optional[float] = Field(default=None, ge=0, le=1, description="WWR")
    fenestration_u_factor: Optional[float] = Field(default=None, description="Area-weighted U-factor")

    # Wall areas
    exterior_wall_area: Optional[float] = Field(default=None, ge=0, description="Exterior wall area sq ft")
    underground_wall_area: Optional[float] = Field(default=0.0, ge=0, description="Underground wall area sq ft")

    # Slab/floor areas
    slab_floor_area: Optional[float] = Field(default=None, ge=0, description="Conditioned zone slab floor area sq ft")
    exposed_slab_floor_area: Optional[float] = Field(default=0.0, ge=0, description="Exposed slab floor area sq ft")
    below_grade_floor_area: Optional[float] = Field(default=0.0, ge=0, description="Conditioned zone below grade floor area sq ft")
    exposed_below_grade_floor_area: Optional[float] = Field(default=0.0, ge=0, description="Exposed below grade floor area sq ft")

    # PV
    pv_credit_available: Optional[bool] = Field(default=None, description="PV credit available")
    pv_generation_max_credit: Optional[float] = Field(default=None, description="PV generation max credit LSC $")
    credit_available_for_pv: Optional[float] = Field(default=None, description="Credit available for PV LSC $")
    final_pv_credit: Optional[float] = Field(default=None, description="Final PV credit LSC $/ft2-yr")

    # Infiltration & quality
    zonal_control: Optional[bool] = Field(default=None, description="Zonal control")
    infiltration_ach50: Optional[float] = Field(default=None, description="Envelope infiltration ACH @ 50 Pa")
    infiltration_cfm50: Optional[float] = Field(default=None, description="Envelope infiltration CFM @ 50 Pa")
    quality_insulation_installation: Optional[bool] = Field(default=None, description="QII")


# ============================================================================
# Wall Components
# ============================================================================

class WallComponent(BaseModel):
    """Individual exterior wall component."""
    name: str = Field(description="Wall name/identifier")
    zone: Optional[str] = Field(default=None, description="Zone name")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    construction_type: Optional[str] = Field(default=None, description="Wall construction type (e.g., R-21 Wall)")
    orientation: Optional[float] = Field(default=None, description="Orientation in degrees")
    area: Optional[float] = Field(default=None, ge=0, description="Wall area sq ft")
    window_area: Optional[float] = Field(default=None, ge=0, description="Window area in this wall sq ft")
    door_area: Optional[float] = Field(default=None, ge=0, description="Door area sq ft")
    tilt: Optional[float] = Field(default=None, description="Tilt angle in degrees")
    framing_factor: Optional[float] = Field(default=None, description="Framing factor")


class WallConstruction(BaseModel):
    """Wall construction assembly."""
    name: str = Field(description="Construction name")
    construction_type: Optional[str] = Field(default=None, description="Wood Framed Wall, etc.")
    cavity_r_value: Optional[float] = Field(default=None, description="Total cavity R-value")
    total_thickness: Optional[float] = Field(default=None, description="Total thickness in inches")
    winter_design_u_value: Optional[float] = Field(default=None, description="Winter design U-value")
    layers: Optional[List[str]] = Field(default=None, description="Layer descriptions")


# ============================================================================
# Window Components
# ============================================================================

class WindowComponent(BaseModel):
    """Individual window/fenestration component."""
    name: str = Field(description="Window name/identifier")
    wall: Optional[str] = Field(default=None, description="Parent wall name")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    azimuth: Optional[float] = Field(default=None, description="Azimuth in degrees")
    height: Optional[float] = Field(default=None, description="Height in ft")
    width: Optional[float] = Field(default=None, description="Width in ft")
    multiplier: Optional[int] = Field(default=None, description="Window multiplier")
    area: Optional[float] = Field(default=None, ge=0, description="Window area sq ft")
    u_factor: Optional[float] = Field(default=None, description="U-factor")
    shgc: Optional[float] = Field(default=None, description="SHGC")
    exterior_shade: Optional[str] = Field(default=None, description="Exterior shading type")


# ============================================================================
# Ceiling Components
# ============================================================================

class CeilingComponent(BaseModel):
    """Cathedral ceiling / roof component."""
    name: str = Field(description="Ceiling name/identifier")
    zone: Optional[str] = Field(default=None, description="Zone name")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    construction_type: Optional[str] = Field(default=None, description="Ceiling construction type")
    orientation: Optional[float] = Field(default=None, description="Orientation in degrees")
    area: Optional[float] = Field(default=None, ge=0, description="Ceiling area sq ft")
    roof_rise: Optional[float] = Field(default=None, description="Roof rise (x in 12)")
    roof_pitch: Optional[float] = Field(default=None, description="Roof pitch")
    roof_tilt: Optional[float] = Field(default=None, description="Roof tilt in degrees")
    roof_reflectance: Optional[float] = Field(default=None, description="Roof reflectance")
    roof_emittance: Optional[float] = Field(default=None, description="Roof emittance")
    framing_factor: Optional[float] = Field(default=None, description="Framing factor")


class CeilingConstruction(BaseModel):
    """Ceiling construction assembly."""
    name: str = Field(description="Construction name")
    construction_type: Optional[str] = Field(default=None, description="Wood Framed Ceiling, etc.")
    cavity_r_value: Optional[float] = Field(default=None, description="Total cavity R-value")
    total_thickness: Optional[float] = Field(default=None, description="Total thickness in inches")
    winter_design_u_value: Optional[float] = Field(default=None, description="Winter design U-value")
    layers: Optional[List[str]] = Field(default=None, description="Layer descriptions")


# ============================================================================
# Floor Components
# ============================================================================

class SlabFloor(BaseModel):
    """Slab-on-grade floor component."""
    name: str = Field(description="Floor name/identifier")
    zone: Optional[str] = Field(default=None, description="Zone name")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    area: Optional[float] = Field(default=None, ge=0, description="Floor area sq ft")
    perimeter: Optional[float] = Field(default=None, ge=0, description="Perimeter in ft")
    edge_insulation_r_value: Optional[float] = Field(default=None, description="Edge insulation R-value")
    carpeted_fraction: Optional[float] = Field(default=None, ge=0, le=1, description="Carpeted fraction")
    heated: Optional[bool] = Field(default=None, description="Heated slab")


# ============================================================================
# Zone Info
# ============================================================================

class ZoneInfo(BaseModel):
    """Thermal zone data."""
    name: str = Field(description="Zone name")
    zone_type: Optional[str] = Field(default=None, description="Conditioned, Unconditioned, Plenum")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    floor_area: Optional[float] = Field(default=None, ge=0, description="Zone floor area sq ft")
    ceiling_height: Optional[float] = Field(default=None, description="Ceiling height in ft")
    stories: Optional[int] = Field(default=None, description="Number of stories in zone")
    volume: Optional[float] = Field(default=None, ge=0, description="Zone volume cu ft")
    exterior_wall_area: Optional[float] = Field(default=None, ge=0, description="Zone exterior wall area sq ft")
    exterior_wall_door_area: Optional[float] = Field(default=None, ge=0, description="Zone exterior wall door area sq ft")
    ceiling_below_attic_area: Optional[float] = Field(default=None, ge=0, description="Ceiling below attic area sq ft")
    cathedral_ceiling_area: Optional[float] = Field(default=None, ge=0, description="Cathedral ceiling area sq ft")
    slab_floor_area: Optional[float] = Field(default=None, ge=0, description="Zone slab floor area sq ft")
    exterior_floor_area: Optional[float] = Field(default=None, ge=0, description="Zone exterior floor area sq ft")


# ============================================================================
# Water Heating
# ============================================================================

class WaterHeater(BaseModel):
    """Individual water heater."""
    name: str = Field(description="Water heater name/identifier")
    fuel: Optional[str] = Field(default=None, description="Electric Resistance, Natural Gas, Heat Pump")
    tank_type: Optional[str] = Field(default=None, description="Storage, Tankless, etc.")
    volume: Optional[float] = Field(default=None, ge=0, description="Tank volume in gallons")
    energy_factor: Optional[float] = Field(default=None, description="Energy factor (EF or UEF)")
    input_rating: Optional[float] = Field(default=None, description="Input rating")
    input_rating_units: Optional[str] = Field(default=None, description="watts, Btuh, etc.")
    interior_insulation_r_value: Optional[float] = Field(default=None, description="Interior insulation R-value")
    exterior_insulation_r_value: Optional[float] = Field(default=None, description="Exterior insulation R-value")
    standby_loss: Optional[float] = Field(default=None, description="Standby loss")
    tank_location: Optional[str] = Field(default=None, description="Tank location")
    rated_flow: Optional[float] = Field(default=None, description="Rated flow GPM")
    first_hour_rating: Optional[float] = Field(default=None, description="First hour rating")
    recovery_efficiency: Optional[float] = Field(default=None, description="Recovery efficiency")


class WaterHeatingSystem(BaseModel):
    """Water heating system."""
    name: str = Field(description="System name/identifier")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    system_type: Optional[str] = Field(default=None, description="Central, Point of use, etc.")
    water_heaters: List[WaterHeater] = Field(default_factory=list, description="Water heaters in system")


# ============================================================================
# HVAC Systems
# ============================================================================

class HeatPumpHeating(BaseModel):
    """Heat pump heating performance data."""
    system_type: Optional[str] = Field(default=None, description="SplitHeatPump, PackagedHeatPump, etc.")
    hspf: Optional[float] = Field(default=None, description="HSPF rating")
    capacity_47: Optional[float] = Field(default=None, description="Capacity at 47F in Btuh")
    capacity_17: Optional[float] = Field(default=None, description="Capacity at 17F in Btuh")
    auxiliary_heating_capacity: Optional[float] = Field(default=None, description="Auxiliary heating capacity Btuh")
    ducted: Optional[bool] = Field(default=None, description="Ducted system")


class HeatPumpCooling(BaseModel):
    """Heat pump cooling performance data."""
    system_type: Optional[str] = Field(default=None, description="SplitHeatPump, PackagedHeatPump, etc.")
    seer2: Optional[float] = Field(default=None, description="SEER2 rating")
    eer2: Optional[float] = Field(default=None, description="EER2 rating")
    cfm_per_ton: Optional[float] = Field(default=None, description="CFM per ton")
    ac_charge: Optional[str] = Field(default=None, description="AC charge verification status")
    ducted: Optional[bool] = Field(default=None, description="Ducted system")


class DistributionSystem(BaseModel):
    """HVAC distribution/duct system."""
    name: str = Field(description="Distribution system name")
    system_type: Optional[str] = Field(default=None, description="DuctsInAll, DuctsInConditioned, etc.")
    percent_leakage: Optional[float] = Field(default=None, description="Duct leakage percent")
    insulation_r_value: Optional[float] = Field(default=None, description="Duct insulation R-value")
    supply_area: Optional[float] = Field(default=None, description="Supply duct area sq ft")
    supply_diameter: Optional[float] = Field(default=None, description="Supply duct diameter in")
    return_area: Optional[float] = Field(default=None, description="Return duct area sq ft")
    return_diameter: Optional[float] = Field(default=None, description="Return duct diameter in")
    bypass_duct: Optional[bool] = Field(default=None, description="Has bypass duct")


class HVACSystem(BaseModel):
    """Complete HVAC system."""
    name: str = Field(description="System name/identifier")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    system_type: Optional[str] = Field(default=None, description="Heat Pump, Furnace, etc.")
    heating: Optional[HeatPumpHeating] = Field(default=None, description="Heating performance")
    cooling: Optional[HeatPumpCooling] = Field(default=None, description="Cooling performance")
    distribution: Optional[DistributionSystem] = Field(default=None, description="Distribution system")


# ============================================================================
# Extraction Metadata
# ============================================================================

class ExtractionConflict(BaseModel):
    """A conflict between extractor outputs."""
    field: str = Field(description="Field name with conflict")
    item_name: Optional[str] = Field(default=None, description="Array item name if applicable")
    source_extractor: str = Field(description="First extractor that reported value")
    reported_value: Any = Field(description="Value from first extractor")
    conflicting_extractor: str = Field(description="Second extractor with different value")
    conflicting_value: Any = Field(description="Value from second extractor")
    resolution: str = Field(default="flagged_for_review", description="Resolution status")


class ExtractionStatus(BaseModel):
    """Per-domain extraction status."""
    domain: str = Field(description="Domain name: project, zones, windows, hvac, dhw")
    status: str = Field(description="success, partial, failed")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    items_extracted: int = Field(default=0, description="Number of items extracted")


# ============================================================================
# Complete Building Spec
# ============================================================================

class BuildingSpec(BaseModel):
    """Complete building specification from extraction.

    Contains all data needed to build an EnergyPlus model from
    California Title 24 compliance documents.
    """
    # Core info
    project: ProjectInfo = Field(default_factory=ProjectInfo)
    envelope: EnvelopeInfo = Field(default_factory=EnvelopeInfo)

    # Zones
    zones: List[ZoneInfo] = Field(default_factory=list)

    # Envelope components
    walls: List[WallComponent] = Field(default_factory=list)
    wall_constructions: List[WallConstruction] = Field(default_factory=list)
    windows: List[WindowComponent] = Field(default_factory=list)
    ceilings: List[CeilingComponent] = Field(default_factory=list)
    ceiling_constructions: List[CeilingConstruction] = Field(default_factory=list)
    slab_floors: List[SlabFloor] = Field(default_factory=list)

    # Systems
    hvac_systems: List[HVACSystem] = Field(default_factory=list)
    water_heating_systems: List[WaterHeatingSystem] = Field(default_factory=list)

    # Extraction metadata
    extraction_status: Dict[str, ExtractionStatus] = Field(default_factory=dict, description="Per-domain extraction status")
    conflicts: List[ExtractionConflict] = Field(default_factory=list, description="Conflicts between extractors")
