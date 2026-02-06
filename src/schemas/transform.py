"""Transform between TakeoffSpec (orientation-based) and BuildingSpec (component-list).

The transformation allows extractors to work with orientation-based data that matches
document structure while still verifying against existing BuildingSpec ground truth.

TakeoffSpec → BuildingSpec:
- house_walls.north → walls[] with name="N Wall"
- house_walls.north.fenestration[] → windows[] with wall="N Wall"
- thermal_boundary.conditioned_zones[] → zones[] with zone_type="Conditioned"
"""
from typing import Dict, List, Optional

from .takeoff_spec import (
    TakeoffSpec,
    OrientationWall,
    FenestrationEntry,
    ConditionedZone,
    UnconditionedZone,
    CeilingEntry,
    SlabEntry,
    HVACSystemEntry,
    DHWSystem,
)
from .building_spec import (
    BuildingSpec,
    ProjectInfo,
    EnvelopeInfo,
    ZoneInfo,
    WallComponent,
    WindowComponent,
    CeilingComponent,
    SlabFloor,
    HVACSystem,
    HeatPumpHeating,
    HeatPumpCooling,
    DistributionSystem,
    WaterHeatingSystem,
    WaterHeater,
)


# ============================================================================
# Orientation to Wall Name Mapping
# ============================================================================

ORIENTATION_TO_WALL_NAME = {
    "north": "N Wall",
    "east": "E Wall",
    "south": "S Wall",
    "west": "W Wall",
}

ORIENTATION_TO_AZIMUTH = {
    "north": 0.0,
    "east": 90.0,
    "south": 180.0,
    "west": 270.0,
}


def _get_zone_name(takeoff: TakeoffSpec) -> str:
    """Get the primary zone name from TakeoffSpec."""
    if takeoff.thermal_boundary.conditioned_zones:
        return takeoff.thermal_boundary.conditioned_zones[0].name
    return "Zone 1"


# ============================================================================
# Wall Transformation
# ============================================================================

def _transform_wall(
    orientation: str,
    wall: OrientationWall,
    zone_name: str
) -> WallComponent:
    """Transform an OrientationWall to a WallComponent."""
    wall_name = ORIENTATION_TO_WALL_NAME.get(orientation, f"{orientation.title()} Wall")
    default_azimuth = ORIENTATION_TO_AZIMUTH.get(orientation, 0.0)

    # Calculate window area from nested fenestration
    window_area = wall.total_fenestration_area
    door_area = wall.total_door_area

    return WallComponent(
        name=wall_name,
        zone=zone_name,
        status=wall.status,
        construction_type=wall.construction_type,
        orientation=wall.azimuth if wall.azimuth is not None else default_azimuth,
        area=wall.gross_wall_area,
        window_area=window_area if window_area > 0 else 0.0,
        door_area=door_area if door_area > 0 else 0.0,
        tilt=90.0,  # Vertical walls
        framing_factor=wall.framing_factor,
    )


def _transform_walls(takeoff: TakeoffSpec) -> List[WallComponent]:
    """Transform all walls from TakeoffSpec to BuildingSpec format."""
    walls = []
    zone_name = _get_zone_name(takeoff)

    for orientation, wall in takeoff.house_walls.get_all_walls():
        walls.append(_transform_wall(orientation, wall, zone_name))

    return walls


# ============================================================================
# Window Transformation
# ============================================================================

def _transform_fenestration(
    fenestration: FenestrationEntry,
    orientation: str,
    wall: OrientationWall
) -> WindowComponent:
    """Transform a FenestrationEntry to a WindowComponent."""
    wall_name = ORIENTATION_TO_WALL_NAME.get(orientation, f"{orientation.title()} Wall")
    default_azimuth = ORIENTATION_TO_AZIMUTH.get(orientation, 0.0)

    return WindowComponent(
        name=fenestration.name,
        wall=wall_name,
        status=fenestration.status,
        azimuth=wall.azimuth if wall.azimuth is not None else default_azimuth,
        height=fenestration.height,
        width=fenestration.width,
        multiplier=fenestration.multiplier,
        area=fenestration.area,
        u_factor=fenestration.u_factor,
        shgc=fenestration.shgc,
        exterior_shade=fenestration.exterior_shade,
    )


def _transform_windows(takeoff: TakeoffSpec) -> List[WindowComponent]:
    """Transform all fenestration from TakeoffSpec to BuildingSpec format."""
    windows = []

    for orientation, wall in takeoff.house_walls.get_all_walls():
        for fenestration in wall.fenestration:
            windows.append(_transform_fenestration(fenestration, orientation, wall))

    return windows


# ============================================================================
# Zone Transformation
# ============================================================================

def _transform_conditioned_zone(zone: ConditionedZone) -> ZoneInfo:
    """Transform a ConditionedZone to a ZoneInfo."""
    return ZoneInfo(
        name=zone.name,
        zone_type="Conditioned",
        status="New",  # Default to new
        floor_area=zone.floor_area,
        ceiling_height=zone.ceiling_height,
        stories=zone.stories,
        volume=zone.volume,
        exterior_wall_area=zone.exterior_wall_area,
        ceiling_below_attic_area=zone.ceiling_below_attic_area,
        cathedral_ceiling_area=zone.cathedral_ceiling_area,
        slab_floor_area=zone.slab_floor_area,
        exterior_floor_area=zone.exterior_floor_area,
    )


def _transform_unconditioned_zone(zone: UnconditionedZone) -> ZoneInfo:
    """Transform an UnconditionedZone to a ZoneInfo."""
    return ZoneInfo(
        name=zone.name,
        zone_type="Unconditioned",
        status="New",
        floor_area=zone.floor_area,
        volume=zone.volume,
    )


def _transform_zones(takeoff: TakeoffSpec) -> List[ZoneInfo]:
    """Transform thermal boundary zones to BuildingSpec format."""
    zones = []

    for zone in takeoff.thermal_boundary.conditioned_zones:
        zones.append(_transform_conditioned_zone(zone))

    for zone in takeoff.thermal_boundary.unconditioned_zones:
        zones.append(_transform_unconditioned_zone(zone))

    return zones


# ============================================================================
# Ceiling Transformation
# ============================================================================

def _transform_ceiling(ceiling: CeilingEntry) -> CeilingComponent:
    """Transform a CeilingEntry to a CeilingComponent."""
    return CeilingComponent(
        name=ceiling.name,
        zone=ceiling.zone,
        status=ceiling.status,
        construction_type=ceiling.construction_type,
        orientation=ceiling.orientation,
        area=ceiling.area,
        roof_pitch=ceiling.roof_pitch,
        roof_tilt=ceiling.roof_tilt,
        roof_reflectance=ceiling.roof_reflectance,
        roof_emittance=ceiling.roof_emittance,
        framing_factor=ceiling.framing_factor,
    )


def _transform_ceilings(takeoff: TakeoffSpec) -> List[CeilingComponent]:
    """Transform cathedral/vaulted ceilings from TakeoffSpec to BuildingSpec format.

    Only includes cathedral/vaulted ceilings — NOT 'below attic' or standard ceilings.
    The ground truth CSV section 'Cathedral Ceilings:' only lists cathedral ceilings.
    Regular attic ceilings are tracked in a separate section ('Ceiling Below Attic:').
    """
    cathedral_ceilings = []
    for c in takeoff.ceilings:
        ceiling_type = (c.ceiling_type or "").lower()
        construction = (c.construction_type or "").lower()
        name_lower = (c.name or "").lower()
        # Only include if explicitly cathedral or vaulted
        is_cathedral = (
            "cathedral" in ceiling_type or "vaulted" in ceiling_type or
            "cathedral" in construction or "vaulted" in construction or
            "cathedral" in name_lower or "vaulted" in name_lower
        )
        if is_cathedral:
            cathedral_ceilings.append(_transform_ceiling(c))
    return cathedral_ceilings


# ============================================================================
# Slab Floor Transformation
# ============================================================================

def _transform_slab(slab: SlabEntry) -> SlabFloor:
    """Transform a SlabEntry to a SlabFloor."""
    return SlabFloor(
        name=slab.name,
        zone=slab.zone,
        status=slab.status,
        area=slab.area,
        perimeter=slab.perimeter,
        edge_insulation_r_value=slab.edge_insulation_r_value,
        carpeted_fraction=slab.carpeted_fraction,
        heated=slab.heated,
    )


def _transform_slabs(takeoff: TakeoffSpec) -> List[SlabFloor]:
    """Transform all slabs from TakeoffSpec to BuildingSpec format."""
    return [_transform_slab(s) for s in takeoff.slab_floors]


# ============================================================================
# HVAC Transformation
# ============================================================================

def _transform_hvac(hvac: HVACSystemEntry) -> HVACSystem:
    """Transform an HVACSystemEntry to an HVACSystem."""
    heating = None
    cooling = None
    distribution = None

    # Build heating info if available
    if hvac.hspf or hvac.afue or hvac.heating_capacity:
        heating = HeatPumpHeating(
            system_type=hvac.heating_type,
            hspf=hvac.hspf,
            capacity_47=hvac.heating_capacity,
            ducted=hvac.ducted,
        )

    # Build cooling info if available
    if hvac.seer2 or hvac.eer2 or hvac.cooling_capacity:
        cooling = HeatPumpCooling(
            system_type=hvac.cooling_type,
            seer2=hvac.seer2,
            eer2=hvac.eer2,
            ducted=hvac.ducted,
        )

    # Build distribution info if available
    if hvac.ducted is not None or hvac.duct_leakage_percent or hvac.duct_r_value:
        distribution = DistributionSystem(
            name=f"{hvac.name} Distribution",
            system_type=hvac.duct_location,
            percent_leakage=hvac.duct_leakage_percent,
            insulation_r_value=hvac.duct_r_value,
        )

    return HVACSystem(
        name=hvac.name,
        status=hvac.status,
        system_type=hvac.system_type,
        heating=heating,
        cooling=cooling,
        distribution=distribution,
    )


def _transform_hvac_systems(takeoff: TakeoffSpec) -> List[HVACSystem]:
    """Transform all HVAC systems from TakeoffSpec to BuildingSpec format."""
    return [_transform_hvac(h) for h in takeoff.hvac_systems]


# ============================================================================
# DHW Transformation
# ============================================================================

def _transform_dhw(dhw: DHWSystem) -> WaterHeatingSystem:
    """Transform a DHWSystem to a WaterHeatingSystem."""
    water_heater = WaterHeater(
        name=dhw.name,
        fuel=dhw.fuel,
        tank_type=dhw.system_type,
        volume=dhw.tank_volume,
        energy_factor=dhw.energy_factor,
        input_rating=dhw.input_rating,
        input_rating_units=dhw.input_rating_units,
        recovery_efficiency=dhw.recovery_efficiency,
        tank_location=dhw.location,
    )

    return WaterHeatingSystem(
        name=dhw.name,
        status=dhw.status,
        system_type=dhw.system_type,
        water_heaters=[water_heater],
    )


def _transform_dhw_systems(takeoff: TakeoffSpec) -> List[WaterHeatingSystem]:
    """Transform all DHW systems from TakeoffSpec to BuildingSpec format."""
    return [_transform_dhw(d) for d in takeoff.dhw_systems]


# ============================================================================
# Project/Envelope Transformation
# ============================================================================

def _transform_project(takeoff: TakeoffSpec) -> ProjectInfo:
    """Transform TakeoffProjectInfo to ProjectInfo."""
    proj = takeoff.project
    return ProjectInfo(
        run_id=proj.run_id,
        run_title=proj.run_title,
        run_number=proj.run_number,
        run_scope=proj.run_scope,
        address=proj.address,
        city=proj.city,
        climate_zone=proj.climate_zone,
        standards_version=proj.standards_version,
        all_orientations=proj.all_orientations,
        fuel_type=proj.fuel_type,
        house_type=proj.house_type,
        dwelling_units=proj.dwelling_units,
        stories=proj.stories,
        bedrooms=proj.bedrooms,
        attached_garage=proj.attached_garage,
        front_orientation=proj.front_orientation,
        orientation_confidence=proj.orientation_confidence,
        orientation_verification=proj.orientation_verification,
    )


def _transform_envelope(takeoff: TakeoffSpec) -> EnvelopeInfo:
    """Build EnvelopeInfo from TakeoffSpec data."""
    proj = takeoff.project

    # Calculate totals from house_walls if not specified
    total_wall_area = 0.0
    total_window_area = 0.0
    for _, wall in takeoff.house_walls.get_all_walls():
        if wall.gross_wall_area:
            total_wall_area += wall.gross_wall_area
        total_window_area += wall.total_fenestration_area

    # Use project values if available, otherwise calculated
    wall_area = proj.exterior_wall_area if proj.exterior_wall_area else total_wall_area
    window_area = proj.window_area if proj.window_area else total_window_area

    # Calculate slab area from slab_floors
    slab_area = sum(s.area or 0 for s in takeoff.slab_floors)

    return EnvelopeInfo(
        conditioned_floor_area=proj.conditioned_floor_area,
        window_area=window_area if window_area > 0 else None,
        window_to_floor_ratio=proj.window_to_floor_ratio,
        exterior_wall_area=wall_area if wall_area > 0 else None,
        slab_floor_area=slab_area if slab_area > 0 else None,
    )


# ============================================================================
# Main Transform Function
# ============================================================================

def transform_takeoff_to_building_spec(takeoff: TakeoffSpec) -> BuildingSpec:
    """Convert orientation-based TakeoffSpec to component-list BuildingSpec.

    This is the main transformation function that converts:
    - house_walls (orientation-based) → walls[] + windows[] (component lists)
    - thermal_boundary → zones[]
    - Nested fenestration → flat windows list with wall references

    Args:
        takeoff: TakeoffSpec with orientation-based structure

    Returns:
        BuildingSpec with component-list structure for verification
    """
    return BuildingSpec(
        project=_transform_project(takeoff),
        envelope=_transform_envelope(takeoff),
        zones=_transform_zones(takeoff),
        walls=_transform_walls(takeoff),
        windows=_transform_windows(takeoff),
        ceilings=_transform_ceilings(takeoff),
        slab_floors=_transform_slabs(takeoff),
        hvac_systems=_transform_hvac_systems(takeoff),
        water_heating_systems=_transform_dhw_systems(takeoff),
    )
