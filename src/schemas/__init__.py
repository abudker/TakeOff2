"""Takeoff v2 Schemas - Pydantic models for extraction output."""
from .building_spec import BuildingSpec
from .discovery import DocumentMap, PageInfo, PageType
from .takeoff_spec import (
    TakeoffSpec,
    TakeoffProjectInfo,
    HouseWalls,
    OrientationWall,
    FenestrationEntry,
    OpaqueDoorEntry,
    ThermalBoundary,
    ConditionedZone,
    UnconditionedZone,
    CeilingEntry,
    SlabEntry,
    HVACSystemEntry,
    DHWSystem,
    UncertaintyFlag,
    AssumptionEntry,
)
from .transform import transform_takeoff_to_building_spec

__all__ = [
    # BuildingSpec (component-list format)
    "BuildingSpec",
    # Discovery
    "DocumentMap",
    "PageInfo",
    "PageType",
    # TakeoffSpec (orientation-based format)
    "TakeoffSpec",
    "TakeoffProjectInfo",
    "HouseWalls",
    "OrientationWall",
    "FenestrationEntry",
    "OpaqueDoorEntry",
    "ThermalBoundary",
    "ConditionedZone",
    "UnconditionedZone",
    "CeilingEntry",
    "SlabEntry",
    "HVACSystemEntry",
    "DHWSystem",
    "UncertaintyFlag",
    "AssumptionEntry",
    # Transformation
    "transform_takeoff_to_building_spec",
]
