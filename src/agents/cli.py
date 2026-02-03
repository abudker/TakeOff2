"""CLI for extraction agent."""
import json
import logging
import sys
from pathlib import Path
import click
from agents.orchestrator import run_extraction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Extraction agent CLI for Title 24 building specifications."""
    pass


@cli.command()
@click.argument("eval_id")
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("evals"),
    help="Directory containing evaluation cases"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for extracted JSON (default: extracted.json in eval dir)"
)
def extract_one(eval_id: str, evals_dir: Path, output: Path):
    """
    Extract building specification from a single evaluation case.

    EVAL_ID is the evaluation case identifier (e.g., chamberlin-circle).
    """
    try:
        # Find eval directory
        eval_dir = evals_dir / eval_id
        if not eval_dir.exists():
            click.echo(f"Error: Evaluation case not found: {eval_dir}", err=True)
            sys.exit(1)

        # Set default output path
        if output is None:
            output = eval_dir / "extracted.json"

        # Run extraction
        click.echo(f"Extracting from {eval_id}...")
        final_state = run_extraction(eval_id, eval_dir)

        # Check for errors
        if final_state.get("error"):
            click.echo(f"Error: {final_state['error']}", err=True)
            sys.exit(1)

        # Get building spec
        building_spec = final_state.get("building_spec")
        if not building_spec:
            click.echo("Error: No building spec in final state", err=True)
            sys.exit(1)

        # Save to output file
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(building_spec, f, indent=2)

        click.echo(f"Success! Extracted building spec saved to: {output}")
        click.echo(f"  Project: {building_spec['project']['run_title']}")
        click.echo(f"  Address: {building_spec['project']['address']}, {building_spec['project']['city']}")
        click.echo(f"  Climate Zone: {building_spec['project']['climate_zone']}")
        click.echo(f"  CFA: {building_spec['envelope']['conditioned_floor_area']} sq ft")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Extraction failed: {e}", err=True)
        logger.exception("Extraction error details:")
        sys.exit(1)


@cli.command()
@click.option(
    "--evals-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("evals"),
    help="Directory containing evaluation cases"
)
@click.option(
    "--skip-existing",
    is_flag=True,
    help="Skip cases with existing extracted.json"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-extraction even if extracted.json exists"
)
def extract_all(evals_dir: Path, skip_existing: bool, force: bool):
    """
    Extract building specifications from all evaluation cases.

    Processes all eval cases listed in manifest.yaml.
    """
    import yaml

    try:
        # Load manifest
        manifest_path = evals_dir / "manifest.yaml"
        if not manifest_path.exists():
            click.echo(f"Error: manifest.yaml not found in {evals_dir}", err=True)
            sys.exit(1)

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        eval_cases = manifest.get("evals", [])
        if not eval_cases:
            click.echo("No evaluation cases found in manifest.yaml", err=True)
            sys.exit(1)

        click.echo(f"Found {len(eval_cases)} evaluation cases")

        # Track results
        results = []

        for eval_case in eval_cases:
            eval_id = eval_case["id"]
            eval_dir = evals_dir / eval_id
            output_path = eval_dir / "extracted.json"

            # Check if already extracted
            if output_path.exists() and not force:
                if skip_existing:
                    click.echo(f"Skipping {eval_id} (already extracted)")
                    results.append({"eval_id": eval_id, "status": "skipped", "output_path": output_path})
                    continue

            # Run extraction
            click.echo(f"\nExtracting {eval_id}...")
            try:
                final_state = run_extraction(eval_id, eval_dir)

                if final_state.get("error"):
                    click.echo(f"  Error: {final_state['error']}", err=True)
                    results.append({"eval_id": eval_id, "status": "error", "output_path": None})
                    continue

                building_spec = final_state.get("building_spec")
                if not building_spec:
                    click.echo("  Error: No building spec in final state", err=True)
                    results.append({"eval_id": eval_id, "status": "error", "output_path": None})
                    continue

                # Save output
                with open(output_path, "w") as f:
                    json.dump(building_spec, f, indent=2)

                click.echo(f"  Success: {output_path}")
                results.append({"eval_id": eval_id, "status": "success", "output_path": output_path})

            except Exception as e:
                click.echo(f"  Failed: {e}", err=True)
                results.append({"eval_id": eval_id, "status": "error", "output_path": None})

        # Print summary table
        click.echo("\n" + "=" * 80)
        click.echo("EXTRACTION SUMMARY")
        click.echo("=" * 80)
        click.echo(f"{'Eval ID':<30} {'Status':<15} {'Output Path'}")
        click.echo("-" * 80)

        for result in results:
            output_str = str(result["output_path"]) if result["output_path"] else "N/A"
            click.echo(f"{result['eval_id']:<30} {result['status']:<15} {output_str}")

        click.echo("-" * 80)
        success_count = sum(1 for r in results if r["status"] == "success")
        click.echo(f"Total: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("extract-all error details:")
        sys.exit(1)


if __name__ == "__main__":
    cli()
