"""CLI for extraction agent."""
import json
import logging
import sys
import shutil
import time
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional
import click
import yaml
from agents.orchestrator import run_extraction, ALL_DOMAINS

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


def show_timing(timing: Dict[str, Any], eval_id: str):
    """Print pipeline timing breakdown including per-domain detail."""
    if not timing:
        return
    click.echo(f"\n  --- Timing for {eval_id} ---")
    total = timing.get("total", 0)
    for stage, duration in timing.items():
        if stage in ("total", "domains"):
            continue
        if isinstance(duration, (int, float)):
            pct = (duration / total * 100) if total > 0 else 0
            click.echo(f"    {stage:<25} {duration:>7.1f}s  ({pct:>4.0f}%)")
    # Per-domain breakdown
    domain_timing = timing.get("domains")
    if domain_timing:
        for domain, dur in domain_timing.items():
            click.echo(f"      {domain:<23} {dur:>7.1f}s")
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
@click.option(
    "--domains",
    type=str,
    default=None,
    help="Comma-separated domains to extract (zones,windows,hvac,dhw). Default: all"
)
def extract_one(eval_id: str, evals_dir: Path, output: Path, verbose: bool, domains: Optional[str]):
    """
    Extract building specification from a single evaluation case.

    EVAL_ID is the evaluation case identifier (e.g., chamberlin-circle).
    """
    # Check Claude CLI is available
    check_claude_cli()

    # Parse domains
    domain_list = None
    if domains:
        domain_list = [d.strip() for d in domains.split(",")]
        invalid = [d for d in domain_list if d not in ALL_DOMAINS]
        if invalid:
            click.echo(f"Error: Invalid domain(s): {', '.join(invalid)}. Valid: {', '.join(ALL_DOMAINS)}", err=True)
            sys.exit(1)
        click.echo(f"Domains: {', '.join(domain_list)}")

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
        final_state = run_extraction(eval_id, eval_dir, domains=domain_list)

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
@click.option(
    "--eval", "eval_ids",
    multiple=True,
    help="Only run specific eval(s). Can be repeated: --eval foo --eval bar"
)
@click.option(
    "--exclude", "exclude_ids",
    multiple=True,
    help="Exclude specific eval(s). Can be repeated: --exclude foo --exclude bar"
)
@click.option(
    "--domains",
    type=str,
    default=None,
    help="Comma-separated domains to extract (zones,windows,hvac,dhw). Default: all"
)
@click.option(
    "--workers",
    type=int,
    default=1,
    help="Number of evals to extract in parallel (default: 1 = sequential)"
)
def extract_all(evals_dir: Path, skip_existing: bool, force: bool, verbose: bool,
                eval_ids: tuple, exclude_ids: tuple, domains: Optional[str], workers: int):
    """
    Extract building specifications from evaluation cases.

    Processes eval cases from manifest.yaml. Use --eval/--exclude to filter,
    --domains to extract specific domains, --workers for parallelism.
    """
    # Check Claude CLI is available
    check_claude_cli()

    # Parse domains
    domain_list = None
    if domains:
        domain_list = [d.strip() for d in domains.split(",")]
        invalid = [d for d in domain_list if d not in ALL_DOMAINS]
        if invalid:
            click.echo(f"Error: Invalid domain(s): {', '.join(invalid)}. Valid: {', '.join(ALL_DOMAINS)}", err=True)
            sys.exit(1)

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

        # Filter evals
        if eval_ids:
            evals_dict = {k: v for k, v in evals_dict.items() if k in eval_ids}
        if exclude_ids:
            evals_dict = {k: v for k, v in evals_dict.items() if k not in exclude_ids}

        if not evals_dict:
            click.echo("No evaluation cases match the filter criteria.", err=True)
            sys.exit(1)

        # Show config
        config_parts = [f"{len(evals_dict)} evals"]
        if domain_list:
            config_parts.append(f"domains={','.join(domain_list)}")
        if workers > 1:
            config_parts.append(f"{workers} workers")
        click.echo(f"Running extraction: {' | '.join(config_parts)}")
        click.echo("=" * 60)

        wall_clock_start = time.monotonic()

        def _extract_eval(eval_id, eval_info):
            """Extract a single eval, return result dict."""
            eval_dir = evals_dir / eval_id
            output_path = eval_dir / "extracted.json"

            # Check if already extracted
            if output_path.exists() and not force:
                if skip_existing:
                    return {"id": eval_id, "status": "skipped", "output_path": str(output_path)}

            try:
                final_state = run_extraction(eval_id, eval_dir, domains=domain_list)
                timing = final_state.get("timing")

                if final_state.get("error"):
                    return {"id": eval_id, "status": "failed", "error": final_state["error"],
                            "timing": timing}

                building_spec = final_state.get("building_spec")
                if not building_spec:
                    return {"id": eval_id, "status": "failed", "error": "No building spec",
                            "timing": timing}

                # Save output
                with open(output_path, "w") as f:
                    json.dump(building_spec, f, indent=2)

                # Save timing
                if timing:
                    timing_path = eval_dir / "timing.json"
                    with open(timing_path, "w") as f:
                        json.dump(timing, f, indent=2)

                return {
                    "id": eval_id,
                    "status": "success",
                    "zones": len(building_spec.get("zones", [])),
                    "walls": len(building_spec.get("walls", [])),
                    "windows": len(building_spec.get("windows", [])),
                    "hvac": len(building_spec.get("hvac_systems", [])),
                    "dhw": len(building_spec.get("water_heating_systems", [])),
                    "conflicts": len(building_spec.get("conflicts", [])),
                    "output_path": str(output_path),
                    "timing": timing,
                    "extraction_status": building_spec.get("extraction_status", {}),
                }
            except Exception as e:
                return {"id": eval_id, "status": "error", "error": str(e)}

        # Execute extractions (parallel or sequential)
        results = []
        all_timings = {}

        if workers > 1:
            # Parallel extraction across evals
            click.echo(f"Running {len(evals_dict)} evals with {workers} parallel workers...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_extract_eval, eid, einfo): eid
                    for eid, einfo in evals_dict.items()
                }
                for future in concurrent.futures.as_completed(futures):
                    r = future.result()
                    eid = r["id"]
                    timing = r.get("timing")
                    if timing:
                        all_timings[eid] = timing

                    if r["status"] == "success":
                        total_s = f" ({timing['total']:.0f}s)" if timing else ""
                        click.echo(f"[{eid}] SUCCESS{total_s} - Z:{r['zones']} W:{r['walls']} Win:{r['windows']} HVAC:{r['hvac']} DHW:{r['dhw']}")
                    elif r["status"] == "skipped":
                        click.echo(f"[{eid}] Skipped (already extracted)")
                    else:
                        click.echo(f"[{eid}] {r['status'].upper()}: {r.get('error', '?')}")
                    results.append(r)
        else:
            # Sequential extraction
            for eval_id, eval_info in evals_dict.items():
                click.echo(f"\n[{eval_id}] Starting extraction...")
                r = _extract_eval(eval_id, eval_info)
                timing = r.get("timing")
                if timing:
                    all_timings[eval_id] = timing

                if r["status"] == "success":
                    total_s = f" ({timing['total']:.0f}s)" if timing else ""
                    click.echo(f"[{eval_id}] SUCCESS{total_s} - Z:{r['zones']} W:{r['walls']} Win:{r['windows']} HVAC:{r['hvac']} DHW:{r['dhw']}")

                    if verbose:
                        show_diagnostics(eval_id, r.get("extraction_status", {}), [])
                        if timing:
                            show_timing(timing, eval_id)

                    click.echo(f"[{eval_id}] Saved to {r['output_path']}")
                elif r["status"] == "skipped":
                    click.echo(f"[{eval_id}] Skipped (already extracted)")
                else:
                    click.echo(f"[{eval_id}] {r['status'].upper()}: {r.get('error', '?')}")

                results.append(r)

        wall_clock_total = time.monotonic() - wall_clock_start

        # Print summary
        click.echo("\n" + "=" * 60)
        click.echo("EXTRACTION SUMMARY")
        click.echo("=" * 60)

        success_count = sum(1 for r in results if r["status"] == "success")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")
        failed_count = len(results) - success_count - skipped_count

        click.echo(f"Total: {len(results)} | Success: {success_count} | Skipped: {skipped_count} | Failed: {failed_count}")
        click.echo(f"Wall-clock time: {wall_clock_total:.0f}s ({wall_clock_total/60:.1f} min)")

        # Print timing summary across all evals
        if all_timings:
            click.echo("\n" + "─" * 72)
            click.echo("TIMING SUMMARY")
            click.echo("─" * 72)
            click.echo(f"{'Eval':<22} {'Discovery':>10} {'Orient':>10} {'Project':>10} {'Domains':>10} {'Total':>10}")
            click.echo("─" * 72)
            for eid, t in all_timings.items():
                click.echo(
                    f"{eid:<22} "
                    f"{t.get('discovery', 0):>9.0f}s "
                    f"{t.get('orientation', 0):>9.0f}s "
                    f"{t.get('project', 0):>9.0f}s "
                    f"{t.get('parallel_extraction', 0):>9.0f}s "
                    f"{t.get('total', 0):>9.0f}s"
                )
                # Per-domain detail
                domain_timing = t.get("domains")
                if domain_timing:
                    parts = [f"{d}={dur:.0f}s" for d, dur in domain_timing.items()]
                    click.echo(f"{'':>22}   {' | '.join(parts)}")
            click.echo("─" * 72)
            sum_total = sum(t.get("total", 0) for t in all_timings.values())
            click.echo(f"{'Sum (sequential)':<22} {'':>10} {'':>10} {'':>10} {'':>10} {sum_total:>9.0f}s")
            click.echo(f"{'Wall-clock':<22} {'':>10} {'':>10} {'':>10} {'':>10} {wall_clock_total:>9.0f}s")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("extract-all error details:")
        sys.exit(1)


if __name__ == "__main__":
    cli()
