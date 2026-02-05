# Phase 7: CV Sensors - Research

**Researched:** 2026-02-05
**Domain:** Computer Vision for Architectural Drawing Analysis
**Confidence:** MEDIUM

## Summary

Phase 7 aims to reduce orientation extraction variance by introducing deterministic computer vision (CV) sensors that detect geometric features in architectural PDFs. The current LLM two-pass system has high run-to-run variance (poonian-adu: 30% pass rate, lamb-adu: 30% pass rate) due to inconsistent angle estimation. CV can provide deterministic measurements that are identical across runs.

The standard approach combines OpenCV for line/angle detection with PyMuPDF for PDF rendering. The CV layer will detect:
1. **North arrow angle** - Precise arrow tip direction measurement
2. **Building footprint rotation** - Wall edge angles on site plans
3. **Entry wall orientation** - Precise angle of entry wall edge

These measurements become structured hints to the LLM passes, reducing the cognitive load of angle estimation while preserving LLM reasoning for semantic understanding (which elevation is the entry, what building type, etc.).

**Primary recommendation:** Use OpenCV's HoughLinesP for wall edge detection and contour analysis with minAreaRect for north arrow orientation. Render PDF pages to NumPy arrays via PyMuPDF's get_pixmap(), preprocess with Canny edge detection and Gaussian blur, then extract angles. Keep CV sensors as pure measurement functions that return structured data to LLM prompts.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| opencv-python | 4.x | Line detection, angle measurement, contour analysis | Industry standard for CV, well-documented, optimized C++ core |
| pymupdf | 1.26+ | PDF page rendering to images, already in project | Already project dependency, no external binaries needed |
| numpy | Latest | Array operations for image processing | Required by OpenCV, efficient numerical operations |

**Note:** Project already has `pymupdf>=1.26` and `pillow>=10.0` in pyproject.toml. Only need to add `opencv-python`.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | Latest | Advanced image processing (optional) | If Gaussian blur needs more control than cv2.GaussianBlur |
| scikit-image | Latest | Python-native CV algorithms | If OpenCV installation issues arise (fallback) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| opencv-python | scikit-image | Easier install, more Pythonic API, but 10-50x slower for real-time tasks |
| opencv-python | opencv-contrib-python | Includes extra algorithms (arrow detection via template matching), but larger package (450MB vs 90MB) |
| PyMuPDF rendering | pdf2image | Uses Poppler binary, more dependencies, slower |

**Installation:**
```bash
pip install opencv-python  # Add to pyproject.toml dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── cv_sensors/              # New CV sensor module
│   ├── __init__.py
│   ├── rendering.py         # PDF page → NumPy array conversion
│   ├── north_arrow.py       # North arrow angle detection
│   ├── wall_detection.py    # Building footprint wall edge detection
│   └── preprocessing.py     # Shared preprocessing (edge detection, blur)
└── agents/
    └── orchestrator.py      # Integrate CV sensor outputs into LLM prompts
```

### Pattern 1: PDF Page to NumPy Array
**What:** Render PDF pages to images compatible with OpenCV
**When to use:** Before any CV processing on PDF content
**Example:**
```python
# Source: PyMuPDF discussions + OpenCV integration patterns
import pymupdf
import numpy as np

def render_page_to_numpy(pdf_path: str, page_num: int, zoom: float = 2.0) -> np.ndarray:
    """Render PDF page to NumPy array for OpenCV processing.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        zoom: Zoom factor (2.0 = 2x resolution for better line detection)

    Returns:
        RGB NumPy array in OpenCV format (height, width, 3)
    """
    doc = pymupdf.open(pdf_path)
    page = doc[page_num - 1]  # PyMuPDF is 0-indexed

    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)  # alpha=False for white background

    # Convert to NumPy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    ).copy()  # .copy() required - pixmap buffer is read-only

    doc.close()
    return img
```

### Pattern 2: Edge Detection with Preprocessing
**What:** Standard preprocessing pipeline before line/contour detection
**When to use:** Before Hough Transform or contour analysis
**Example:**
```python
# Source: OpenCV official docs - Canny edge detection tutorial
import cv2

def preprocess_for_lines(img: np.ndarray) -> np.ndarray:
    """Preprocess image for line detection.

    Recommended pipeline:
    1. Convert to grayscale
    2. Gaussian blur to reduce noise
    3. Canny edge detection

    Args:
        img: Input RGB image (H, W, 3)

    Returns:
        Binary edge image (H, W) - white lines on black background
    """
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # 2. Reduce noise with Gaussian blur (kernel size must be odd)
    # Canny recommends this - edge detection is susceptible to noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 3. Canny edge detection
    # Threshold ratio 2:1 to 3:1 recommended by Canny
    # Adjust thresholds based on image contrast
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)

    return edges
```

### Pattern 3: Line Detection with Hough Transform
**What:** Detect straight lines for wall edges and north arrow shaft
**When to use:** After edge detection, when you need line segments with endpoints
**Example:**
```python
# Source: OpenCV official docs - Hough Line Transform
import cv2
import numpy as np

def detect_wall_edges(edges: np.ndarray, min_length: int = 100) -> list:
    """Detect straight lines using Probabilistic Hough Transform.

    Args:
        edges: Binary edge image from Canny
        min_length: Minimum line length in pixels

    Returns:
        List of line segments as ((x1, y1), (x2, y2), angle_degrees)
    """
    # HoughLinesP returns line segments directly (faster than HoughLines)
    # rho=1 pixel, theta=1 degree precision
    # threshold=minimum votes (line length proxy)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,  # 1 degree in radians
        threshold=80,        # Minimum votes
        minLineLength=min_length,
        maxLineGap=10        # Max gap to bridge broken lines
    )

    if lines is None:
        return []

    # Convert to (start, end, angle) format
    result = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Calculate angle from horizontal (0° = horizontal, 90° = vertical)
        angle_rad = np.arctan2(y2 - y1, x2 - x1)
        angle_deg = np.degrees(angle_rad)
        # Normalize to [0, 180) - lines have no direction
        if angle_deg < 0:
            angle_deg += 180
        result.append(((x1, y1), (x2, y2), angle_deg))

    return result
```

### Pattern 4: Contour Analysis for Arrow Tip Direction
**What:** Find arrow contours and determine tip orientation
**When to use:** For north arrow angle detection (arrow tip direction)
**Example:**
```python
# Source: OpenCV contour features documentation
import cv2
import numpy as np

def find_arrow_orientation(edges: np.ndarray) -> float:
    """Find arrow tip direction using contour analysis.

    Strategy:
    1. Find arrow contour (likely triangular)
    2. Fit minimum bounding rectangle (gives rotation angle)
    3. Determine tip direction from geometry

    Args:
        edges: Binary edge image (focused on north arrow region)

    Returns:
        Angle in degrees (0° = up/north, 90° = right/east, etc.)
    """
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Find largest contour (likely the arrow)
    arrow_contour = max(contours, key=cv2.contourArea)

    # Fit minimum area rectangle - returns (center, (width, height), angle)
    # Angle is [-90, 0) range (see Common Pitfalls)
    rect = cv2.minAreaRect(arrow_contour)
    center, (width, height), angle = rect

    # Convert angle to compass bearing
    # OpenCV angle is from horizontal, compass is from north
    compass_angle = (90 - angle) % 360

    return compass_angle
```

### Pattern 5: Hybrid CV + LLM Approach
**What:** CV provides measurements, LLM provides semantic reasoning
**When to use:** For complex tasks requiring both precision and understanding
**Example:**
```python
# Conceptual pattern - not actual code
def run_orientation_with_cv_hints(document_map, eval_dir):
    """Augment LLM extraction with CV-measured angles."""

    # 1. CV sensors measure precise angles
    cv_hints = {
        "north_arrow_angle": detect_north_arrow_angle(site_plan_page),
        "entry_wall_candidates": [
            {"angle": 85.3, "length": 245, "position": "right_edge"},
            {"angle": 5.1, "length": 312, "position": "top_edge"},
        ],
        "building_rotation": estimate_building_rotation(site_plan_page),
    }

    # 2. LLM uses CV hints for semantic reasoning
    prompt = f"""
    CV sensors detected these geometric features:
    - North arrow points at {cv_hints['north_arrow_angle']:.1f}° (±2°)
    - Entry wall candidates: {json.dumps(cv_hints['entry_wall_candidates'])}

    Now determine:
    1. Which elevation label (North/South/East/West) shows the entry door?
    2. Which wall candidate matches the entry elevation?
    3. Calculate front_orientation using the matched wall angle.

    Use CV angles directly - don't re-estimate them visually.
    """

    # 3. Verification compares CV + LLM result
    # If they disagree significantly, flag for review
```

### Anti-Patterns to Avoid
- **Don't replace LLM reasoning entirely:** CV can't identify which elevation is "North" or what building type it is. Use CV for measurements only.
- **Don't ignore preprocessing:** Edge detection without Gaussian blur produces noisy results. Always blur before Canny.
- **Don't use HoughLines() when you need endpoints:** Use HoughLinesP() for practical line segment detection. HoughLines() returns parametric form (ρ, θ) which requires extra calculation.
- **Don't assume north arrow is simple:** Arrows have shafts, tips, and sometimes decorative elements. Combine line detection (shaft) with contour analysis (tip).
- **Don't forget coordinate system:** OpenCV has origin at top-left, y increases downward. Angles from `arctan2(dy, dx)` need conversion to compass bearings.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Edge detection algorithm | Custom gradient-based edge finder | `cv2.Canny()` | Canny handles noise suppression, non-maximum suppression, hysteresis thresholding |
| Line detection | Scan pixels looking for straight segments | `cv2.HoughLinesP()` | Optimized C++ implementation, handles gaps, robust to noise |
| Angle calculation | Manual trigonometry on pixel coordinates | `np.arctan2()` then `np.degrees()` | Handles all quadrants correctly, avoids division by zero |
| Image rotation | Manual pixel remapping | `cv2.getRotationMatrix2D()` + `cv2.warpAffine()` | Handles interpolation, clipping, sub-pixel accuracy |
| Contour extraction | Connected component labeling from scratch | `cv2.findContours()` | Optimized, handles holes and hierarchy |
| PDF rendering | Parse PDF structure manually | PyMuPDF's `get_pixmap()` | Handles fonts, vectors, images, color spaces |

**Key insight:** Computer vision is full of edge cases (pun intended). Noise, lighting variation, rotation, scale changes, partial occlusion - these are solved problems in OpenCV. Don't rebuild them.

## Common Pitfalls

### Pitfall 1: Coordinate System Confusion
**What goes wrong:** Y-axis is inverted - origin (0,0) is top-left, y increases downward
**Why it happens:** Standard math has origin at bottom-left, y increases upward
**How to avoid:**
- Remember: `image[y, x]` not `image[x, y]` when indexing NumPy arrays
- Angles from `arctan2(dy, dx)` need adjustment: compass_north = (90 - opencv_angle) % 360
- When rotating, positive angles rotate clockwise (opposite of math convention)
**Warning signs:** Arrows pointing wrong direction, walls at 180° from expected

### Pitfall 2: minAreaRect Angle Range [-90, 0)
**What goes wrong:** `cv2.minAreaRect()` returns angles in [-90, 0) range, not [0, 360)
**Why it happens:** OpenCV represents rectangles with shortest edge first, limiting angle range
**How to avoid:**
- Always convert to your application's angle convention immediately
- If angle < 0, add 180 to get the other orientation
- Document which edge the angle refers to (width edge or height edge)
**Warning signs:** All detected angles are negative, angles jump by 90° unexpectedly

### Pitfall 3: Rotation Center Off-by-0.5 Pixel
**What goes wrong:** Image appears shifted after rotation
**Why it happens:** Pixel coordinates vs affine transform coordinates differ by 0.5
**How to avoid:**
- Use `center=(cols/2.0 - 0.5, rows/2.0 - 0.5)` for `getRotationMatrix2D()`
- Not `center=(cols/2.0, rows/2.0)` which is a common online example error
**Warning signs:** Rotated images have slight translation, cropping at edges

### Pitfall 4: Angle Units (Degrees vs Radians)
**What goes wrong:** Functions expect radians but get degrees (or vice versa)
**Why it happens:** OpenCV mixes conventions - some functions use degrees, others radians
**How to avoid:**
- `cv2.getRotationMatrix2D()` takes degrees
- `np.arctan2()` returns radians - always convert with `np.degrees()`
- HoughLines theta is in radians (π/180 for 1-degree precision)
- Document units in function signatures and variable names (`angle_deg`, `angle_rad`)
**Warning signs:** Tiny rotations instead of expected large ones, or vice versa

### Pitfall 5: Canny Threshold Tuning
**What goes wrong:** Edge detection misses lines or detects too much noise
**Why it happens:** Fixed thresholds don't work across varying image quality
**How to avoid:**
- Start with 2:1 or 3:1 ratio (threshold2 = 2-3 × threshold1)
- Adaptive approach: `threshold1 = 0.33 * median_pixel_value`
- Test on representative samples (site plans vary in line weight, contrast)
- Consider automatic threshold selection (e.g., Otsu's method for binary images)
**Warning signs:** Missing critical lines, detecting paper texture as edges

### Pitfall 6: PyMuPDF Pixmap Buffer Lifetime
**What goes wrong:** NumPy array becomes invalid after closing PDF document
**Why it happens:** `np.frombuffer(pix.samples)` creates a view, not a copy
**How to avoid:**
- Always call `.copy()` on the NumPy array before closing the document
- Or keep document open until CV processing is complete
**Warning signs:** Segmentation fault, corrupted image data, random pixel values

## Code Examples

Verified patterns from official sources:

### North Arrow Detection Pipeline
```python
# Source: Combined patterns from OpenCV docs and architectural CV research
import cv2
import numpy as np
import pymupdf

def detect_north_arrow_angle(pdf_path: str, page_num: int,
                             arrow_region: tuple = None) -> dict:
    """Detect north arrow and measure its angle.

    Strategy:
    1. Render PDF page to high-res image
    2. Optionally crop to arrow region (bottom-right of site plans)
    3. Detect lines (arrow shaft) and contours (arrow tip)
    4. Combine to determine precise angle

    Args:
        pdf_path: Path to PDF
        page_num: Page number (1-indexed)
        arrow_region: Optional (x, y, w, h) crop box in relative coords [0,1]

    Returns:
        {
            "angle": float,  # Compass bearing 0-360 (0=north)
            "confidence": str,  # "high", "medium", "low"
            "method": str,  # "line_detection" or "contour_analysis"
        }
    """
    # 1. Render page
    doc = pymupdf.open(pdf_path)
    page = doc[page_num - 1]
    mat = pymupdf.Matrix(2.0, 2.0)  # 2x zoom for better line detection
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    ).copy()
    doc.close()

    # 2. Crop to arrow region if specified
    if arrow_region:
        x, y, w, h = arrow_region
        h_img, w_img = img.shape[:2]
        x1, y1 = int(x * w_img), int(y * h_img)
        x2, y2 = int((x + w) * w_img), int((y + h) * h_img)
        img = img[y1:y2, x1:x2]

    # 3. Preprocess
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # 4. Detect lines (arrow shaft)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=30, maxLineGap=5)

    if lines is None or len(lines) == 0:
        return {"angle": None, "confidence": "low", "method": "failed"}

    # 5. Find longest line (likely arrow shaft)
    longest_line = max(lines, key=lambda l: np.hypot(
        l[0][2] - l[0][0], l[0][3] - l[0][1]
    ))
    x1, y1, x2, y2 = longest_line[0]

    # 6. Calculate angle (from bottom to top of arrow)
    # Reverse if needed to point from tail to tip
    dx, dy = x2 - x1, y2 - y1
    angle_rad = np.arctan2(-dy, dx)  # -dy because y increases downward
    angle_deg = np.degrees(angle_rad)

    # 7. Convert to compass bearing (0=north, 90=east)
    compass_angle = (90 - angle_deg) % 360

    # 8. Confidence based on line length and straightness
    length = np.hypot(dx, dy)
    confidence = "high" if length > 50 else "medium"

    return {
        "angle": round(compass_angle, 1),
        "confidence": confidence,
        "method": "line_detection"
    }
```

### Wall Edge Angle Measurement
```python
# Source: OpenCV line detection tutorial + architectural floor plan analysis
import cv2
import numpy as np

def measure_wall_edge_angles(pdf_path: str, page_num: int,
                             building_region: tuple = None) -> list:
    """Detect building footprint wall edges and measure their angles.

    Returns list of wall candidates with precise angles for LLM matching.

    Args:
        pdf_path: Path to PDF
        page_num: Site plan page number
        building_region: Optional (x, y, w, h) crop to building footprint

    Returns:
        List of {
            "angle": float,  # Angle from horizontal [0, 180)
            "length": float,  # Line length in pixels
            "position": str,  # "top", "right", "bottom", "left"
            "perpendicular_angle": float  # Outward-facing direction [0, 360)
        }
    """
    # 1-3. Render, crop, preprocess (same as north arrow)
    doc = pymupdf.open(pdf_path)
    page = doc[page_num - 1]
    mat = pymupdf.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    ).copy()
    doc.close()

    if building_region:
        x, y, w, h = building_region
        h_img, w_img = img.shape[:2]
        x1, y1 = int(x * w_img), int(y * h_img)
        x2, y2 = int((x + w) * w_img), int((y + h) * h_img)
        img = img[y1:y2, x1:x2]

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # 4. Detect lines (longer threshold for building walls)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100,
                           minLineLength=100, maxLineGap=20)

    if lines is None:
        return []

    # 5. Process each line
    walls = []
    h, w = img.shape[:2]

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Calculate angle from horizontal
        dx, dy = x2 - x1, y2 - y1
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad)

        # Normalize to [0, 180) - wall edges have no inherent direction
        if angle_deg < 0:
            angle_deg += 180

        # Calculate perpendicular (outward facing) angle
        perp_angle = (angle_deg + 90) % 360

        # Determine position (which edge of footprint)
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        if center_y < h * 0.3:
            position = "top"
        elif center_y > h * 0.7:
            position = "bottom"
        elif center_x < w * 0.3:
            position = "left"
        elif center_x > w * 0.7:
            position = "right"
        else:
            position = "center"

        length = np.hypot(dx, dy)

        walls.append({
            "angle": round(angle_deg, 1),
            "length": round(length, 1),
            "position": position,
            "perpendicular_angle": round(perp_angle, 1),
        })

    # 6. Sort by length (longest walls first)
    walls.sort(key=lambda w: w["length"], reverse=True)

    # 7. Return top candidates (typically 4 walls for rectangular buildings)
    return walls[:6]  # Return top 6 to account for non-rectangular shapes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure LLM vision | Hybrid CV + LLM | 2024-2025 | VLMs like GPT-4V use preprocessed visual features, not raw pixels |
| Template matching for symbols | Deep learning (YOLO, Faster R-CNN) | 2023-2024 | Higher accuracy on varied architectural styles |
| Single-scale processing | Multi-scale (tiling, pyramid) | 2024-2025 | Handles 4K images without huge token costs |
| Fixed Canny thresholds | Adaptive thresholds | Long-standing best practice | Robust across image quality variations |
| OpenCV 3.x | OpenCV 4.x | 2018+ | Improved DNN module, better Python bindings |

**Deprecated/outdated:**
- `cv` module (old C API): Replaced by `cv2` module, old API support ended
- Fixed image resolution: Modern approaches use dynamic resolution or tiling
- `cv2.findContours()` return signature changed in OpenCV 4.x: Now returns (contours, hierarchy), was (image, contours, hierarchy) in 3.x

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal Zoom Factor for PDF Rendering**
   - What we know: Higher zoom (2.0-3.0) improves line detection but increases memory
   - What's unclear: Best trade-off for Title 24 plans specifically (varies by PDF quality)
   - Recommendation: Start with 2.0x, make configurable, test on all 5 evals

2. **Arrow Detection Robustness**
   - What we know: North arrows vary widely (simple arrows, compass roses, decorative)
   - What's unclear: Can single algorithm handle all variants, or need fallback methods?
   - Recommendation: Implement line-based detection first, add contour-based as fallback. Keep LLM visual estimation as final fallback.

3. **CV Sensor Integration Point**
   - What we know: CV hints should augment LLM prompts, not replace them
   - What's unclear: Optimal prompt structure - provide all angles upfront, or only on disagreement?
   - Recommendation: Test both: (A) Always provide CV hints, (B) Run CV only when passes disagree. Measure impact on agreement rate and accuracy.

4. **Region of Interest (ROI) Specification**
   - What we know: North arrows typically in bottom-right of site plans; focusing ROI improves detection
   - What's unclear: Can LLM identify ROI reliably, or should CV scan full page?
   - Recommendation: Phase 1 - scan full page. Phase 2 - use LLM to specify ROI based on document_map. Measure speed vs accuracy trade-off.

5. **scikit-image vs OpenCV for Simple Cases**
   - What we know: scikit-image is easier to install, more Pythonic, but slower
   - What's unclear: Performance difference acceptable for non-real-time batch processing?
   - Recommendation: Benchmark on one eval. If <5% total runtime, consider scikit-image to reduce dependency weight. Otherwise use OpenCV.

## Sources

### Primary (HIGH confidence)
- [OpenCV Official Docs - Hough Line Transform](https://docs.opencv.org/4.x/d6/d10/tutorial_py_houghlines.html) - Line detection API and best practices
- [OpenCV Official Docs - Contour Features](https://docs.opencv.org/3.4/dd/d49/tutorial_py_contour_features.html) - minAreaRect orientation extraction
- [OpenCV Official Docs - Canny Edge Detection](https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html) - Preprocessing pipeline
- [PyMuPDF GitHub Discussion #1208](https://github.com/pymupdf/PyMuPDF/discussions/1208) - Pixmap to NumPy conversion
- [opencv-python PyPI](https://pypi.org/project/opencv-python/) - Package installation details

### Secondary (MEDIUM confidence)
- [Medium: Mastering Edge Detection with OpenCV](https://medium.com/@noel.benji/a-guide-to-robust-edge-detection-with-opencv-1d703506e014) - Preprocessing best practices verified with official docs
- [Medium: OpenCV vs Skimage](https://medium.com/analytics-vidhya/opencv-vs-skimage-for-image-analysis-which-one-is-better-e2bec8d1954f) - Performance comparison for library selection
- [Automaticaddison: Object Orientation with OpenCV](https://automaticaddison.com/how-to-determine-the-orientation-of-an-object-using-opencv/) - minAreaRect practical examples
- [PyImageSearch: OpenCV Getting and Setting Pixels](https://pyimagesearch.com/2021/01/20/opencv-getting-and-setting-pixels/) - Coordinate system explanation
- [Medium: Scanned PDFs Enhancement with PyMuPDF & OpenCV](https://medium.com/@bocharova.maiia/scanned-pdfs-quality-enhancement-using-pymupdf-opencv-d2a291a0d822) - Integration pattern

### Tertiary (LOW confidence - context only)
- [MDPI: Structural Analysis of Hand-Drawn Sketches](https://www.mdpi.com/1424-8220/24/9/2923) - Research context, not implementation
- [GitHub: FloorplanToBlender3d](https://github.com/grebtsew/FloorplanToBlender3d) - Architectural CV example, different use case
- [ResearchGate: Architectural Computer Vision](https://www.researchgate.net/publication/30871800_Architectural_Computer_Vision_Automated_Recognition_of_Architectural_Drawings) - Academic background, dated

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - OpenCV + PyMuPDF verified from official docs and project dependencies
- Architecture: MEDIUM - Patterns verified in docs, but integration with existing orchestrator needs testing
- Pitfalls: HIGH - Documented in official OpenCV docs and common Q&A forums
- Code examples: MEDIUM - Synthesized from official docs, not tested on Title 24 PDFs

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - stable CV domain, OpenCV 4.x mature)

**Key uncertainties requiring validation:**
1. Arrow detection robustness across all 5 evals
2. Optimal zoom factor and preprocessing thresholds for Title 24 PDFs
3. CV sensor integration approach (always-on vs on-disagreement)
4. Performance impact (acceptable batch processing overhead?)
