"""PDF to image rasterization for Claude multimodal input."""

from pathlib import Path

import pymupdf


def estimate_tokens(width: int, height: int) -> int:
    """
    Estimate Claude token usage for an image.

    Formula from Anthropic docs: tokens = (width * height) / 750

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Estimated token count
    """
    return (width * height) // 750


def rasterize_pdf(
    pdf_path: Path,
    output_dir: Path,
    max_longest_edge: int = 1568,
    output_format: str = "png",
) -> list[tuple[Path, int, int]]:
    """
    Rasterize PDF pages to images with maximum resolution limit.

    Converts each page of a PDF to an image file, scaling down to fit
    within the specified maximum resolution. Never upscales - if the
    original page is smaller than max_longest_edge, it is rendered
    at its original resolution.

    Args:
        pdf_path: Path to input PDF file
        output_dir: Directory for output images
        max_longest_edge: Maximum pixels on longest edge (default: 1568,
            Claude's recommended max before auto-resize)
        output_format: Image format - "png", "jpeg", or "webp"

    Returns:
        List of (path, width, height) tuples for each generated image.
        Useful for token estimation: estimate_tokens(width, height)
    """
    doc = pymupdf.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[Path, int, int]] = []

    try:
        for page_num, page in enumerate(doc, 1):
            # Get page dimensions (in points, 72 pts = 1 inch)
            rect = page.rect
            longest = max(rect.width, rect.height)

            # Calculate zoom factor - never upscale
            zoom = min(max_longest_edge / longest, 1.0)
            mat = pymupdf.Matrix(zoom, zoom)

            # Render page to pixmap (alpha=False forces white background)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Save to file with zero-padded page number
            output_path = output_dir / f"page-{page_num:03d}.{output_format}"
            pix.save(output_path)

            results.append((output_path, pix.width, pix.height))

    finally:
        # Always close document to free memory
        doc.close()

    return results
