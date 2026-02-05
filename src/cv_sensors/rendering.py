"""PDF page rendering to NumPy arrays for CV processing.

Uses PyMuPDF to render PDF pages as high-resolution raster images,
returning NumPy arrays suitable for OpenCV operations.
"""

import pymupdf
import numpy as np
from pathlib import Path


def render_page_to_numpy(pdf_path: str, page_num: int, zoom: float = 2.0) -> np.ndarray:
    """Render a PDF page to a NumPy RGB array.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (1-indexed, matching human convention)
        zoom: Zoom factor for rendering resolution (default: 2.0 = ~150 DPI)

    Returns:
        NumPy array of shape (height, width, 3) with dtype uint8 (RGB)

    Raises:
        FileNotFoundError: If PDF doesn't exist
        IndexError: If page number is out of range

    Note:
        CRITICAL: The pixmap buffer is read-only and invalidated when the
        document is closed. We MUST call .copy() before closing the document.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Open PDF
    doc = pymupdf.open(str(pdf_path))

    try:
        # Convert 1-indexed to 0-indexed
        page_idx = page_num - 1

        if page_idx < 0 or page_idx >= len(doc):
            raise IndexError(
                f"Page {page_num} out of range (PDF has {len(doc)} pages)"
            )

        # Get page and render at specified zoom
        page = doc[page_idx]
        matrix = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # Convert to NumPy array (RGB, 3 channels)
        # CRITICAL: Must copy before closing document
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, 3).copy()

        return img

    finally:
        doc.close()
