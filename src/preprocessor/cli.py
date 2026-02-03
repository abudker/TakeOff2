"""CLI entry points for PDF preprocessing."""

from pathlib import Path

import click
from tqdm import tqdm

from .rasterize import estimate_tokens, rasterize_pdf


@click.group()
def cli():
    """Takeoff v2 Preprocessor - PDF rasterization for extraction."""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (default: preprocessed/<pdf-stem> next to PDF)",
)
@click.option(
    "--max-edge",
    "-m",
    type=int,
    default=1568,
    help="Max pixels on longest edge (default: 1568)",
)
def rasterize_one(pdf_path: Path, output_dir: Path | None, max_edge: int):
    """
    Rasterize a single PDF to images.

    Output files are named page-001.png, page-002.png, etc.

    Example:
        preprocessor rasterize-one evals/lamb-adu/plans.pdf
    """
    if output_dir is None:
        output_dir = pdf_path.parent / "preprocessed" / pdf_path.stem

    click.echo(f"Rasterizing {pdf_path} to {output_dir}")

    pages = rasterize_pdf(pdf_path, output_dir, max_longest_edge=max_edge)

    # Calculate token estimates
    total_tokens = sum(estimate_tokens(w, h) for _, w, h in pages)

    click.echo(f"Rasterized {len(pages)} pages")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"Estimated tokens: {total_tokens:,}")


@cli.command()
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("evals"),
    help="Evals directory (default: evals)",
)
@click.option(
    "--max-edge",
    "-m",
    type=int,
    default=1568,
    help="Max pixels on longest edge (default: 1568)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Regenerate even if preprocessed/ exists",
)
def preprocess_all(evals_dir: Path, max_edge: int, force: bool):
    """
    Preprocess all eval PDFs.

    Finds all plans.pdf and spec_sheet.pdf files in the evals directory
    and rasterizes them to PNG sequences.

    Example:
        preprocessor preprocess-all
        preprocessor preprocess-all --force
    """
    # Find all PDFs in evals
    pdf_files = list(evals_dir.glob("*/plans.pdf")) + list(
        evals_dir.glob("*/spec_sheet.pdf")
    )
    pdf_files.sort()

    click.echo(f"Found {len(pdf_files)} PDFs to process")

    total_pages = 0
    total_tokens = 0
    processed_count = 0
    skipped_count = 0

    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        output_dir = pdf_path.parent / "preprocessed" / pdf_path.stem

        # Skip if preprocessed directory exists (unless --force)
        if output_dir.exists() and not force:
            skipped_count += 1
            continue

        pages = rasterize_pdf(pdf_path, output_dir, max_longest_edge=max_edge)

        page_tokens = sum(estimate_tokens(w, h) for _, w, h in pages)
        total_pages += len(pages)
        total_tokens += page_tokens
        processed_count += 1

    click.echo("")
    click.echo("Preprocessing complete!")
    click.echo(f"  PDFs processed: {processed_count}")
    if skipped_count > 0:
        click.echo(f"  PDFs skipped (already exist): {skipped_count}")
    click.echo(f"  Total pages: {total_pages}")
    click.echo(f"  Total estimated tokens: {total_tokens:,}")


if __name__ == "__main__":
    cli()
