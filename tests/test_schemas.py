"""Tests for schema models and enums."""
import pytest
from schemas.enums import (
    FuelType, HouseType, RunScope, ComponentStatus, ZoneType,
    HVACSystemType, WaterHeaterType, WaterHeaterFuel,
    Orientation, FlagSeverity,
    ERROR_TYPES, METRIC_NAMES,
)
from schemas.building_spec import ProjectInfo, ProjectInfoBase, BuildingSpec
from schemas.takeoff_spec import TakeoffSpec, TakeoffProjectInfo


class TestEnums:
    def test_fuel_type_values(self):
        assert FuelType.ALL_ELECTRIC.value == "All Electric"
        assert FuelType.NATURAL_GAS.value == "Natural Gas"
        assert FuelType.MIXED.value == "Mixed"

    def test_orientation_values(self):
        assert Orientation.NORTH.value == "north"
        assert Orientation.EAST.value == "east"
        assert Orientation.SOUTH.value == "south"
        assert Orientation.WEST.value == "west"

    def test_flag_severity_values(self):
        assert FlagSeverity.HIGH.value == "high"
        assert FlagSeverity.MEDIUM.value == "medium"
        assert FlagSeverity.LOW.value == "low"

    def test_error_types_constant(self):
        assert "omission" in ERROR_TYPES
        assert "hallucination" in ERROR_TYPES
        assert "wrong_value" in ERROR_TYPES
        assert "format_error" in ERROR_TYPES

    def test_metric_names_constant(self):
        assert "f1" in METRIC_NAMES
        assert "precision" in METRIC_NAMES
        assert "recall" in METRIC_NAMES

    def test_enums_are_str(self):
        """All enums should be str subclasses for JSON serialization."""
        assert isinstance(FuelType.ALL_ELECTRIC, str)
        assert isinstance(Orientation.NORTH, str)
        assert isinstance(FlagSeverity.HIGH, str)


class TestProjectInfo:
    def test_project_info_inherits_base(self):
        assert issubclass(ProjectInfo, ProjectInfoBase)

    def test_project_info_defaults(self):
        info = ProjectInfo()
        assert info.run_id is None
        assert info.climate_zone is None
        assert info.front_orientation is None

    def test_project_info_with_values(self):
        info = ProjectInfo(
            run_id="test-001",
            climate_zone=12,
            front_orientation=90.0,
        )
        assert info.run_id == "test-001"
        assert info.climate_zone == 12
        assert info.front_orientation == 90.0

    def test_project_info_climate_zone_validation(self):
        with pytest.raises(Exception):
            ProjectInfo(climate_zone=0)
        with pytest.raises(Exception):
            ProjectInfo(climate_zone=17)


class TestTakeoffProjectInfo:
    def test_defaults(self):
        info = TakeoffProjectInfo()
        assert info.attached_garage is False
        assert info.conditioned_floor_area is None

    def test_front_orientation_validation(self):
        info = TakeoffProjectInfo(front_orientation=180.0)
        assert info.front_orientation == 180.0

        with pytest.raises(Exception):
            TakeoffProjectInfo(front_orientation=360.0)
