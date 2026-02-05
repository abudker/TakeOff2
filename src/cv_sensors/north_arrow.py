"""North arrow detection using computer vision.

Detects north arrows on architectural site plans and returns the compass bearing.
Uses line detection (Hough) and contour-based methods for robustness.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any
from .rendering import render_page_to_numpy
from .preprocessing import preprocess_for_lines, preprocess_for_contours


def detect_north_arrow_angle(
    pdf_path: str,
    page_num: int,
    search_region: Optional[Tuple[int, int, int, int]] = None,
    zoom: float = 2.0
) -> Dict[str, Any]:
    """Detect north arrow angle on a PDF page using computer vision.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        search_region: Optional (x, y, width, height) region to search
        zoom: Rendering zoom factor (default: 2.0)

    Returns:
        Dict with keys:
            - angle: float compass bearing [0, 360) or None if not detected
            - confidence: "high", "medium", "low", or "none"
            - method: Description of detection method used
            - debug: Dict with detection details (lines, contours, raw angles)

    Coordinate System Notes:
        - OpenCV origin is top-left, y increases downward
        - arctan2(-dy, dx) corrects for inverted y-axis
        - compass_bearing = (90 - math_angle_degrees) % 360
    """
    # Render page
    img = render_page_to_numpy(pdf_path, page_num, zoom)
    h, w = img.shape[:2]

    # Define search regions (quadrants) if not specified
    if search_region is None:
        # Search bottom-right and bottom-left quadrants (common arrow locations)
        search_regions = [
            (w // 2, h // 2, w // 2, h // 2),  # Bottom-right
            (0, h // 2, w // 2, h // 2),        # Bottom-left
            (w // 2, 0, w // 2, h // 2),        # Top-right
            (0, 0, w // 2, h // 2),             # Top-left
        ]
    else:
        search_regions = [search_region]

    best_result = None
    best_confidence_score = 0

    for region in search_regions:
        x, y, rw, rh = region
        region_img = img[y:y+rh, x:x+rw]

        # Try line-based detection
        line_result = _detect_via_lines(region_img)

        # Try contour-based detection
        contour_result = _detect_via_contours(region_img)

        # Combine results
        result = _combine_results(line_result, contour_result)

        # Track best result across regions
        confidence_scores = {"high": 3, "medium": 2, "low": 1, "none": 0}
        score = confidence_scores.get(result["confidence"], 0)
        if score > best_confidence_score:
            best_confidence_score = score
            best_result = result

    return best_result


def _detect_via_lines(img: np.ndarray) -> Dict[str, Any]:
    """Detect north arrow via Hough line detection."""
    edges = preprocess_for_lines(img)

    # Detect lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=30,
        maxLineGap=5
    )

    if lines is None or len(lines) == 0:
        return {
            "angle": None,
            "confidence": "none",
            "method": "lines",
            "debug": {"lines_count": 0, "longest_line_length": 0}
        }

    # Find longest line (likely arrow shaft)
    max_length = 0
    best_line = None

    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if length > max_length:
            max_length = length
            best_line = (x1, y1, x2, y2)

    if best_line is None:
        return {
            "angle": None,
            "confidence": "none",
            "method": "lines",
            "debug": {"lines_count": len(lines), "longest_line_length": 0}
        }

    # Calculate angle
    x1, y1, x2, y2 = best_line
    dx = x2 - x1
    dy = y2 - y1

    # CRITICAL: Negate dy because y increases downward in image coordinates
    math_angle_deg = np.degrees(np.arctan2(-dy, dx))

    # Convert to compass bearing (0 = North, 90 = East, etc.)
    compass_bearing = (90 - math_angle_deg) % 360

    # Determine confidence based on line length
    if max_length > 80:
        confidence = "medium"
    elif max_length > 50:
        confidence = "low"
    else:
        confidence = "none"
        compass_bearing = None

    return {
        "angle": compass_bearing,
        "confidence": confidence,
        "method": "lines",
        "debug": {
            "lines_count": len(lines),
            "longest_line_length": float(max_length),
            "raw_math_angle": float(math_angle_deg),
            "line_coords": best_line
        }
    }


def _detect_via_contours(img: np.ndarray) -> Dict[str, Any]:
    """Detect north arrow via contour detection (arrow tip)."""
    binary = preprocess_for_contours(img)

    # Find contours
    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return {
            "angle": None,
            "confidence": "none",
            "method": "contours",
            "debug": {"contours_count": 0}
        }

    # Look for triangular contours (arrow tips)
    for contour in contours:
        # Approximate polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

        # Arrow tips typically have 3-5 vertices
        if len(approx) >= 3 and len(approx) <= 5:
            # Get orientation via minAreaRect
            rect = cv2.minAreaRect(contour)
            angle = rect[2]  # Angle in range [-90, 0)

            # Convert minAreaRect angle to compass bearing
            # minAreaRect returns angle of rectangle's width relative to horizontal
            # We need to normalize this to [0, 360) compass bearing
            if angle < -45:
                angle = 90 + angle
            else:
                angle = angle

            compass_bearing = (90 - angle) % 360

            return {
                "angle": compass_bearing,
                "confidence": "low",  # Contour method alone is less reliable
                "method": "contours",
                "debug": {
                    "contours_count": len(contours),
                    "vertices": len(approx),
                    "raw_rect_angle": float(rect[2])
                }
            }

    return {
        "angle": None,
        "confidence": "none",
        "method": "contours",
        "debug": {"contours_count": len(contours)}
    }


def _combine_results(
    line_result: Dict[str, Any],
    contour_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Combine line and contour detection results."""
    line_angle = line_result.get("angle")
    contour_angle = contour_result.get("angle")

    # If both methods agree (within 20 degrees), high confidence
    if line_angle is not None and contour_angle is not None:
        angle_diff = abs(line_angle - contour_angle)
        # Handle wraparound (e.g., 355 vs 5 degrees)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        if angle_diff <= 20:
            # Average the angles
            avg_angle = (line_angle + contour_angle) / 2
            return {
                "angle": avg_angle,
                "confidence": "high",
                "method": "lines+contours",
                "debug": {
                    "line": line_result["debug"],
                    "contour": contour_result["debug"],
                    "angle_agreement": float(angle_diff)
                }
            }

    # If only one method succeeded, use it
    if line_angle is not None:
        return line_result

    if contour_angle is not None:
        return contour_result

    # Both failed
    return {
        "angle": None,
        "confidence": "none",
        "method": "none",
        "debug": {
            "line": line_result["debug"],
            "contour": contour_result["debug"]
        }
    }
