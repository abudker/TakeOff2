"""CV Sensors - Deterministic geometric measurements from architectural PDFs.

This module provides computer vision-based angle detection for north arrows
and wall edges, eliminating the variance in LLM-based visual estimation.

Public API:
    detect_north_arrow_angle: Find north arrow and return compass bearing
    measure_wall_edge_angles: Detect building wall edges with precise angles
    render_page_to_numpy: Convert PDF page to NumPy array for CV processing
"""

from .north_arrow import detect_north_arrow_angle
from .wall_detection import measure_wall_edge_angles, estimate_building_rotation
from .rendering import render_page_to_numpy

__all__ = [
    "detect_north_arrow_angle",
    "measure_wall_edge_angles",
    "estimate_building_rotation",
    "render_page_to_numpy",
]
