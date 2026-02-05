"""Orientation-based takeoff schema for human-aligned extraction.

TakeoffSpec organizes data by orientation (matching CBECC structure) rather than
component lists. This aligns with how human takeoff instructions work:
- Walls grouped by orientation (North/East/South/West)
- Fenestration nested under parent walls
- Explicit thermal boundary (conditioned vs unconditioned)
- Uncertainty flags for every assumption

The TakeoffSpec is transformed to BuildingSpec for verification against ground truth.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class Orientation(str, Enum):
    """Cardinal orientation labels."""
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


class FlagSeverity(str, Enum):
    """Uncertainty flag severity levels."""
    HIGH = "high"      # Likely incorrect, needs review
    MEDIUM = "medium"  # Uncertain, may need verification
    LOW = "low"        # Minor uncertainty, probably correct


class ComponentStatus(str, Enum):
    """Status of building component."""
    NEW = "New"
    EXISTING = "Existing"
    ALTERED = "Altered"


class ZoneType(str, Enum):
    """Thermal zone classification."""
    CONDITIONED = "Conditioned"
    UNCONDITIONED = "Unconditioned"
    PLENUM = "Plenum"


# ============================================================================
# Uncertainty Tracking
# ============================================================================

class UncertaintyFlag(BaseModel):
    """Flag for tracking extraction uncertainties."""
    field_path: str = Field(description="Dot-path to field, e.g., 'house_walls.north.gross_wall_area'")
    severity: FlagSeverity = Field(description="How uncertain this value is")
    reason: str = Field(description="Why this value is uncertain")
    source_page: Optional[int] = Field(default=None, description="Page number where value was found")
    alternative_value: Optional[str] = Field(default=None, description="Alternative interpretation if any")


class AssumptionEntry(BaseModel):
    """Explicit assumption made during extraction."""
    field_path: str = Field(description="Dot-path to affected field")
    assumption: str = Field(description="What was assumed")
    rationale: str = Field(description="Why this assumption was made")
    default_used: bool = Field(default=False, description="Whether a default value was used")


# ============================================================================
# Fenestration (Windows/Glazed Doors)
# ============================================================================

class FenestrationEntry(BaseModel):
    """Window or glazed door nested under parent wall."""
    name: str = Field(description="Window identifier (W1, SGD1, etc.)")
    fenestration_type: Optional[str] = Field(default=None, description="Window, Sliding Glass Door, etc.")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")

    # Dimensions
    height: Optional[float] = Field(default=None, ge=0, description="Height in feet")
    width: Optional[float] = Field(default=None, ge=0, description="Width in feet")
    area: Optional[float] = Field(default=None, ge=0, description="Area in sq ft")
    multiplier: int = Field(default=1, ge=1, description="Number of identical units")

    # Performance
    u_factor: Optional[float] = Field(default=None, description="Thermal transmittance")
    shgc: Optional[float] = Field(default=None, ge=0, le=1, description="Solar heat gain coefficient")

    # Shading
    exterior_shade: Optional[str] = Field(default=None, description="Overhang or shading description")
    overhang_depth: Optional[float] = Field(default=None, ge=0, description="Overhang depth in feet")


class OpaqueDoorEntry(BaseModel):
    """Non-glazed door in a wall."""
    name: str = Field(description="Door identifier")
    door_type: Optional[str] = Field(default=None, description="Entry, garage, etc.")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")
    area: Optional[float] = Field(default=None, ge=0, description="Area in sq ft")
    u_factor: Optional[float] = Field(default=None, description="Thermal transmittance")


# ============================================================================
# Wall Components (Orientation-Based)
# ============================================================================

class OrientationWall(BaseModel):
    """Wall component for a specific orientation.

    Fenestration is nested here, not in a separate list.
    This matches CBECC structure and human takeoff instructions.
    """
    gross_wall_area: Optional[float] = Field(default=None, ge=0, description="Total wall area before deductions (sq ft)")
    net_wall_area: Optional[float] = Field(default=None, ge=0, description="Wall area after window/door deductions (sq ft)")
    azimuth: Optional[float] = Field(default=None, ge=0, lt=360, description="True azimuth in degrees")

    # Construction
    construction_type: Optional[str] = Field(default=None, description="e.g., R-21 Wood Frame Wall")
    framing_factor: Optional[float] = Field(default=None, description="Framing fraction")

    # Components status
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")

    # Nested fenestration (key difference from BuildingSpec)
    fenestration: List[FenestrationEntry] = Field(default_factory=list, description="Windows and glazed doors in this wall")
    opaque_doors: List[OpaqueDoorEntry] = Field(default_factory=list, description="Non-glazed doors in this wall")

    @property
    def total_fenestration_area(self) -> float:
        """Calculate total fenestration area in this wall."""
        return sum(
            (f.area or 0) * f.multiplier
            for f in self.fenestration
        )

    @property
    def total_door_area(self) -> float:
        """Calculate total opaque door area in this wall."""
        return sum(d.area or 0 for d in self.opaque_doors)


class HouseWalls(BaseModel):
    """All exterior walls organized by cardinal orientation.

    This is the key difference from BuildingSpec: walls are grouped
    by orientation with fenestration nested under each.
    """
    north: Optional[OrientationWall] = Field(default=None, description="North-facing wall")
    east: Optional[OrientationWall] = Field(default=None, description="East-facing wall")
    south: Optional[OrientationWall] = Field(default=None, description="South-facing wall")
    west: Optional[OrientationWall] = Field(default=None, description="West-facing wall")

    # For non-cardinal orientations (rotated buildings)
    additional_walls: List[OrientationWall] = Field(default_factory=list, description="Walls at other orientations")

    def get_all_walls(self) -> List[tuple[str, OrientationWall]]:
        """Get all walls as (label, wall) tuples."""
        walls = []
        if self.north:
            walls.append(("north", self.north))
        if self.east:
            walls.append(("east", self.east))
        if self.south:
            walls.append(("south", self.south))
        if self.west:
            walls.append(("west", self.west))
        for i, wall in enumerate(self.additional_walls):
            walls.append((f"wall_{i}", wall))
        return walls


# ============================================================================
# Thermal Boundary
# ============================================================================

class ConditionedZone(BaseModel):
    """Conditioned (heated/cooled) thermal zone."""
    name: str = Field(description="Zone identifier")
    floor_area: Optional[float] = Field(default=None, ge=0, description="Floor area in sq ft")
    ceiling_height: Optional[float] = Field(default=None, gt=0, description="Ceiling height in feet")
    volume: Optional[float] = Field(default=None, ge=0, description="Zone volume in cu ft")
    stories: int = Field(default=1, ge=1, description="Number of stories in this zone")

    # Envelope areas
    exterior_wall_area: Optional[float] = Field(default=None, ge=0, description="Total exterior wall area (sq ft)")
    ceiling_below_attic_area: Optional[float] = Field(default=None, ge=0, description="Ceiling below attic (sq ft)")
    cathedral_ceiling_area: Optional[float] = Field(default=None, ge=0, description="Cathedral ceiling area (sq ft)")
    slab_floor_area: Optional[float] = Field(default=None, ge=0, description="Slab-on-grade floor area (sq ft)")
    exterior_floor_area: Optional[float] = Field(default=None, ge=0, description="Exterior floor area (sq ft)")


class UnconditionedZone(BaseModel):
    """Unconditioned zone (garage, storage, etc.)."""
    name: str = Field(description="Zone identifier")
    zone_subtype: Optional[str] = Field(default=None, description="Garage, storage, attic, etc.")
    floor_area: Optional[float] = Field(default=None, ge=0, description="Floor area in sq ft")
    volume: Optional[float] = Field(default=None, ge=0, description="Zone volume in cu ft")


class ThermalBoundary(BaseModel):
    """Defines conditioned vs unconditioned spaces.

    This explicit separation helps extractors identify what's inside
    the thermal envelope vs outside.
    """
    conditioned_zones: List[ConditionedZone] = Field(default_factory=list, description="Heated/cooled zones")
    unconditioned_zones: List[UnconditionedZone] = Field(default_factory=list, description="Non-conditioned zones")

    # Aggregate metrics
    total_conditioned_floor_area: Optional[float] = Field(default=None, ge=0, description="Sum of conditioned zone areas")

    @property
    def calculated_conditioned_area(self) -> float:
        """Calculate total conditioned floor area from zones."""
        return sum(z.floor_area or 0 for z in self.conditioned_zones)


# ============================================================================
# Ceiling/Roof Components
# ============================================================================

class CeilingEntry(BaseModel):
    """Ceiling or roof component."""
    name: str = Field(description="Ceiling identifier")
    ceiling_type: Optional[str] = Field(default=None, description="Below attic, cathedral, etc.")
    zone: Optional[str] = Field(default=None, description="Parent zone name")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")

    # Geometry
    area: Optional[float] = Field(default=None, ge=0, description="Ceiling area in sq ft")
    orientation: Optional[float] = Field(default=None, description="Roof orientation in degrees")
    roof_pitch: Optional[float] = Field(default=None, description="Rise per 12 run")
    roof_tilt: Optional[float] = Field(default=None, description="Tilt angle in degrees")

    # Construction
    construction_type: Optional[str] = Field(default=None, description="R-value assembly type")
    framing_factor: Optional[float] = Field(default=None, description="Framing fraction")

    # Surface properties
    roof_reflectance: Optional[float] = Field(default=None, ge=0, le=1, description="Cool roof reflectance")
    roof_emittance: Optional[float] = Field(default=None, ge=0, le=1, description="Roof emittance")


# ============================================================================
# Slab/Floor Components
# ============================================================================

class SlabEntry(BaseModel):
    """Slab-on-grade floor component."""
    name: str = Field(description="Slab identifier")
    zone: Optional[str] = Field(default=None, description="Parent zone name")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")

    # Geometry
    area: Optional[float] = Field(default=None, ge=0, description="Floor area in sq ft")
    perimeter: Optional[float] = Field(default=None, ge=0, description="Exposed perimeter in feet")

    # Thermal properties
    edge_insulation_r_value: Optional[float] = Field(default=None, description="Edge insulation R-value")
    carpeted_fraction: Optional[float] = Field(default=None, ge=0, le=1, description="Fraction with carpet")
    heated: bool = Field(default=False, description="Radiant floor heating")


# ============================================================================
# HVAC Systems
# ============================================================================

class HVACSystemEntry(BaseModel):
    """HVAC system in takeoff format."""
    name: str = Field(description="System identifier")
    system_type: Optional[str] = Field(default=None, description="Heat Pump, Furnace, etc.")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")

    # Heating performance
    heating_type: Optional[str] = Field(default=None, description="Heat pump, gas furnace, electric, etc.")
    hspf: Optional[float] = Field(default=None, description="HSPF rating for heat pumps")
    afue: Optional[float] = Field(default=None, description="AFUE rating for furnaces")
    heating_capacity: Optional[float] = Field(default=None, description="Heating capacity in Btuh")

    # Cooling performance
    cooling_type: Optional[str] = Field(default=None, description="Heat pump, AC, etc.")
    seer2: Optional[float] = Field(default=None, description="SEER2 rating")
    eer2: Optional[float] = Field(default=None, description="EER2 rating")
    cooling_capacity: Optional[float] = Field(default=None, description="Cooling capacity in Btuh")

    # Distribution
    ducted: Optional[bool] = Field(default=None, description="Ducted vs ductless")
    duct_location: Optional[str] = Field(default=None, description="Conditioned, attic, etc.")
    duct_leakage_percent: Optional[float] = Field(default=None, description="Duct leakage as percent")
    duct_r_value: Optional[float] = Field(default=None, description="Duct insulation R-value")


# ============================================================================
# DHW Systems
# ============================================================================

class DHWSystem(BaseModel):
    """Domestic hot water system."""
    name: str = Field(description="System identifier")
    system_type: Optional[str] = Field(default=None, description="Storage, Tankless, Heat Pump")
    status: Optional[str] = Field(default=None, description="New, Existing, Altered")

    # Equipment
    fuel: Optional[str] = Field(default=None, description="Electric, Natural Gas, Heat Pump")
    tank_volume: Optional[float] = Field(default=None, ge=0, description="Tank volume in gallons")

    # Performance
    energy_factor: Optional[float] = Field(default=None, description="EF or UEF rating")
    input_rating: Optional[float] = Field(default=None, description="Input rating (watts or Btuh)")
    input_rating_units: Optional[str] = Field(default=None, description="watts, Btuh, etc.")
    recovery_efficiency: Optional[float] = Field(default=None, ge=0, le=1, description="Recovery efficiency")

    # Location
    location: Optional[str] = Field(default=None, description="Conditioned, garage, etc.")


# ============================================================================
# Project Information
# ============================================================================

class TakeoffProjectInfo(BaseModel):
    """Project metadata for takeoff."""
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
    fuel_type: Optional[str] = Field(default=None, description="All Electric, Natural Gas, Mixed")
    house_type: Optional[str] = Field(default=None, description="Single Family, Multi Family, ADU")
    dwelling_units: Optional[int] = Field(default=None, ge=1, description="Number of dwelling units")
    stories: Optional[int] = Field(default=None, ge=1, description="Number of stories")
    bedrooms: Optional[int] = Field(default=None, ge=0, description="Number of bedrooms")

    # Orientation
    front_orientation: Optional[float] = Field(default=None, ge=0, lt=360, description="Front orientation in degrees")
    orientation_confidence: Optional[str] = Field(default=None, description="Orientation extraction confidence: high/medium/low")
    orientation_verification: Optional[str] = Field(default=None, description="Two-pass verification: agreement/side_front_confusion/front_back_confusion/disagreement")
    all_orientations: Optional[bool] = Field(default=None, description="All orientations analysis (CBECC-only, non-extractable)")

    # Envelope aggregates (from CBECC)
    conditioned_floor_area: Optional[float] = Field(default=None, gt=0, description="CFA in sq ft")
    window_area: Optional[float] = Field(default=None, ge=0, description="Total window area sq ft")
    window_to_floor_ratio: Optional[float] = Field(default=None, ge=0, le=1, description="WWR")
    exterior_wall_area: Optional[float] = Field(default=None, ge=0, description="Exterior wall area sq ft")

    # Features
    attached_garage: bool = Field(default=False, description="Has attached garage")


# ============================================================================
# Complete TakeoffSpec
# ============================================================================

class TakeoffSpec(BaseModel):
    """Complete orientation-based takeoff specification.

    This schema matches human takeoff instructions:
    - Walls organized by orientation (N/E/S/W)
    - Fenestration nested under parent walls
    - Explicit thermal boundary
    - Uncertainty flags for every assumption

    TakeoffSpec is transformed to BuildingSpec for verification.
    """
    # Core info
    project: TakeoffProjectInfo = Field(default_factory=TakeoffProjectInfo)

    # Walls by orientation (key difference from BuildingSpec)
    house_walls: HouseWalls = Field(default_factory=HouseWalls)

    # Thermal boundary
    thermal_boundary: ThermalBoundary = Field(default_factory=ThermalBoundary)

    # Other envelope
    ceilings: List[CeilingEntry] = Field(default_factory=list)
    slab_floors: List[SlabEntry] = Field(default_factory=list)

    # Systems
    hvac_systems: List[HVACSystemEntry] = Field(default_factory=list)
    dhw_systems: List[DHWSystem] = Field(default_factory=list)

    # Uncertainty tracking (key addition)
    flags: List[UncertaintyFlag] = Field(default_factory=list, description="Uncertainties for review")
    assumptions: List[AssumptionEntry] = Field(default_factory=list, description="Explicit assumptions made")

    # Extraction metadata
    extraction_notes: Optional[str] = Field(default=None, description="General extraction notes")
