"""Wall edge detection and building rotation estimation using computer vision.

Detects building wall edges on site plans and estimates overall building rotation
by clustering parallel wall angles.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .rendering import render_page_to_numpy
from .preprocessing import preprocess_for_lines


def measure_wall_edge_angles(
    pdf_path: str,
    page_num: int,
    building_region: Optional[Tuple[int, int, int, int]] = None,
    zoom: float = 2.0
) -> List[Dict[str, Any]]:
    """Measure wall edge angles on a site plan.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        building_region: Optional (x, y, width, height) region to search
        zoom: Rendering zoom factor (default: 2.0)

    Returns:
        List of wall edge dicts (max 8), sorted by length descending:
            - angle_from_horizontal: float in [0, 180)
            - length: float (line length in pixels)
            - position: str ("top", "right", "bottom", "left", "center")
            - perpendicular_angle: float in [0, 360) (outward normal)
    """
    # Render page
    img = render_page_to_numpy(pdf_path, page_num, zoom)
    h, w = img.shape[:2]

    # Apply region mask if specified
    if building_region is not None:
        x, y, rw, rh = building_region
        region_img = img[y:y+rh, x:x+rw]
        offset_x, offset_y = x, y
    else:
        region_img = img
        offset_x, offset_y = 0, 0

    # Preprocess for line detection
    edges = preprocess_for_lines(region_img)

    # Detect lines with higher thresholds for building walls
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=20
    )

    if lines is None or len(lines) == 0:
        return []

    wall_edges = []

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Convert to absolute coordinates
        x1 += offset_x
        x2 += offset_x
        y1 += offset_y
        y2 += offset_y

        # Calculate angle from horizontal
        dx = x2 - x1
        dy = y2 - y1
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad)

        # Normalize to [0, 180) (direction doesn't matter for walls)
        angle_from_horizontal = angle_deg % 180

        # Calculate line length
        length = np.sqrt(dx**2 + dy**2)

        # Determine position relative to image
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        position = _determine_position(center_x, center_y, w, h)

        # Calculate perpendicular (outward normal) angle
        perpendicular_angle = (angle_from_horizontal + 90) % 360

        wall_edges.append({
            "angle_from_horizontal": float(angle_from_horizontal),
            "length": float(length),
            "position": position,
            "perpendicular_angle": float(perpendicular_angle)
        })

    # Sort by length descending, return top 8
    wall_edges.sort(key=lambda x: x["length"], reverse=True)
    return wall_edges[:8]


def estimate_building_rotation(
    pdf_path: str,
    page_num: int,
    building_region: Optional[Tuple[int, int, int, int]] = None,
    zoom: float = 2.0
) -> Dict[str, Any]:
    """Estimate building rotation from wall edge clustering.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        building_region: Optional (x, y, width, height) region to search
        zoom: Rendering zoom factor (default: 2.0)

    Returns:
        Dict with keys:
            - rotation_from_horizontal: float in [0, 180)
            - confidence: "high", "medium", "low", or "none"
            - dominant_angles: List[float] (angles in the dominant cluster)
    """
    # Get wall edges
    wall_edges = measure_wall_edge_angles(pdf_path, page_num, building_region, zoom)

    if len(wall_edges) < 2:
        return {
            "rotation_from_horizontal": 0.0,
            "confidence": "none",
            "dominant_angles": []
        }

    # Extract angles for clustering
    angles = [edge["angle_from_horizontal"] for edge in wall_edges]

    # Cluster angles into two groups (parallel pairs for rectangular buildings)
    # Use simple k-means-like clustering with k=2
    clusters = _cluster_angles(angles, k=2)

    # Find dominant cluster (most lines or highest total length)
    cluster_weights = []
    for cluster in clusters:
        total_length = sum(
            wall_edges[i]["length"]
            for i in range(len(wall_edges))
            if wall_edges[i]["angle_from_horizontal"] in cluster
        )
        cluster_weights.append(total_length)

    dominant_idx = np.argmax(cluster_weights)
    dominant_cluster = clusters[dominant_idx]

    # Calculate mean angle of dominant cluster
    rotation = np.mean(dominant_cluster)

    # Calculate confidence based on cluster tightness
    std_dev = np.std(dominant_cluster)
    if std_dev < 5:
        confidence = "high"
    elif std_dev < 10:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "rotation_from_horizontal": float(rotation),
        "confidence": confidence,
        "dominant_angles": [float(a) for a in dominant_cluster]
    }


def _determine_position(x: float, y: float, w: int, h: int) -> str:
    """Determine position label based on line center coordinates."""
    # Divide image into 3x3 grid
    third_w = w / 3
    third_h = h / 3

    if y < third_h:
        if x < third_w:
            return "top-left"
        elif x < 2 * third_w:
            return "top"
        else:
            return "top-right"
    elif y < 2 * third_h:
        if x < third_w:
            return "left"
        elif x < 2 * third_w:
            return "center"
        else:
            return "right"
    else:
        if x < third_w:
            return "bottom-left"
        elif x < 2 * third_w:
            return "bottom"
        else:
            return "bottom-right"


def _cluster_angles(angles: List[float], k: int = 2) -> List[List[float]]:
    """Simple angle clustering using k-means-like approach.

    Args:
        angles: List of angles in [0, 180)
        k: Number of clusters (default: 2 for rectangular buildings)

    Returns:
        List of k clusters, each containing a list of angles
    """
    if len(angles) <= k:
        # Not enough angles to cluster
        return [[a] for a in angles]

    # Initialize cluster centers (evenly spaced)
    centers = [i * (180 / k) for i in range(k)]

    # Iterate a few times to converge
    for _ in range(10):
        # Assign angles to nearest cluster
        clusters = [[] for _ in range(k)]
        for angle in angles:
            # Find nearest center
            distances = [_angular_distance(angle, center) for center in centers]
            nearest_idx = np.argmin(distances)
            clusters[nearest_idx].append(angle)

        # Update centers
        new_centers = []
        for cluster in clusters:
            if len(cluster) > 0:
                new_centers.append(np.mean(cluster))
            else:
                # Keep old center if cluster is empty
                new_centers.append(centers[len(new_centers)])
        centers = new_centers

    return [c for c in clusters if len(c) > 0]


def _angular_distance(angle1: float, angle2: float) -> float:
    """Calculate angular distance in [0, 180) space."""
    diff = abs(angle1 - angle2)
    # Handle wraparound (e.g., 5 vs 175 degrees)
    if diff > 90:
        diff = 180 - diff
    return diff
