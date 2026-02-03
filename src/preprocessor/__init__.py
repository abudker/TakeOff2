"""Takeoff v2 Preprocessor - PDF rasterization for extraction."""

__version__ = "0.1.0"

from .rasterize import rasterize_pdf, estimate_tokens

__all__ = ["rasterize_pdf", "estimate_tokens", "__version__"]
