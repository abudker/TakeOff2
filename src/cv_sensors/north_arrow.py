"""North arrow detection using computer vision.

Detects north arrows on architectural site plans and returns the compass bearing.
Uses line detection (Hough) and contour-based methods for robustness.
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from .rendering import render_page_to_numpy
from .preprocessing import preprocess_for_lines, preprocess_for_contours

# --- Detection constants ---
# Corner search: fraction of page width/height to search in each corner
CORNER_SEARCH_FRACTION = 0.25

# Hough line detection parameters
LINE_HOUGH_THRESHOLD = 50
LINE_HOUGH_MIN_LENGTH = 30
LINE_HOUGH_MAX_GAP = 5

# Arrow length bounds (pixels at default zoom)
MIN_ARROW_LENGTH = 30   # Below this = noise
MAX_ARROW_LENGTH = 250  # Above this = page border / dimension line

# Lines within this many degrees of a cardinal axis are "axis-aligned"
AXIS_TOLERANCE_DEG = 15

# Confidence thresholds based on longest line length
LINE_CONFIDENCE_MEDIUM_THRESHOLD = 80
LINE_CONFIDENCE_LOW_THRESHOLD = 50

# Contour area bounds for arrow tip detection
MIN_CONTOUR_AREA = 100
MAX_CONTOUR_AREA = 10000

# Max angular difference for line+contour agreement
AGREEMENT_THRESHOLD_DEG = 20


def _no_detection(method: str = "none", debug: Optional[Dict] = None) -> Dict[str, Any]:
    """Return a standard 'no detection' result."""
    return {
        "angle": None,
        "confidence": "none",
        "method": method,
        "debug": debug or {},
    }


def _circular_mean_degrees(angles: List[float]) -> float:
    """Compute circular mean of angles in degrees [0, 360).

    Handles wraparound correctly (e.g., mean of 355 and 5 = 0, not 180).
    """
    rads = np.radians(angles)
    mean_sin = np.mean(np.sin(rads))
    mean_cos = np.mean(np.cos(rads))
    return float(np.degrees(np.arctan2(mean_sin, mean_cos)) % 360)


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

    # Define search regions (corner margins) if not specified
    if search_region is None:
        # Search 25% corner regions — north arrows appear in margins/corners,
        # not page center. Smaller regions exclude page borders.
        margin_w = int(w * 0.25)
        margin_h = int(h * 0.25)
        search_regions = [
            (w - margin_w, h - margin_h, margin_w, margin_h),  # Bottom-right
            (0, h - margin_h, margin_w, margin_h),              # Bottom-left
            (w - margin_w, 0, margin_w, margin_h),              # Top-right
            (0, 0, margin_w, margin_h),                         # Top-left
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
        threshold=LINE_HOUGH_THRESHOLD,
        minLineLength=LINE_HOUGH_MIN_LENGTH,
        maxLineGap=LINE_HOUGH_MAX_GAP,
    )

    if lines is None or len(lines) == 0:
        return _no_detection("lines", {"lines_count": 0, "longest_line_length": 0})

    candidates = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if MIN_ARROW_LENGTH <= length <= MAX_ARROW_LENGTH:
            dy = y2 - y1
            dx = x2 - x1
            compass = (90 - np.degrees(np.arctan2(-dy, dx))) % 360
            candidates.append((x1, y1, x2, y2, length, compass))

    if not candidates:
        return _no_detection("lines", {"lines_count": len(lines), "filtered_count": 0})

    # Prefer non-axis-aligned lines: architectural drawings are full of
    # horizontal (90/270) and vertical (0/180) lines from dimensions,
    # text, and borders. A tilted north arrow stands out as non-axis-aligned.
    non_axis = []
    axis_aligned = []
    for c in candidates:
        compass = c[5]
        near_axis = any(
            abs((compass - a + 180) % 360 - 180) < AXIS_TOLERANCE_DEG
            for a in [0, 90, 180, 270]
        )
        if near_axis:
            axis_aligned.append(c)
        else:
            non_axis.append(c)

    # Use non-axis lines if available (more likely to be the arrow)
    if non_axis:
        non_axis.sort(key=lambda c: c[4], reverse=True)
        best_line = non_axis[0][:4]
        max_length = non_axis[0][4]
    else:
        # Only axis-aligned lines found — likely not the arrow, just drawing elements.
        return _no_detection("lines", {
            "lines_count": len(lines),
            "filtered_count": len(candidates),
            "all_axis_aligned": True,
        })

    # Calculate angle
    x1, y1, x2, y2 = best_line
    dx = x2 - x1
    dy = y2 - y1

    # CRITICAL: Negate dy because y increases downward in image coordinates
    math_angle_deg = np.degrees(np.arctan2(-dy, dx))

    # Convert to compass bearing (0 = North, 90 = East, etc.)
    compass_bearing = (90 - math_angle_deg) % 360

    # Determine confidence based on line length
    if max_length > LINE_CONFIDENCE_MEDIUM_THRESHOLD:
        confidence = "medium"
    elif max_length > LINE_CONFIDENCE_LOW_THRESHOLD:
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
        return _no_detection("contours", {"contours_count": 0})

    # Look for triangular contours (arrow tips) with size filtering
    for contour in contours:
        # Skip contours that are too small (noise) or too large (page-level shapes)
        area = cv2.contourArea(contour)
        if area < MIN_CONTOUR_AREA or area > MAX_CONTOUR_AREA:
            continue

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

    return _no_detection("contours", {"contours_count": len(contours)})


def _combine_results(
    line_result: Dict[str, Any],
    contour_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Combine line and contour detection results."""
    line_angle = line_result.get("angle")
    contour_angle = contour_result.get("angle")

    # If both methods agree (within threshold), combine them
    if line_angle is not None and contour_angle is not None:
        angle_diff = abs(line_angle - contour_angle)
        # Handle wraparound (e.g., 355 vs 5 degrees)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        if angle_diff <= AGREEMENT_THRESHOLD_DEG:
            # Use circular mean to handle 0/360 boundary correctly
            avg_angle = _circular_mean_degrees([line_angle, contour_angle])
            # Only upgrade to "high" if line method had at least "medium" confidence
            # (i.e., found a line in the valid arrow-size range with decent length)
            line_conf = line_result.get("confidence", "none")
            combined_conf = "high" if line_conf in ("medium", "high") else "medium"
            return {
                "angle": avg_angle,
                "confidence": combined_conf,
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
    return _no_detection("none", {
        "line": line_result["debug"],
        "contour": contour_result["debug"],
    })
