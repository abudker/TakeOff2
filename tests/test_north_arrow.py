"""Tests for CV sensor north arrow detection utilities."""
import pytest
import numpy as np


class TestCircularMean:
    """Test circular mean independently (avoids pymupdf dependency)."""

    @staticmethod
    def _circular_mean_degrees(angles):
        """Reimplementation for testing without pymupdf dependency."""
        rads = np.radians(angles)
        mean_sin = np.mean(np.sin(rads))
        mean_cos = np.mean(np.cos(rads))
        return float(np.degrees(np.arctan2(mean_sin, mean_cos)) % 360)

    def test_simple_average(self):
        """Regular angles should give regular mean."""
        result = self._circular_mean_degrees([10.0, 20.0])
        assert abs(result - 15.0) < 0.1

    def test_wraparound(self):
        """Angles near 0/360 boundary should average correctly."""
        result = self._circular_mean_degrees([350.0, 10.0])
        assert abs(result - 0.0) < 0.1 or abs(result - 360.0) < 0.1

    def test_wraparound_near_180(self):
        """Angles near 180 should average correctly."""
        result = self._circular_mean_degrees([170.0, 190.0])
        assert abs(result - 180.0) < 0.1

    def test_single_angle(self):
        """Single angle should return itself."""
        result = self._circular_mean_degrees([45.0])
        assert abs(result - 45.0) < 0.01

    def test_opposite_angles(self):
        """Diametrically opposed angles."""
        result = self._circular_mean_degrees([0.0, 180.0])
        assert result == pytest.approx(90.0, abs=0.1) or result == pytest.approx(270.0, abs=0.1)

    def test_three_angles_wraparound(self):
        """Three angles near 0/360."""
        result = self._circular_mean_degrees([355.0, 0.0, 5.0])
        assert abs(result - 0.0) < 1.0 or abs(result - 360.0) < 1.0
