"""CLI for extraction agent."""
import json
import logging
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Any
import click
import yaml
from agents.orchestrator import run_extraction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_claude_cli():
    """Check if Claude CLI is available."""
    if not shutil.which("claude"):
        click.echo("Error: Claude CLI not found.", err=True)
        click.echo("", err=True)
        click.echo("The extraction system requires Claude Code to invoke agent workers.", err=True)
        click.echo("Please install Claude Code: https://claude.ai/download", err=True)
        sys.exit(1)


def show_diagnostics(eval_id: str, extraction_status: Dict[str, Any], conflicts: List[Dict[str, Any]]):
    """Show verbose extraction diagnostics.

    Args:
        eval_id: Evaluation case identifier
        extraction_status: Dict mapping domain to status info
        conflicts: List of conflict records from extraction
    """
    click.echo(f"\n  --- Diagnostics for {eval_id} ---")

    # Per-domain status
    click.echo("  Extraction Status:")
    for domain, status in extraction_status.items():
        if isinstance(status, dict):
            s = status.get("status", "unknown")
            items = status.get("items_extracted", 0)
            retries = status.get("retry_count", 0)
            error = status.get("error", "")

            status_str = f"{domain}: {s} ({items} items)"
            if retries > 0:
                status_str += f" [retried {retries}x]"
            if error:
                status_str += f" [{error[:50]}...]"
            click.echo(f"    {status_str}")

    # Conflicts
    if conflicts:
        click.echo(f"\n  Conflicts ({len(conflicts)}):")
        for c in conflicts[:5]:  # Show first 5
            if isinstance(c, dict):
                field = c.get("field", "unknown")
                item = c.get("item_name", "")
                resolution = c.get("resolution", "")
                click.echo(f"    - {field} ({item}): {resolution}")
        if len(conflicts) > 5:
            click.echo(f"    ... and {len(conflicts) - 5} more")


def show_timing(timing: Dict[str, float], eval_id: str):
    """Print pipeline timing breakdown."""
    if not timing:
        return
    click.echo(f"\n  --- Timing for {eval_id} ---")
    total = timing.get("total", 0)
    for stage, duration in timing.items():
        if stage == "total":
            continue
        pct = (duration / total * 100) if total > 0 else 0
        click.echo(f"    {stage:<25} {duration:>7.1f}s  ({pct:>4.0f}%)")
    click.echo(f"    {'total':<25} {total:>7.1f}s")


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
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed extraction diagnostics"
)
def extract_one(eval_id: str, evals_dir: Path, output: Path, verbose: bool):
    """
    Extract building specification from a single evaluation case.

    EVAL_ID is the evaluation case identifier (e.g., chamberlin-circle).
    """
    # Check Claude CLI is available
    check_claude_cli()

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

        # Show timing
        timing = final_state.get("timing")
        if timing:
            show_timing(timing, eval_id)

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

        # Show extraction counts
        zones_count = len(building_spec.get("zones", []))
        walls_count = len(building_spec.get("walls", []))
        windows_count = len(building_spec.get("windows", []))
        hvac_count = len(building_spec.get("hvac_systems", []))
        dhw_count = len(building_spec.get("water_heating_systems", []))
        click.echo(f"  Components: {zones_count} zones, {walls_count} walls, {windows_count} windows, {hvac_count} HVAC, {dhw_count} DHW")

        if verbose:
            extraction_status = building_spec.get("extraction_status", {})
            conflicts = building_spec.get("conflicts", [])
            show_diagnostics(eval_id, extraction_status, conflicts)

        # Save timing alongside results
        if timing:
            timing_path = eval_dir / "timing.json"
            with open(timing_path, "w") as f:
                json.dump(timing, f, indent=2)

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
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed extraction diagnostics per eval"
)
def extract_all(evals_dir: Path, skip_existing: bool, force: bool, verbose: bool):
    """
    Extract building specifications from all evaluation cases.

    Processes all eval cases listed in manifest.yaml.
    """
    # Check Claude CLI is available
    check_claude_cli()

    try:
        # Load manifest
        manifest_path = evals_dir / "manifest.yaml"
        if not manifest_path.exists():
            click.echo(f"Error: manifest.yaml not found in {evals_dir}", err=True)
            sys.exit(1)

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Manifest uses 'evals' dict with eval_id as key
        evals_dict = manifest.get("evals", {})
        if not evals_dict:
            click.echo("No evaluation cases found in manifest.yaml", err=True)
            sys.exit(1)

        click.echo(f"Running extraction on {len(evals_dict)} evaluation cases...")
        click.echo("=" * 60)

        # Track results
        results = []
        all_timings = {}

        for eval_id, eval_info in evals_dict.items():
            eval_dir = evals_dir / eval_id
            output_path = eval_dir / "extracted.json"

            # Check if already extracted
            if output_path.exists() and not force:
                if skip_existing:
                    click.echo(f"[{eval_id}] Skipped (already extracted)")
                    results.append({
                        "id": eval_id,
                        "status": "skipped",
                        "output_path": output_path
                    })
                    continue

            # Run extraction
            click.echo(f"\n[{eval_id}] Starting extraction...")
            try:
                final_state = run_extraction(eval_id, eval_dir)

                # Collect timing
                timing = final_state.get("timing")
                if timing:
                    all_timings[eval_id] = timing

                if final_state.get("error"):
                    click.echo(f"[{eval_id}] FAILED: {final_state['error']}")
                    results.append({
                        "id": eval_id,
                        "status": "failed",
                        "error": final_state["error"]
                    })
                    continue

                building_spec = final_state.get("building_spec")
                if not building_spec:
                    click.echo(f"[{eval_id}] FAILED: No building spec in final state")
                    results.append({
                        "id": eval_id,
                        "status": "failed",
                        "error": "No building spec"
                    })
                    continue

                # Count extracted items
                zones_count = len(building_spec.get("zones", []))
                walls_count = len(building_spec.get("walls", []))
                windows_count = len(building_spec.get("windows", []))
                hvac_count = len(building_spec.get("hvac_systems", []))
                dhw_count = len(building_spec.get("water_heating_systems", []))
                extraction_status = building_spec.get("extraction_status", {})
                conflicts = building_spec.get("conflicts", [])

                total_s = f" ({timing['total']:.0f}s)" if timing else ""
                click.echo(f"[{eval_id}] SUCCESS{total_s} - Zones: {zones_count}, Walls: {walls_count}, Windows: {windows_count}, HVAC: {hvac_count}, DHW: {dhw_count}")

                if verbose:
                    show_diagnostics(eval_id, extraction_status, conflicts)
                    if timing:
                        show_timing(timing, eval_id)

                # Save output
                with open(output_path, "w") as f:
                    json.dump(building_spec, f, indent=2)
                click.echo(f"[{eval_id}] Saved to {output_path}")

                # Save timing
                if timing:
                    timing_path = eval_dir / "timing.json"
                    with open(timing_path, "w") as f:
                        json.dump(timing, f, indent=2)

                results.append({
                    "id": eval_id,
                    "status": "success",
                    "zones": zones_count,
                    "walls": walls_count,
                    "windows": windows_count,
                    "hvac": hvac_count,
                    "dhw": dhw_count,
                    "conflicts": len(conflicts),
                    "output_path": output_path
                })

            except Exception as e:
                click.echo(f"[{eval_id}] ERROR: {e}")
                results.append({
                    "id": eval_id,
                    "status": "error",
                    "error": str(e)
                })

        # Print summary
        click.echo("\n" + "=" * 60)
        click.echo("EXTRACTION SUMMARY")
        click.echo("=" * 60)

        success_count = sum(1 for r in results if r["status"] == "success")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")
        failed_count = len(results) - success_count - skipped_count

        click.echo(f"Total: {len(results)} | Success: {success_count} | Skipped: {skipped_count} | Failed: {failed_count}")

        # Print timing summary across all evals
        if all_timings:
            click.echo("\n" + "─" * 60)
            click.echo("TIMING SUMMARY")
            click.echo("─" * 60)
            click.echo(f"{'Eval':<22} {'Discovery':>10} {'Orient':>10} {'Project':>10} {'Domains':>10} {'Total':>10}")
            click.echo("─" * 60)
            for eid, t in all_timings.items():
                click.echo(
                    f"{eid:<22} "
                    f"{t.get('discovery', 0):>9.0f}s "
                    f"{t.get('orientation', 0):>9.0f}s "
                    f"{t.get('project', 0):>9.0f}s "
                    f"{t.get('parallel_extraction', 0):>9.0f}s "
                    f"{t.get('total', 0):>9.0f}s"
                )
            grand_total = sum(t.get("total", 0) for t in all_timings.values())
            click.echo("─" * 60)
            click.echo(f"{'Grand total':<22} {'':>10} {'':>10} {'':>10} {'':>10} {grand_total:>9.0f}s")

        if verbose:
            click.echo("\nPer-eval results:")
            for r in results:
                if r["status"] == "success":
                    click.echo(f"  {r['id']}: {r['zones']}z/{r['walls']}w/{r['windows']}win/{r['hvac']}hvac/{r['dhw']}dhw ({r['conflicts']} conflicts)")
                elif r["status"] == "skipped":
                    click.echo(f"  {r['id']}: skipped")
                else:
                    click.echo(f"  {r['id']}: {r['status']} - {r.get('error', 'Unknown')}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("extract-all error details:")
        sys.exit(1)


if __name__ == "__main__":
    cli()
