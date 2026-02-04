"""CLI entry point for Takeoff v2 Verifier."""
import csv
import json
import webbrowser
from pathlib import Path
from typing import Optional
import click
import yaml

from .compare import compare_fields, compare_all_fields, flatten_dict, load_field_mapping
from .metrics import compute_field_level_metrics, compute_aggregate_metrics
from .report import EvalReport, generate_html_report
from .persistence import EvalStore, save_evaluation, get_next_iteration


def parse_value(value_str: str):
    """Parse a string value to appropriate Python type."""
    value_str = value_str.strip().strip('"')

    # Handle empty values
    if not value_str or value_str == ' ':
        return None

    # Handle boolean values
    if value_str.lower() in ('yes', 'true'):
        return True
    if value_str.lower() in ('no', 'false'):
        return False

    # Try to convert to number
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except (ValueError, TypeError):
        return value_str


def set_nested_value_with_arrays(result: dict, json_path: str, value):
    """Set value in nested dict, handling array notation like zones[0].name."""
    import re

    # Split path and handle array indices
    parts = []
    for part in json_path.split('.'):
        # Check for array notation like zones[0]
        match = re.match(r'(\w+)\[(\d+)\]', part)
        if match:
            parts.append(('array', match.group(1), int(match.group(2))))
        else:
            parts.append(('key', part, None))

    d = result
    for i, (ptype, key, idx) in enumerate(parts[:-1]):
        if ptype == 'array':
            if key not in d:
                d[key] = []
            # Extend list if needed
            while len(d[key]) <= idx:
                d[key].append({})
            d = d[key][idx]
        else:
            d = d.setdefault(key, {})

    # Set final value
    final_type, final_key, final_idx = parts[-1]
    if final_type == 'array':
        if final_key not in d:
            d[final_key] = []
        while len(d[final_key]) <= final_idx:
            d[final_key].append({})
        d[final_key][final_idx] = value
    else:
        d[final_key] = value


def load_ground_truth_csv(csv_path: Path, mapping: dict) -> dict:
    """
    Load ground truth from CSV and convert to nested dict structure.

    The CSV has CBECC-Res/EnergyPro format:
    - Section headers in column A
    - Field names in column B (after comma)
    - Values in column C
    - Units in column D (optional)
    - Array sections have header rows with column names, then data rows

    Lines have variable column counts, so we use Python's csv module
    with flexible handling.
    """
    result = {}
    csv_to_json = mapping.get('csv_to_json', {})
    array_mappings = mapping.get('array_mappings', {})

    # Build reverse lookup: section name -> (json_key, field_mapping)
    section_to_config = {}
    for json_key, config in array_mappings.items():
        section_name = config.get('csv_section', '')
        if section_name:
            section_to_config[section_name] = (json_key, config.get('fields', {}))

    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    current_section = None
    current_headers = []
    current_json_key = None
    current_field_mapping = {}

    for row in rows:
        # Skip empty rows
        if not row or all(not cell.strip() for cell in row):
            current_section = None
            current_headers = []
            continue

        # Check for array section header (format: ,Section Name:, col1, col2, ...)
        if len(row) >= 3 and row[1].strip().endswith(':'):
            section_name = row[1].strip()
            if section_name in section_to_config:
                current_section = section_name
                current_json_key, current_field_mapping = section_to_config[section_name]
                # Headers are in columns 2+ (after the empty col 0 and section name col 1)
                current_headers = [h.strip() for h in row[2:]]
                # Initialize the array in result
                if current_json_key not in result:
                    result[current_json_key] = []
                continue

        # Check for array data row (format: ,,value1, value2, ...)
        if current_section and len(row) >= 3 and not row[0].strip() and not row[1].strip() and row[2].strip():
            # This is a data row for the current array section
            values = row[2:]
            item = {}
            for i, header in enumerate(current_headers):
                if i < len(values) and values[i].strip():
                    # Map CSV header to JSON field name
                    json_field = current_field_mapping.get(header, header.lower().replace(' ', '_').replace('(', '').replace(')', ''))
                    parsed = parse_value(values[i])
                    if parsed is not None:
                        item[json_field] = parsed
            if item:
                result[current_json_key].append(item)
            continue

        # Regular key-value field (format: anything, field_name, value, ...)
        if len(row) >= 3:
            field_name = row[1].strip() if row[1] else None
            value = row[2].strip() if row[2] else None

            if field_name and field_name in csv_to_json and value:
                json_path = csv_to_json[field_name]
                parsed_value = parse_value(value)

                # Skip None values
                if parsed_value is None:
                    continue

                # Set in result dict using path (handles arrays)
                set_nested_value_with_arrays(result, json_path, parsed_value)

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
@click.option('--save', is_flag=True, default=False,
              help='Save results to iteration directory with HTML report')
@click.option('--open-report', is_flag=True, default=False,
              help='Open HTML report in browser after generation')
def verify_one(eval_id: str, extracted_json: str, evals_dir: str, output: Optional[str],
               save: bool, open_report: bool):
    """
    Run verification on a single extraction result.

    EVAL_ID: Identifier of the eval (e.g., lamb-adu)
    EXTRACTED_JSON: Path to extracted JSON file

    Example:
        verifier verify-one lamb-adu results/extracted.json
        verifier verify-one lamb-adu results/extracted.json --save --open-report
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
    all_field_comparisons = compare_all_fields(ground_truth, extracted, mapping)

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

    # Save results if output specified (simple JSON output)
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

    # Save to iteration directory with HTML report if --save flag
    if save:
        store = EvalStore(evals_path)
        iteration = store.get_next_iteration(eval_id)

        # Get history for report
        history = store.get_history(eval_id)

        # Prepare discrepancies as dicts for report
        discrepancy_dicts = [
            {
                'field_path': d.field_path,
                'expected': d.expected,
                'actual': d.actual,
                'error_type': d.error_type
            }
            for d in discrepancies
        ]

        # Prepare all field comparisons for full diff view
        all_fields_dicts = [
            {
                'field_path': f.field_path,
                'expected': f.expected,
                'actual': f.actual,
                'matches': f.matches,
                'error_type': f.error_type
            }
            for f in all_field_comparisons
        ]

        # Prepare raw JSON data for display
        extracted_json = json.dumps(extracted, indent=2, default=str)
        ground_truth_json = json.dumps(ground_truth, indent=2, default=str)

        # Generate HTML report
        report = EvalReport(
            eval_id=eval_id,
            metrics=metrics,
            discrepancies=discrepancy_dicts,
            iteration=iteration,
            history=history,
            all_fields=all_fields_dicts,
            extracted_data=extracted_json,
            ground_truth_data=ground_truth_json,
        )
        html_content = report.render_html()

        # Build eval results
        eval_results = {
            'eval_id': eval_id,
            'metrics': metrics,
            'discrepancies': discrepancy_dicts,
        }

        # Save everything
        iter_dir = store.save_iteration(
            eval_id=eval_id,
            iteration=iteration,
            extracted_data=extracted,
            eval_results=eval_results,
            html_report=html_content,
        )

        click.echo(f"\nResults saved to iteration {iteration}:")
        click.echo(f"  {iter_dir}/extracted.json")
        click.echo(f"  {iter_dir}/eval-results.json")
        click.echo(f"  {iter_dir}/eval-report.html")

        report_path = iter_dir / "eval-report.html"

        # Open report in browser if requested
        if open_report:
            webbrowser.open(f"file://{report_path.absolute()}")
            click.echo(f"\nOpened report in browser")


@cli.command()
@click.option('--evals-dir', type=click.Path(exists=True), default='evals',
              help='Directory containing eval datasets')
@click.option('--results-subdir', default='results',
              help='Subdirectory within each eval containing extraction results')
@click.option('--output', '-o', type=click.Path(), default=None,
              help='Output file for aggregate results JSON')
@click.option('--save', is_flag=True, default=False,
              help='Save results to iteration directories with HTML reports')
def verify_all(evals_dir: str, results_subdir: str, output: Optional[str], save: bool):
    """
    Run verification on all evals and show aggregate metrics.

    Looks for extracted.json in each eval's results directory.

    Example:
        verifier verify-all
        verifier verify-all --evals-dir ./evals --output aggregate.json
        verifier verify-all --save
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
        all_field_comparisons = compare_all_fields(ground_truth, extracted, mapping)
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
            'discrepancy_count': len(discrepancies),
            'discrepancies': [
                {
                    'field_path': d.field_path,
                    'expected': d.expected,
                    'actual': d.actual,
                    'error_type': d.error_type
                }
                for d in discrepancies
            ],
            'all_fields': [
                {
                    'field_path': f.field_path,
                    'expected': f.expected,
                    'actual': f.actual,
                    'matches': f.matches,
                    'error_type': f.error_type
                }
                for f in all_field_comparisons
            ],
            'extracted_data': extracted,
            'ground_truth_data': ground_truth,
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

    # Save to iteration directories with HTML reports if --save flag
    if save:
        click.echo(f"\nSaving results to iteration directories...")
        for eval_id, eval_data in results_by_eval.items():
            store = EvalStore(evals_path)
            iteration = store.get_next_iteration(eval_id)

            # Get history for report
            history = store.get_history(eval_id)

            # Prepare raw JSON data for display
            extracted_json = json.dumps(eval_data['extracted_data'], indent=2, default=str)
            ground_truth_json = json.dumps(eval_data.get('ground_truth_data', {}), indent=2, default=str)

            # Generate HTML report
            report = EvalReport(
                eval_id=eval_id,
                metrics=eval_data['metrics'],
                discrepancies=eval_data['discrepancies'],
                iteration=iteration,
                history=history,
                all_fields=eval_data.get('all_fields'),
                extracted_data=extracted_json,
                ground_truth_data=ground_truth_json,
            )
            html_content = report.render_html()

            # Build eval results
            eval_results = {
                'eval_id': eval_id,
                'metrics': eval_data['metrics'],
                'discrepancies': eval_data['discrepancies'],
            }

            # Save everything
            iter_dir = store.save_iteration(
                eval_id=eval_id,
                iteration=iteration,
                extracted_data=eval_data['extracted_data'],
                eval_results=eval_results,
                html_report=html_content,
            )
            click.echo(f"  {eval_id}: iteration-{iteration:03d}")

    # Save aggregate results if output specified
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
            'by_eval': {
                eval_id: {
                    'metrics': data['metrics'],
                    'discrepancy_count': data['discrepancy_count'],
                }
                for eval_id, data in results_by_eval.items()
            },
            'skipped': skipped_evals
        }
        Path(output).write_text(json.dumps(output_data, indent=2, default=str))
        click.echo(f"\nAggregate results saved to: {output}")


@cli.command()
@click.argument('eval_id')
@click.option('--evals-dir', type=click.Path(exists=True), default='evals',
              help='Directory containing eval datasets')
@click.option('--results-subdir', default='results',
              help='Subdirectory within each eval containing results')
def history(eval_id: str, evals_dir: str, results_subdir: str):
    """
    Show F1 score progression across iterations for an eval.

    EVAL_ID: Identifier of the eval (e.g., lamb-adu)

    Example:
        verifier history lamb-adu
        python -m verifier history lamb-adu
    """
    evals_path = Path(evals_dir)
    store = EvalStore(evals_path, results_subdir)

    history_data = store.get_history(eval_id)

    if not history_data:
        click.echo(f"\nNo iteration history found for {eval_id}")
        click.echo(f"Run 'verifier verify-one {eval_id} <json> --save' to create iterations")
        return

    aggregate = store.load_aggregate(eval_id)

    click.echo(f"\n{'='*60}")
    click.echo(f"F1 Score History: {eval_id}")
    click.echo(f"{'='*60}")

    if aggregate:
        click.echo(f"\nBest F1: {aggregate['best_f1']:.3f} (iteration {aggregate['best_iteration']})")
        click.echo(f"Total iterations: {len(history_data)}")

    click.echo(f"\n  {'Iter':<6} {'F1':>8} {'P':>8} {'R':>8} {'Trend':>10} {'Timestamp':<20}")
    click.echo(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*20}")

    for h in history_data:
        trend = h.get('trend', 0)
        trend_str = f"+{trend:.3f}" if trend > 0 else f"{trend:.3f}" if trend < 0 else "--"
        timestamp = h.get('timestamp', '')[:19] if h.get('timestamp') else ''

        click.echo(
            f"  {h['iteration']:<6} "
            f"{h['f1']:>8.3f} "
            f"{h['precision']:>8.3f} "
            f"{h['recall']:>8.3f} "
            f"{trend_str:>10} "
            f"{timestamp:<20}"
        )

    # Show trend visualization
    if len(history_data) >= 2:
        click.echo(f"\nTrend: ", nl=False)
        for h in history_data:
            f1 = h['f1']
            if f1 >= 0.9:
                click.echo(click.style("*", fg='green'), nl=False)
            elif f1 >= 0.7:
                click.echo(click.style("*", fg='blue'), nl=False)
            elif f1 >= 0.5:
                click.echo(click.style("*", fg='yellow'), nl=False)
            else:
                click.echo(click.style("*", fg='red'), nl=False)
        click.echo()  # newline


if __name__ == '__main__':
    cli()
