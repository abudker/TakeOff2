"""Shared enums used across both BuildingSpec and TakeoffSpec schemas."""
from enum import Enum


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


class Orientation(str, Enum):
    """Cardinal orientation labels."""
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


class FlagSeverity(str, Enum):
    """Uncertainty flag severity levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Error types used in verification and improvement modules
ERROR_TYPES = ("omission", "hallucination", "wrong_value", "format_error")

# Metric names used across the codebase
METRIC_NAMES = ("f1", "precision", "recall")
