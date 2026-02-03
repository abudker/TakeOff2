---
phase: 02-document-processing
plan: 01
subsystem: preprocessing
tags: [pymupdf, pdf, rasterization, cli, multimodal, vision]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Project structure, CLI patterns (verifier), pyproject.toml setup
provides:
  - PDF to PNG rasterization with resolution capping
  - preprocessor CLI with rasterize-one and preprocess-all commands
  - Token estimation for Claude context budget management
affects: [03-extraction, agents]

# Tech tracking
tech-stack:
  added: [pymupdf>=1.26, pillow>=10.0, tqdm>=4.66]
  patterns: [resolution-capped rasterization, batch preprocessing with skip/force]

key-files:
  created:
    - src/preprocessor/__init__.py
    - src/preprocessor/rasterize.py
    - src/preprocessor/cli.py
  modified:
    - pyproject.toml

key-decisions:
  - "PyMuPDF over pdf2image: no external dependencies, faster, self-contained"
  - "1568px max longest edge: Claude's recommended max before auto-resize"
  - "PNG format: lossless for text/diagrams in building plans"
  - "1-indexed zero-padded filenames: page-001.png for consistent ordering"

patterns-established:
  - "Resolution-capped rasterization: zoom = min(target/actual, 1.0) - never upscale"
  - "Preprocessing output structure: evals/{id}/preprocessed/{pdf-stem}/page-NNN.png"
  - "Token estimation: (width * height) // 750 per Anthropic docs"

# Metrics
duration: 3min
completed: 2026-02-03
---

# Phase 2 Plan 01: PDF Preprocessing Summary

**PyMuPDF-based PDF rasterization CLI producing 1568px-capped PNG sequences for Claude multimodal extraction**

## Performance

- **Duration:** 3 min 11 sec
- **Started:** 2026-02-03T21:03:52Z
- **Completed:** 2026-02-03T21:07:03Z
- **Tasks:** 2/2
- **Files created:** 3
- **Files modified:** 1

## Accomplishments

- Working `preprocessor rasterize-one` command converts single PDFs to PNG sequences
- Working `preprocessor preprocess-all` command batch processes all eval PDFs
- All 10 eval PDFs (5 plans + 5 spec sheets) preprocessed: 75 pages, ~143k tokens total
- Resolution verified: all images capped at 1568px longest edge
- Token budget validated: all PDFs fit comfortably within Claude's 200k context window

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement PDF rasterization core** - `8326aee` (feat)
2. **Task 2: Implement CLI and register entry point** - `646aefd` (feat)

## Files Created/Modified

- `src/preprocessor/__init__.py` - Module init with public exports
- `src/preprocessor/rasterize.py` - Core rasterize_pdf and estimate_tokens functions
- `src/preprocessor/cli.py` - Click CLI with rasterize-one and preprocess-all commands
- `pyproject.toml` - Added dependencies (pymupdf, pillow, tqdm) and preprocessor CLI entry point

## Decisions Made

- **PyMuPDF over pdf2image:** Self-contained (no Poppler dependency), faster, actively maintained by Artifex
- **1568px max resolution:** Claude's documented maximum before automatic resize, optimizes token usage
- **PNG output format:** Lossless compression essential for text legibility in building plan schedules
- **alpha=False in pixmap:** Forces white background, prevents transparency issues
- **Sequential processing with tqdm:** Simpler than parallel processing, adequate for 10 PDFs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all verification steps passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 5 eval cases have preprocessed images ready for extraction agents
- Token budget verified: 143k tokens for all 75 pages leaves ample headroom for prompts
- Preprocessing infrastructure can be extended with selective page processing if needed
- Ready for Phase 3 (Extraction System) to consume preprocessed images

---
*Phase: 02-document-processing*
*Completed: 2026-02-03*
