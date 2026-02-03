"""CLI entry point for Takeoff v2 Verifier."""
import csv
import json
from pathlib import Path
from typing import Optional
import click
import yaml

from .compare import compare_fields, flatten_dict, load_field_mapping
from .metrics import compute_field_level_metrics, compute_aggregate_metrics


def load_ground_truth_csv(csv_path: Path, mapping: dict) -> dict:
    """
    Load ground truth from CSV and convert to nested dict structure.

    The CSV has CBECC-Res/EnergyPro format:
    - Section headers in column A
    - Field names in column B (after comma)
    - Values in column C
    - Units in column D (optional)

    Lines have variable column counts, so we use Python's csv module
    with flexible handling.
    """
    result = {}
    csv_to_json = mapping.get('csv_to_json', {})

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip rows with fewer than 3 columns
            if len(row) < 3:
                continue

            # Field name is in column 1 (index 1), value in column 2 (index 2)
            field_name = row[1].strip() if row[1] else None
            value = row[2].strip() if row[2] else None

            if field_name and field_name in csv_to_json and value:
                json_path = csv_to_json[field_name]

                # Parse value to appropriate type
                value_str = value.strip().strip('"')

                # Try to convert to number
                try:
                    if '.' in value_str:
                        parsed_value = float(value_str)
                    else:
                        parsed_value = int(value_str)
                except (ValueError, TypeError):
                    parsed_value = value_str

                # Set in result dict using path
                keys = json_path.split('.')
                d = result
                for key in keys[:-1]:
                    d = d.setdefault(key, {})
                d[keys[-1]] = parsed_value

    return result


def load_extracted_json(json_path: Path) -> dict:
    """Load extracted JSON from file."""
    with open(json_path) as f:
        return json.load(f)


@click.group()
def cli():
    """Takeoff v2 Verifier - Evaluate extraction quality against ground truth."""
    pass


@cli.command()
@click.argument('eval_id')
@click.argument('extracted_json', type=click.Path(exists=True))
@click.option('--evals-dir', type=click.Path(exists=True), default='evals',
              help='Directory containing eval datasets')
@click.option('--output', '-o', type=click.Path(), default=None,
              help='Output file for results JSON')
def verify_one(eval_id: str, extracted_json: str, evals_dir: str, output: Optional[str]):
    """
    Run verification on a single extraction result.

    EVAL_ID: Identifier of the eval (e.g., lamb-adu)
    EXTRACTED_JSON: Path to extracted JSON file

    Example:
        verifier verify-one lamb-adu results/extracted.json
        python -m verifier verify-one lamb-adu results/extracted.json
    """
    evals_path = Path(evals_dir)
    mapping = load_field_mapping()

    # Load ground truth
    gt_path = evals_path / eval_id / "ground_truth.csv"
    if not gt_path.exists():
        click.echo(f"Error: Ground truth not found at {gt_path}", err=True)
        raise SystemExit(1)

    ground_truth = load_ground_truth_csv(gt_path, mapping)

    # Load extracted JSON
    extracted = load_extracted_json(Path(extracted_json))

    # Compare
    discrepancies = compare_fields(ground_truth, extracted, mapping)

    # Flatten for counting
    gt_flat = flatten_dict(ground_truth)
    ext_flat = flatten_dict(extracted)

    # Compute metrics
    metrics = compute_field_level_metrics(
        discrepancies,
        len(gt_flat),
        len(ext_flat)
    )

    # Output results
    click.echo(f"\n{'='*60}")
    click.echo(f"Verification Results: {eval_id}")
    click.echo(f"{'='*60}")
    click.echo(f"\nMetrics:")
    click.echo(f"  Precision: {metrics['precision']:.3f}")
    click.echo(f"  Recall:    {metrics['recall']:.3f}")
    click.echo(f"  F1 Score:  {metrics['f1']:.3f}")
    click.echo(f"\n  Correct:   {metrics['correct_fields']}/{metrics['total_fields_gt']} fields")

    click.echo(f"\nError Breakdown:")
    for error_type, count in metrics['errors_by_type'].items():
        click.echo(f"  {error_type}: {count}")

    if discrepancies:
        click.echo(f"\nField-Level Discrepancies ({len(discrepancies)} total):")
        for d in discrepancies[:20]:  # Show first 20
            click.echo(f"  [{d.error_type}] {d.field_path}")
            click.echo(f"    Expected: {d.expected}")
            click.echo(f"    Actual:   {d.actual}")
        if len(discrepancies) > 20:
            click.echo(f"  ... and {len(discrepancies) - 20} more")

    # Save results if output specified
    if output:
        results = {
            'eval_id': eval_id,
            'metrics': metrics,
            'discrepancies': [
                {
                    'field_path': d.field_path,
                    'expected': d.expected,
                    'actual': d.actual,
                    'error_type': d.error_type
                }
                for d in discrepancies
            ]
        }
        Path(output).write_text(json.dumps(results, indent=2, default=str))
        click.echo(f"\nResults saved to: {output}")


@cli.command()
@click.option('--evals-dir', type=click.Path(exists=True), default='evals',
              help='Directory containing eval datasets')
@click.option('--results-subdir', default='results',
              help='Subdirectory within each eval containing extraction results')
@click.option('--output', '-o', type=click.Path(), default=None,
              help='Output file for aggregate results JSON')
def verify_all(evals_dir: str, results_subdir: str, output: Optional[str]):
    """
    Run verification on all evals and show aggregate metrics.

    Looks for extracted.json in each eval's results directory.

    Example:
        verifier verify-all
        verifier verify-all --evals-dir ./evals --output aggregate.json
        python -m verifier verify-all
    """
    evals_path = Path(evals_dir)
    mapping = load_field_mapping()

    # Load manifest
    manifest_path = evals_path / "manifest.yaml"
    if not manifest_path.exists():
        click.echo(f"Error: Manifest not found at {manifest_path}", err=True)
        raise SystemExit(1)

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    all_metrics = []
    results_by_eval = {}
    skipped_evals = []

    for eval_id in manifest.get('evals', {}).keys():
        # Find latest extraction result
        results_dir = evals_path / eval_id / results_subdir
        extracted_path = None

        if results_dir.exists():
            # Look for extracted.json directly in results dir
            if (results_dir / "extracted.json").exists():
                extracted_path = results_dir / "extracted.json"
            else:
                # Check for iteration directories
                iter_dirs = sorted([d for d in results_dir.iterdir()
                                   if d.is_dir() and d.name.startswith('iteration-')])
                if iter_dirs:
                    latest_iter = iter_dirs[-1]
                    if (latest_iter / "extracted.json").exists():
                        extracted_path = latest_iter / "extracted.json"

        if not extracted_path:
            skipped_evals.append(eval_id)
            continue

        # Load ground truth
        gt_path = evals_path / eval_id / "ground_truth.csv"
        if not gt_path.exists():
            skipped_evals.append(eval_id)
            continue

        # Load and compare
        ground_truth = load_ground_truth_csv(gt_path, mapping)
        extracted = load_extracted_json(extracted_path)

        discrepancies = compare_fields(ground_truth, extracted, mapping)
        gt_flat = flatten_dict(ground_truth)
        ext_flat = flatten_dict(extracted)

        metrics = compute_field_level_metrics(
            discrepancies,
            len(gt_flat),
            len(ext_flat)
        )
        metrics['eval_id'] = eval_id

        all_metrics.append(metrics)
        results_by_eval[eval_id] = {
            'metrics': metrics,
            'discrepancy_count': len(discrepancies)
        }

    # Output skipped evals
    if skipped_evals:
        click.echo(f"\nSkipped (no extraction results): {', '.join(skipped_evals)}")

    if not all_metrics:
        click.echo("\nNo evaluations found with extraction results.")
        click.echo("Run extraction first, then verify.")
        click.echo(f"\nExpected structure: {evals_dir}/<eval_id>/{results_subdir}/extracted.json")
        raise SystemExit(1)

    # Compute aggregate
    aggregate = compute_aggregate_metrics(all_metrics)

    # Output results
    click.echo(f"\n{'='*60}")
    click.echo("Aggregate Verification Results")
    click.echo(f"{'='*60}")
    click.echo(f"\nEvaluated: {len(all_metrics)}/{len(manifest.get('evals', {}))} evals")
    click.echo(f"\nAggregate Metrics (Macro-Average):")
    click.echo(f"  Precision: {aggregate['precision']:.3f}")
    click.echo(f"  Recall:    {aggregate['recall']:.3f}")
    click.echo(f"  F1 Score:  {aggregate['f1']:.3f}")

    click.echo(f"\nPer-Eval Breakdown:")
    click.echo(f"  {'Eval':<25} {'P':>8} {'R':>8} {'F1':>8} {'Errors':>8}")
    click.echo(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for m in all_metrics:
        errors_total = sum(m['errors_by_type'].values())
        click.echo(f"  {m['eval_id']:<25} {m['precision']:>8.3f} {m['recall']:>8.3f} {m['f1']:>8.3f} {errors_total:>8}")

    # Save results if output specified
    if output:
        output_data = {
            'aggregate': {
                'precision': aggregate['precision'],
                'recall': aggregate['recall'],
                'f1': aggregate['f1'],
                'micro_precision': aggregate.get('micro_precision', 0),
                'micro_recall': aggregate.get('micro_recall', 0),
                'micro_f1': aggregate.get('micro_f1', 0),
                'total_evals': aggregate['total_evals'],
            },
            'by_eval': results_by_eval,
            'skipped': skipped_evals
        }
        Path(output).write_text(json.dumps(output_data, indent=2, default=str))
        click.echo(f"\nResults saved to: {output}")


if __name__ == '__main__':
    cli()
