# Phase 2: Document Processing - Research

**Researched:** 2026-02-03
**Domain:** PDF rasterization and preprocessing for Claude multimodal input
**Confidence:** HIGH

## Summary

Phase 2 establishes a PDF preprocessing pipeline that converts Title 24 building plans into Claude-readable image sequences. The primary challenge is that the eval PDFs are large (11-18 pages, 3-22 MB) with high-resolution pages (2592x1728 to 3240x2160 pts) that would consume 65k-168k tokens per document at native resolution - potentially exceeding Claude's 200k context window when combined with system prompts and extraction instructions.

Research reveals two viable approaches: (1) rasterize PDFs to PNG images at a resolution that fits within context budget (~1568px longest edge, ~1600 tokens/page), or (2) use Claude's native PDF support which automatically handles text extraction plus page-as-image conversion. The native PDF approach is simpler but has limitations (100 page max, 32MB max per request). For Title 24 plans with 11-18 pages and 3-22MB file sizes, native PDF support should work but will be tight on the largest files.

The recommended approach is a hybrid strategy: build a Python CLI tool using PyMuPDF that can rasterize PDFs to PNG sequences at configurable resolution, enabling fine-grained control over token budgets. This tool can preprocess all eval PDFs in batch, outputting numbered page images to a `preprocessed/` directory alongside the original PDFs. The extraction agents can then consume these images directly via Claude's vision capabilities.

**Primary recommendation:** Use PyMuPDF (not pdf2image) for PDF-to-image conversion because it's faster, has no external dependencies, and integrates cleanly with Python. Create a CLI tool (`rasterize`) that converts PDFs to PNG sequences at 1568px longest edge resolution (Claude's recommended max), with configurable DPI for text-heavy vs diagram-heavy pages.

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF | 1.26.7+ | PDF rendering and rasterization | Fastest Python PDF library, no external dependencies, actively maintained by Artifex, supports high-quality rendering with configurable resolution |
| Click | 8.1+ | CLI framework | Already in project dependencies (used by verifier), consistent CLI patterns |
| Pillow | 10.0+ | Image processing and format conversion | Industry standard for image manipulation, integrates with PyMuPDF for format flexibility |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path handling | All file operations |
| concurrent.futures | stdlib | Parallel processing | Batch processing multiple PDFs |
| tqdm | 4.66+ | Progress bars | Visual feedback during batch preprocessing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF | pdf2image + Poppler | pdf2image requires external Poppler binaries, slower for PNG output, but more widely documented. PyMuPDF is self-contained and faster. |
| PyMuPDF | Claude native PDF support | Native PDF support is simpler (no preprocessing needed) but has 100-page/32MB limits and provides less control over token budget. For R&D flexibility, preprocessing is preferred. |
| Custom CLI | pdftoppm shell wrapper | Shell wrappers are fragile and harder to test. Python CLI provides consistent cross-platform behavior and better error handling. |

**Installation:**
```bash
# Add to pyproject.toml
pip install pymupdf pillow tqdm

# Or with uv
uv pip install pymupdf pillow tqdm
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── verifier/           # Existing evaluation infrastructure
├── schemas/            # Existing schemas
└── preprocessor/       # NEW: PDF preprocessing
    ├── __init__.py
    ├── cli.py          # CLI entry points (rasterize, preprocess-all)
    ├── rasterize.py    # PDF to image conversion logic
    └── config.py       # Preprocessing configuration

evals/
├── manifest.yaml
└── {eval-id}/
    ├── plans.pdf           # Original PDF
    ├── spec_sheet.pdf      # Spec sheet PDF
    ├── ground_truth.csv    # Ground truth
    ├── preprocessed/       # NEW: Rasterized page images
    │   ├── plans/
    │   │   ├── page-001.png
    │   │   ├── page-002.png
    │   │   └── ...
    │   └── spec_sheet/
    │       └── page-001.png
    └── results/            # Extraction results
```

### Pattern 1: Resolution-Based Rasterization

**What:** Convert PDF pages to PNG images at a resolution that maximizes quality while staying within Claude's token budget.

**When to use:** Always - the default preprocessing approach.

**Token Budget Analysis:**
```
Claude context window: 200,000 tokens
Reserved for system/instructions: 50,000 tokens
Available for images: 150,000 tokens

At 1568px longest edge (~1.6 MP): ~2,186 tokens/page
  - Fits ~68 pages in budget
  - Sufficient for all eval PDFs (max 18 pages)

At 1200px longest edge (~0.96 MP): ~1,280 tokens/page
  - Fits ~117 pages in budget
  - More headroom for complex extractions
```

**Example:**
```python
# src/preprocessor/rasterize.py
import pymupdf
from pathlib import Path
from typing import Iterator

def rasterize_pdf(
    pdf_path: Path,
    output_dir: Path,
    max_longest_edge: int = 1568,
    output_format: str = "png"
) -> Iterator[Path]:
    """
    Rasterize PDF pages to images at specified max resolution.

    Args:
        pdf_path: Path to input PDF
        output_dir: Directory for output images
        max_longest_edge: Maximum pixels on longest edge (default: Claude's recommended max)
        output_format: Image format (png, jpeg, webp)

    Yields:
        Path to each generated image file
    """
    doc = pymupdf.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    for page_num, page in enumerate(doc, 1):
        # Calculate zoom factor to achieve target resolution
        page_rect = page.rect
        current_longest = max(page_rect.width, page_rect.height)
        zoom = max_longest_edge / current_longest

        # Ensure we don't upscale (only downscale)
        zoom = min(zoom, 1.0)

        # Create transformation matrix
        mat = pymupdf.Matrix(zoom, zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Save to file
        output_path = output_dir / f"page-{page_num:03d}.{output_format}"
        pix.save(output_path)

        yield output_path

    doc.close()
```

### Pattern 2: Batch Preprocessing with Manifest

**What:** Process all eval PDFs in a single command, updating manifest with preprocessing status.

**When to use:** Before extraction runs, to ensure all PDFs are preprocessed.

**Example:**
```python
# src/preprocessor/cli.py
import click
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from .rasterize import rasterize_pdf

@click.group()
def cli():
    """Takeoff v2 Preprocessor - PDF rasterization for extraction."""
    pass

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), default=None,
              help='Output directory (default: preprocessed/ next to PDF)')
@click.option('--max-edge', '-m', type=int, default=1568,
              help='Max pixels on longest edge (default: 1568)')
@click.option('--format', '-f', 'output_format', type=click.Choice(['png', 'jpeg', 'webp']),
              default='png', help='Output image format')
def rasterize_one(pdf_path: Path, output_dir: Path, max_edge: int, output_format: str):
    """
    Rasterize a single PDF to images.

    Example:
        preprocessor rasterize-one evals/lamb-adu/plans.pdf
    """
    if output_dir is None:
        output_dir = pdf_path.parent / "preprocessed" / pdf_path.stem

    pages = list(rasterize_pdf(pdf_path, output_dir, max_edge, output_format))
    click.echo(f"Rasterized {len(pages)} pages to {output_dir}")

@cli.command()
@click.option('--evals-dir', type=click.Path(exists=True, path_type=Path),
              default=Path('evals'), help='Evals directory')
@click.option('--max-edge', '-m', type=int, default=1568,
              help='Max pixels on longest edge')
@click.option('--parallel', '-p', type=int, default=4,
              help='Number of parallel workers')
def preprocess_all(evals_dir: Path, max_edge: int, parallel: int):
    """
    Preprocess all eval PDFs.

    Example:
        preprocessor preprocess-all
    """
    # Find all PDFs in evals
    pdf_files = list(evals_dir.glob("*/plans.pdf")) + list(evals_dir.glob("*/spec_sheet.pdf"))

    click.echo(f"Found {len(pdf_files)} PDFs to process")

    with ProcessPoolExecutor(max_workers=parallel) as executor:
        futures = []
        for pdf_path in pdf_files:
            output_dir = pdf_path.parent / "preprocessed" / pdf_path.stem
            futures.append(executor.submit(
                rasterize_pdf_to_list, pdf_path, output_dir, max_edge
            ))

        for future in tqdm(futures, desc="Processing PDFs"):
            pages = future.result()
            # Could update manifest here

    click.echo("Preprocessing complete!")

if __name__ == '__main__':
    cli()
```

### Pattern 3: Selective Page Processing

**What:** Process only specific pages or page ranges when full document is unnecessary.

**When to use:** When only certain pages (e.g., CBECC schedules, specific sheets) are needed for extraction.

**Example:**
```python
def rasterize_pages(
    pdf_path: Path,
    output_dir: Path,
    pages: list[int] | None = None,  # None = all pages
    max_longest_edge: int = 1568
) -> list[Path]:
    """Rasterize specific pages from a PDF."""
    doc = pymupdf.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_indices = pages if pages else range(len(doc))
    outputs = []

    for page_num in page_indices:
        if page_num < 0 or page_num >= len(doc):
            continue

        page = doc[page_num]
        # ... same rendering logic as Pattern 1

    return outputs
```

### Anti-Patterns to Avoid

- **Upscaling low-resolution PDFs:** Never upscale - if original PDF is lower resolution than target, use original resolution
- **Processing PDFs at full resolution:** Will blow token budget. Always cap at 1568px longest edge.
- **Using JPEG for diagrams/schedules:** Use PNG for text/diagrams (lossless), JPEG only for photo-heavy pages
- **Preprocessing on-demand:** Preprocess once, use many times. Don't rasterize during extraction.
- **Ignoring aspect ratio:** Maintain original aspect ratio when resizing

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF page rendering | ImageMagick shell commands | PyMuPDF.page.get_pixmap() | PyMuPDF handles fonts, vectors, transparency correctly; shell commands are fragile |
| Image resizing | Manual pixel manipulation | PyMuPDF Matrix transform | Matrix handles aspect ratio, anti-aliasing, quality automatically |
| Batch processing | Sequential for loop | concurrent.futures.ProcessPoolExecutor | PDFs are independent, parallel processing is 3-4x faster |
| Progress reporting | print statements | tqdm | Consistent UX, time estimates, handles edge cases |
| Path handling | String manipulation | pathlib.Path | Cross-platform, cleaner API, avoids path separator bugs |

**Key insight:** PDF rendering is deceptively complex (fonts, vectors, color spaces, transparency). PyMuPDF handles all edge cases. Don't try to shell out to command-line tools.

## Common Pitfalls

### Pitfall 1: Token Budget Overflow

**What goes wrong:** Images are rasterized at too high resolution, causing extraction to exceed context window and fail.

**Why it happens:** Default PDF resolution (72-150 DPI) can produce very large images. A 3240x2160 pt page at 150 DPI is 6750x4500 pixels = ~40,500 tokens.

**How to avoid:**
- Always cap longest edge at 1568px (Claude's recommended maximum)
- Calculate token budget before processing: `tokens_per_page = (width * height) / 750`
- Leave headroom (50k+ tokens) for system prompts and extraction output

**Warning signs:**
- Extraction fails with context length errors
- Claude's response is truncated
- Very slow time-to-first-token (indicates oversized images being resized)

### Pitfall 2: Text Legibility Loss

**What goes wrong:** Aggressive downscaling makes text in schedules and tables unreadable.

**Why it happens:** Title 24 plans contain dense tables with small text (8-10pt). Downscaling to 1000px wide makes this illegible.

**How to avoid:**
- Test readability on text-heavy pages (CBECC schedules, spec sheets)
- Consider separate resolution settings for plans vs. spec sheets
- Minimum recommended: 1200px longest edge for text-heavy documents

**Warning signs:**
- Extraction misses values from tables
- OCR-style errors (5 vs S, 0 vs O, l vs 1)
- Consistent failures on numeric values

### Pitfall 3: Color Space Issues

**What goes wrong:** Images have wrong colors or transparency causes white-on-transparent rendering.

**Why it happens:** PDFs can use various color spaces (RGB, CMYK, spot colors) and alpha channels.

**How to avoid:**
- Use `alpha=False` in get_pixmap() to force solid white background
- Convert to RGB if needed: `pix = pymupdf.Pixmap(pymupdf.csRGB, pix)`

**Warning signs:**
- Images appear washed out or wrong colors
- White text disappears (rendered on transparent background)
- Inconsistent colors between pages

### Pitfall 4: Memory Exhaustion on Large PDFs

**What goes wrong:** Processing large PDFs (20+ MB) causes out-of-memory errors.

**Why it happens:** PyMuPDF loads entire page into memory for rendering. High-DPI rendering of large pages can consume gigabytes.

**How to avoid:**
- Process pages sequentially (not all at once)
- Use `doc.close()` to free memory after processing
- Monitor memory usage during batch processing
- For very large pages, consider tiled rendering

**Warning signs:**
- Python process killed (OOM)
- System becomes unresponsive during preprocessing
- Swap usage spikes

### Pitfall 5: Inconsistent Page Numbering

**What goes wrong:** Page numbering in output doesn't match PDF page numbers, causing extraction to reference wrong pages.

**Why it happens:** PDF internal page indices are 0-based, but displayed page numbers often start at 1 or use custom numbering.

**How to avoid:**
- Always use 1-based numbering in output filenames: `page-001.png`
- Document numbering convention clearly
- Match extraction page references to preprocessing output

**Warning signs:**
- Extraction references pages that don't exist
- Consistent off-by-one errors in page lookups
- Confusion in error reports about which page failed

## Code Examples

Verified patterns from official sources:

### Basic PDF to PNG Conversion

```python
# Source: PyMuPDF documentation
import pymupdf

def pdf_to_images_basic(pdf_path: str, output_dir: str, dpi: int = 150):
    """Basic PDF to PNG conversion at specified DPI."""
    doc = pymupdf.open(pdf_path)

    # Calculate zoom factor for target DPI (72 is PDF default)
    zoom = dpi / 72
    mat = pymupdf.Matrix(zoom, zoom)

    for page_num, page in enumerate(doc, 1):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(f"{output_dir}/page-{page_num:03d}.png")

    doc.close()
```
*Source: [PyMuPDF Tutorial](https://pymupdf.readthedocs.io/en/latest/tutorial.html)*

### Resolution-Limited Conversion

```python
# Source: PyMuPDF GitHub Discussions #1307
import pymupdf
from pathlib import Path

def pdf_to_images_max_resolution(
    pdf_path: Path,
    output_dir: Path,
    max_longest_edge: int = 1568
) -> list[tuple[Path, int, int]]:
    """
    Convert PDF pages to images with maximum resolution limit.
    Returns list of (path, width, height) tuples.
    """
    doc = pymupdf.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for page_num, page in enumerate(doc, 1):
        rect = page.rect
        longest = max(rect.width, rect.height)

        # Calculate zoom to hit target (but never upscale)
        zoom = min(max_longest_edge / longest, 1.0)
        mat = pymupdf.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=mat, alpha=False)
        output_path = output_dir / f"page-{page_num:03d}.png"
        pix.save(output_path)

        results.append((output_path, pix.width, pix.height))

    doc.close()
    return results
```
*Source: [PyMuPDF GitHub Discussion](https://github.com/pymupdf/PyMuPDF/discussions/1307)*

### Token Cost Calculation

```python
def estimate_tokens(width: int, height: int) -> int:
    """
    Estimate Claude token usage for an image.
    Formula from Anthropic docs: tokens = (width * height) / 750
    """
    return (width * height) // 750

def calculate_pdf_token_cost(
    pdf_path: Path,
    max_longest_edge: int = 1568
) -> dict:
    """Calculate total estimated token cost for a PDF at given resolution."""
    doc = pymupdf.open(pdf_path)
    total_tokens = 0
    page_costs = []

    for page in doc:
        rect = page.rect
        longest = max(rect.width, rect.height)
        zoom = min(max_longest_edge / longest, 1.0)

        # Calculate resulting dimensions
        width = int(rect.width * zoom)
        height = int(rect.height * zoom)
        tokens = estimate_tokens(width, height)

        total_tokens += tokens
        page_costs.append({
            'width': width,
            'height': height,
            'tokens': tokens
        })

    doc.close()

    return {
        'total_pages': len(page_costs),
        'total_tokens': total_tokens,
        'pages': page_costs,
        'fits_200k': total_tokens < 150000,  # Leave 50k headroom
    }
```
*Source: [Anthropic Vision Documentation](https://platform.claude.com/docs/en/build-with-claude/vision)*

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Text extraction only (pdftotext, PyPDF2) | Multimodal page-as-image | Claude 3 vision (2024) | Enables understanding of diagrams, tables, layouts - not just extracted text |
| External tools (Poppler, ImageMagick) | PyMuPDF self-contained | PyMuPDF 1.20+ (2023) | No system dependencies, easier deployment, faster performance |
| Fixed DPI rasterization | Resolution-limited rasterization | LLM context limits (2024-2025) | Token budget management for large documents |
| PDF native support only | Hybrid PDF + preprocessed images | Claude Code (2025-2026) | Better control over token usage, caching of preprocessed images |

**Deprecated/outdated:**
- **pdf2image + Poppler:** Still works but requires external binary installation. PyMuPDF is preferred for new projects.
- **Text-only extraction:** Loses critical visual information from building plans (diagrams, schedules, annotations).
- **Full-resolution images:** Wastes context window tokens. Always resize to Claude's recommended maximum.

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal resolution for text-heavy vs diagram-heavy pages**
   - What we know: 1568px is Claude's max before auto-resize, higher resolution preserves text better
   - What's unclear: Whether spec sheets (text-heavy) need different resolution than plans (diagram-heavy)
   - Recommendation: Start with uniform 1568px, add configurable per-document-type settings if extraction accuracy suffers on specific types

2. **Native PDF support vs preprocessed images for extraction**
   - What we know: Claude Code can read PDFs natively (32MB, 100 page limits); preprocessing gives more control
   - What's unclear: Which approach produces better extraction accuracy for Title 24 plans
   - Recommendation: Build preprocessing infrastructure (more flexible), but test native PDF support as fallback for simpler cases

3. **Caching strategy for preprocessed images**
   - What we know: PDFs don't change, preprocessed images should be generated once
   - What's unclear: Whether to check for existing preprocessed images or always regenerate
   - Recommendation: Check for existing preprocessed/ directory, add `--force` flag to regenerate

4. **Page selection for extraction**
   - What we know: Not all pages are equally useful (cover pages, general notes vs CBECC schedules)
   - What's unclear: Whether to preprocess all pages or implement intelligent page filtering
   - Recommendation: Preprocess all pages initially, let discovery agent (Phase 3) identify relevant pages

## Sources

### Primary (HIGH confidence)

- [Anthropic Vision Documentation](https://platform.claude.com/docs/en/build-with-claude/vision) - Image token calculation, size recommendations, best practices
- [Anthropic PDF Support Documentation](https://platform.claude.com/docs/en/docs/build-with-claude/pdf-support) - Native PDF handling, limits, processing modes
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/) - Official docs for PDF rendering, get_pixmap(), Matrix transforms
- [PyMuPDF Tutorial](https://pymupdf.readthedocs.io/en/latest/tutorial.html) - Basic PDF to image patterns
- [PyMuPDF Images Recipes](https://pymupdf.readthedocs.io/en/latest/recipes-images.html) - Advanced image conversion patterns
- [PyMuPDF GitHub Discussion #1307](https://github.com/pymupdf/PyMuPDF/discussions/1307) - Resolution and DPI settings

### Secondary (MEDIUM confidence)

- [Converting PDFs to Images with PyMuPDF - Artifex Blog](https://artifex.com/blog/converting-pdfs-to-images-with-pymupdf-a-complete-guide) - Best practices for image conversion
- [pdf2image PyPI](https://pypi.org/project/pdf2image/) - Alternative library comparison
- [pdftoppm man page](https://linux.die.net/man/1/pdftoppm) - CLI tool for PDF rasterization (reference for resolution settings)
- [Claude Code PDF Reading Thread](https://www.threads.com/@boris_cherny/post/DM8tPKeTKGE/) - Claude Code native PDF support announcement

### Tertiary (LOW confidence)

- [llm-pdf-to-images GitHub](https://github.com/simonw/llm-pdf-to-images) - Community plugin for PDF to image conversion
- [PyMuPDF4LLM Medium Article](https://medium.com/@danushidk507/using-pymupdf4llm-a-practical-guide-for-pdf-extraction-in-llm-rag-environments-63649915abbf) - LLM-focused PDF processing patterns

## Token Budget Analysis for Eval PDFs

Based on actual eval PDF analysis:

| Eval | Pages | Original Size | At 1568px | Total Tokens | Fits 200k? |
|------|-------|---------------|-----------|--------------|------------|
| canterbury-rd | 18 | 3240x2160 pts | ~1568x1045 | ~39,348 | Yes |
| chamberlin-circle | 11 | 2592x1728 pts | ~1568x1045 | ~24,046 | Yes |
| lamb-adu | 11 | 2592x1728 pts | ~1568x1045 | ~24,046 | Yes |
| martinez-adu | 13 | 1224x792 pts | ~1224x792 | ~16,822 | Yes |
| poonian-adu | 16 | 2592x1728 pts | ~1568x1045 | ~34,976 | Yes |

**Conclusion:** All eval PDFs comfortably fit within Claude's 200k context window at recommended resolution (1568px longest edge), leaving ample headroom for system prompts and extraction output.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyMuPDF is well-documented, actively maintained, and verified from official sources
- Architecture: HIGH - Patterns derived from official PyMuPDF documentation and Anthropic vision docs
- Pitfalls: MEDIUM - Based on general PDF processing experience and Claude-specific documentation, validation needed during implementation

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (60 days - stable technologies, PyMuPDF has regular releases)
