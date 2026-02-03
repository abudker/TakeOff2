"""Pydantic models for building specification extraction output."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class FuelType(str, Enum):
    ALL_ELECTRIC = "All Electric"
    NATURAL_GAS = "Natural Gas"
    MIXED = "Mixed"


class HouseType(str, Enum):
    SINGLE_FAMILY = "Single Family"
    MULTI_FAMILY = "Multi Family"


class ProjectInfo(BaseModel):
    """Project metadata."""
    run_title: str = Field(description="Project title")
    address: str = Field(description="Street address")
    city: str = Field(description="City name")
    climate_zone: int = Field(ge=1, le=16, description="CA climate zone 1-16")
    fuel_type: FuelType = Field(description="Fuel type")
    house_type: HouseType = Field(description="House type")
    dwelling_units: int = Field(ge=1, description="Number of dwelling units")
    stories: int = Field(ge=1, description="Number of stories")
    bedrooms: int = Field(ge=0, description="Number of bedrooms")


class EnvelopeInfo(BaseModel):
    """Building envelope data."""
    conditioned_floor_area: float = Field(gt=0, description="CFA in sq ft")
    window_area: float = Field(ge=0, description="Total window area sq ft")
    window_to_floor_ratio: float = Field(ge=0, le=1, description="WWR")
    exterior_wall_area: float = Field(ge=0, description="Exterior wall area sq ft")
    fenestration_u_factor: Optional[float] = Field(default=None, description="Area-weighted U-factor")


class ZoneInfo(BaseModel):
    """Zone data."""
    name: str
    floor_area: float = Field(ge=0)
    volume: float = Field(ge=0)


class WallInfo(BaseModel):
    """Wall data."""
    name: str
    orientation: str
    area: float = Field(ge=0)
    r_value: Optional[float] = Field(default=None, ge=0)


class WindowInfo(BaseModel):
    """Window/fenestration data."""
    name: str
    area: float = Field(ge=0)
    u_factor: Optional[float] = Field(default=None)
    shgc: Optional[float] = Field(default=None)


class HVACSystem(BaseModel):
    """HVAC system data."""
    name: str
    system_type: str
    heating_capacity: Optional[float] = None
    cooling_capacity: Optional[float] = None
    efficiency_heating: Optional[float] = None  # HSPF, AFUE
    efficiency_cooling: Optional[float] = None  # SEER


class WaterHeater(BaseModel):
    """Water heater data."""
    name: str
    system_type: str
    capacity: Optional[float] = None
    efficiency: Optional[float] = None  # EF or UEF


class BuildingSpec(BaseModel):
    """Complete building specification from extraction."""
    project: ProjectInfo
    envelope: EnvelopeInfo
    zones: List[ZoneInfo] = Field(default_factory=list)
    walls: List[WallInfo] = Field(default_factory=list)
    windows: List[WindowInfo] = Field(default_factory=list)
    hvac_systems: List[HVACSystem] = Field(default_factory=list)
    water_heaters: List[WaterHeater] = Field(default_factory=list)
