"""Image preprocessing pipelines for CV detection tasks.

Provides standard preprocessing operations for line/edge detection
and contour-based shape detection.
"""

import cv2
import numpy as np


def preprocess_for_lines(
    img: np.ndarray,
    canny_low: int = 50,
    canny_high: int = 150
) -> np.ndarray:
    """Preprocess image for line detection (Hough transform).

    Pipeline:
        RGB -> Grayscale -> Gaussian Blur -> Canny Edge Detection

    Args:
        img: Input RGB image (H, W, 3)
        canny_low: Lower threshold for Canny edge detection
        canny_high: Upper threshold for Canny edge detection

    Returns:
        Binary edge image (H, W) with dtype uint8
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny edge detection
    edges = cv2.Canny(blurred, canny_low, canny_high)

    return edges


def preprocess_for_contours(img: np.ndarray) -> np.ndarray:
    """Preprocess image for contour detection (shape finding).

    Pipeline:
        RGB -> Grayscale -> Otsu Threshold -> Morphological Close

    Args:
        img: Input RGB image (H, W, 3)

    Returns:
        Binary image (H, W) with dtype uint8, suitable for findContours
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Otsu's thresholding
    _, binary = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    # Morphological closing to fill small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return closed
