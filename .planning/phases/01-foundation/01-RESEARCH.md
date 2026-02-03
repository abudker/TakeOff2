# Phase 1: Foundation - Research

**Researched:** 2026-02-03
**Domain:** Claude Code agent architecture + LLM evaluation infrastructure
**Confidence:** HIGH

## Summary

Phase 1 establishes two foundational systems: (1) a dynamic agent architecture where Claude Code agents load instructions from external files rather than hardcoded prompts, enabling the self-improvement loop to edit instructions without modifying agent definitions, and (2) a comprehensive evaluation infrastructure that compares extracted JSON against CSV ground truth, computes precision/recall/F1 metrics, categorizes failures, and generates HTML reports with iteration tracking.

Research reveals that Claude Code's native architecture already supports dynamic instruction loading through CLAUDE.md files and the progressive disclosure pattern, where agents reference external instruction files that Claude loads on-demand. The evaluation infrastructure requires field-level JSON comparison against CSV ground truth, Python-based metric computation, error categorization (omission, hallucination, format error, wrong value), HTML report generation with Jinja2 templates, and persistent storage for tracking iterations—all well-supported by existing Python libraries and patterns.

The critical insight: Phase 1 is not about building complex multi-agent orchestration (that comes later in Phase 3-4). It's about establishing the measurement and modification infrastructure that enables all future improvement. Without dynamic instructions, the critic agent cannot propose changes. Without evaluation infrastructure, you cannot measure if changes improve extraction quality.

**Primary recommendation:** Use Claude Code's native CLAUDE.md + skills pattern for dynamic instructions, implement evaluation as a standalone Python CLI tool using Pydantic for validation and Jinja2 for HTML reports, and store results in simple file-based JSON logs (no database needed for 5 eval cases).

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Claude Code | 2.0+ | Agent runtime with native dynamic instruction loading | Official Anthropic product, native support for CLAUDE.md files and skills with external file references |
| Pydantic | 2.10+ | Schema validation and field-level JSON comparison | Industry standard for Python validation (30M+ downloads/month), native JSON schema support, field-level error reporting |
| Jinja2 | 3.1+ | HTML report template engine | Standard Python templating (100M+ downloads/month), used by pytest-html and major reporting tools |
| pytest | 8.3+ | Testing framework and CLI harness | De facto standard for Python testing, extensible plugin system for custom reporting |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-html | 4.1+ | HTML test report generation | Base framework for evaluation HTML reports with customizable templates |
| pandas | 2.2+ | CSV parsing and data manipulation | Reading ground_truth.csv files, computing aggregate metrics across fields |
| click | 8.1+ | CLI framework | Building user-friendly command-line interface for verifier agent |
| pytest-json-report | 1.5+ | JSON test output | Persisting evaluation results in structured format for iteration tracking |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File-based instruction storage | Database-backed prompt registry | File-based is simpler for R&D, easier to version control with git, no DB overhead. Use DB only if team collaboration or complex versioning becomes bottleneck. |
| pytest + Jinja2 | Custom HTML generator | pytest ecosystem provides rich plugin support, test discovery, and reporting patterns out of the box. Custom only if pytest model doesn't fit. |
| Pydantic | JSON Schema + jsonschema library | Pydantic integrates validation with Python types seamlessly, better error messages, field-level granularity. jsonschema is lower-level but more portable. |
| pandas CSV parsing | csv module | pandas provides richer data manipulation for aggregate metrics (e.g., mean F1 across fields), worth the dependency for 50+ field comparison. |

**Installation:**
```bash
# Core evaluation infrastructure
pip install pydantic pandas jinja2 click

# Testing and reporting
pip install pytest pytest-html pytest-json-report

# Alternative: Use uv for faster dependency resolution
uv pip install pydantic pandas jinja2 click pytest pytest-html pytest-json-report
```

## Architecture Patterns

### Recommended Project Structure
```
.claude/
├── agents/                  # Agent definitions (thin wrappers)
│   ├── verifier.md         # Verifier agent definition
│   └── critic.md           # Critic agent (Phase 5)
├── instructions/            # Dynamic instruction files
│   ├── verifier/
│   │   ├── instructions.md # Main verifier instructions
│   │   ├── error-types.md  # Error categorization guide
│   │   └── metrics.md      # Metric computation guide
│   └── extractors/         # Extractor instructions (Phase 3+)
└── settings.json           # Claude Code settings

evals/
├── manifest.yaml           # Eval dataset registry
├── {eval-id}/
│   ├── plans.pdf
│   ├── spec_sheet.pdf
│   ├── ground_truth.csv    # Ground truth in CBECC CSV format
│   └── results/            # Extraction results + eval reports
│       ├── iteration-001/
│       │   ├── extracted.json
│       │   ├── eval-report.html
│       │   └── eval-results.json
│       └── iteration-002/
│           └── ...

src/
├── verifier/               # Evaluation infrastructure
│   ├── __init__.py
│   ├── cli.py             # CLI entry point (verify command)
│   ├── compare.py         # Field-level comparison logic
│   ├── metrics.py         # Precision/recall/F1 computation
│   ├── categorize.py      # Error categorization
│   ├── report.py          # HTML report generation
│   └── templates/
│       └── eval-report.html.j2  # Jinja2 template
└── schemas/
    └── building_spec.py   # Pydantic schema for extraction output

tests/
└── verifier/
    └── test_compare.py    # Unit tests for comparison logic
```

### Pattern 1: Dynamic Agent Instructions (Progressive Disclosure)

**What:** Agent definitions (.claude/agents/*.md) are thin wrappers that reference external instruction files. Claude loads instruction files on-demand using progressive disclosure pattern.

**When to use:** When you need to modify agent behavior without changing agent definitions, enabling automated improvement loops to edit instructions.

**Example:**
```markdown
<!-- .claude/agents/verifier.md -->
---
name: verifier
description: Compares extracted JSON against ground truth and computes metrics
tools: Read, Write, Bash
---

<role>
You are a verifier agent that evaluates extraction quality.

Your instructions are maintained in separate files:
- Main instructions: .claude/instructions/verifier/instructions.md
- Error categorization: .claude/instructions/verifier/error-types.md
- Metrics guide: .claude/instructions/verifier/metrics.md

Read these instruction files to understand your responsibilities.
</role>

<workflow>
1. Read instruction files from .claude/instructions/verifier/
2. Load ground truth CSV and extracted JSON
3. Compare field-by-field following instructions
4. Categorize errors using error-types.md taxonomy
5. Compute metrics following metrics.md formulas
6. Generate HTML report
</workflow>
```

```markdown
<!-- .claude/instructions/verifier/instructions.md -->
# Verifier Instructions v1.0.0

## Purpose
Compare extracted BuildingSpec JSON against ground_truth.csv and report discrepancies.

## Field Comparison Process

For each field in ground_truth.csv:
1. Extract expected value from CSV
2. Navigate to corresponding field in extracted JSON
3. Compare values using appropriate comparison logic:
   - Numeric: tolerance of ±0.5% or ±0.01 (whichever is larger)
   - String: case-insensitive exact match after trimming whitespace
   - Boolean: exact match
4. If mismatch, categorize error using error-types.md taxonomy
5. Record discrepancy with context

[... rest of instructions ...]
```

**Benefits:**
- Agent definition remains stable (checked into version control)
- Instructions can be modified by improvement loop
- Clear separation of agent scaffolding vs. behavior
- Git tracks instruction changes separately from code changes

### Pattern 2: Field-Level JSON Comparison with Pydantic

**What:** Define Pydantic schema matching ground truth structure, validate extracted JSON against schema, compare field-by-field to identify specific discrepancies.

**When to use:** When you need precise error reporting at field granularity (not just "extraction failed" but "window_count: expected 4, got 3").

**Example:**
```python
# src/schemas/building_spec.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class ProjectInfo(BaseModel):
    """Project metadata from ground truth."""
    run_title: str = Field(description="Project title")
    address: str = Field(description="Street address")
    city: str = Field(description="City name")
    climate_zone: int = Field(ge=1, le=16, description="CA climate zone 1-16")

    @field_validator('climate_zone')
    def validate_climate_zone(cls, v):
        if v not in range(1, 17):
            raise ValueError(f"Invalid climate zone: {v}")
        return v

class EnvelopeInfo(BaseModel):
    """Building envelope data."""
    conditioned_floor_area: float = Field(gt=0, description="CFA in sq ft")
    window_area: float = Field(ge=0, description="Total window area sq ft")
    window_to_floor_ratio: float = Field(ge=0, le=1, description="WWR")

class BuildingSpec(BaseModel):
    """Complete building specification from extraction."""
    project: ProjectInfo
    envelope: EnvelopeInfo
    # ... additional sections

# src/verifier/compare.py
from typing import Dict, Any, List
from pydantic import ValidationError

class FieldDiscrepancy:
    def __init__(self, field_path: str, expected: Any, actual: Any, error_type: str):
        self.field_path = field_path
        self.expected = expected
        self.actual = actual
        self.error_type = error_type

def compare_fields(ground_truth: Dict, extracted: Dict, schema: type[BaseModel]) -> List[FieldDiscrepancy]:
    """Compare extracted data against ground truth, return field-level discrepancies."""
    discrepancies = []

    # Validate extracted data against schema first
    try:
        validated = schema(**extracted)
    except ValidationError as e:
        for error in e.errors():
            field_path = '.'.join(str(loc) for loc in error['loc'])
            discrepancies.append(FieldDiscrepancy(
                field_path=field_path,
                expected="valid value",
                actual=extracted.get(field_path),
                error_type="format_error"
            ))
        return discrepancies

    # Field-by-field comparison
    for field_path, expected_value in flatten_dict(ground_truth).items():
        actual_value = get_nested_value(extracted, field_path)

        if actual_value is None:
            discrepancies.append(FieldDiscrepancy(
                field_path, expected_value, None, "omission"
            ))
        elif not values_match(expected_value, actual_value):
            discrepancies.append(FieldDiscrepancy(
                field_path, expected_value, actual_value, "wrong_value"
            ))

    # Check for hallucinated fields (present in extracted but not in ground truth)
    for field_path, actual_value in flatten_dict(extracted).items():
        if field_path not in flatten_dict(ground_truth):
            discrepancies.append(FieldDiscrepancy(
                field_path, None, actual_value, "hallucination"
            ))

    return discrepancies
```

### Pattern 3: Error Categorization Taxonomy

**What:** Classify each field-level discrepancy into standardized error types (omission, hallucination, format_error, wrong_value) to enable targeted improvement.

**When to use:** When building self-improvement loop—error categories inform which instructions to modify.

**Error Taxonomy:**
| Error Type | Definition | Example | Improvement Signal |
|------------|------------|---------|-------------------|
| **omission** | Expected field missing from extraction | ground_truth has `bedrooms: 2`, extracted JSON missing `bedrooms` | Extractor instructions need to emphasize completeness, add field to checklist |
| **hallucination** | Field present in extraction but not in ground truth | Extracted `garage_area: 400` but ground truth has no garage | Extractor instructions need to emphasize evidence grounding, add validation |
| **format_error** | Field present but wrong type/format | Expected `climate_zone: 12` (int), got `climate_zone: "12"` (string) | Schema enforcement in extraction, add type hints to instructions |
| **wrong_value** | Field present, correct type, but incorrect value | Expected `window_count: 4`, got `window_count: 3` | Extractor instructions need domain-specific guidance (e.g., "count all windows on all elevations") |

**Implementation:**
```python
# src/verifier/categorize.py
def categorize_error(discrepancy: FieldDiscrepancy, schema: type[BaseModel]) -> str:
    """Categorize error type for improvement loop."""
    if discrepancy.expected is None and discrepancy.actual is not None:
        return "hallucination"

    if discrepancy.actual is None and discrepancy.expected is not None:
        return "omission"

    # Check if type mismatch
    expected_type = get_field_type(schema, discrepancy.field_path)
    actual_type = type(discrepancy.actual)
    if expected_type != actual_type:
        return "format_error"

    # Value mismatch with correct type
    return "wrong_value"
```

### Pattern 4: HTML Report Generation with Jinja2

**What:** Generate human-readable HTML reports showing evaluation results, field comparisons, error breakdown, and metrics using Jinja2 templates.

**When to use:** Always—reports are critical for debugging extraction issues and demonstrating improvement across iterations.

**Example:**
```python
# src/verifier/report.py
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

class EvalReport:
    def __init__(self, eval_id: str, iteration: int, discrepancies: List[FieldDiscrepancy], metrics: Dict):
        self.eval_id = eval_id
        self.iteration = iteration
        self.discrepancies = discrepancies
        self.metrics = metrics

    def generate_html(self, output_path: Path):
        """Generate HTML report using Jinja2 template."""
        env = Environment(loader=FileSystemLoader('src/verifier/templates'))
        template = env.get_template('eval-report.html.j2')

        # Group discrepancies by error type
        errors_by_type = {}
        for d in self.discrepancies:
            errors_by_type.setdefault(d.error_type, []).append(d)

        html = template.render(
            eval_id=self.eval_id,
            iteration=self.iteration,
            metrics=self.metrics,
            discrepancies=self.discrepancies,
            errors_by_type=errors_by_type,
            total_fields=self.metrics['total_fields'],
            correct_fields=self.metrics['correct_fields']
        )

        output_path.write_text(html)
```

```html
<!-- src/verifier/templates/eval-report.html.j2 -->
<!DOCTYPE html>
<html>
<head>
    <title>Evaluation Report: {{ eval_id }} - Iteration {{ iteration }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background: #f0f0f0; border-radius: 5px; }
        .error-omission { background: #ffecb3; }
        .error-hallucination { background: #ffcdd2; }
        .error-format_error { background: #e1bee7; }
        .error-wrong_value { background: #b3e5fc; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>Evaluation Report: {{ eval_id }}</h1>
    <p>Iteration: {{ iteration }} | Date: {{ metrics.timestamp }}</p>

    <h2>Metrics</h2>
    <div class="metric">
        <strong>Precision:</strong> {{ "%.3f"|format(metrics.precision) }}
    </div>
    <div class="metric">
        <strong>Recall:</strong> {{ "%.3f"|format(metrics.recall) }}
    </div>
    <div class="metric">
        <strong>F1 Score:</strong> {{ "%.3f"|format(metrics.f1) }}
    </div>
    <div class="metric">
        <strong>Accuracy:</strong> {{ correct_fields }}/{{ total_fields }} fields correct
    </div>

    <h2>Error Breakdown</h2>
    <table>
        <tr>
            <th>Error Type</th>
            <th>Count</th>
            <th>Percentage</th>
        </tr>
        {% for error_type, errors in errors_by_type.items() %}
        <tr class="error-{{ error_type }}">
            <td>{{ error_type }}</td>
            <td>{{ errors|length }}</td>
            <td>{{ "%.1f"|format(100 * errors|length / discrepancies|length) }}%</td>
        </tr>
        {% endfor %}
    </table>

    <h2>Field-Level Discrepancies</h2>
    <table>
        <tr>
            <th>Field</th>
            <th>Expected</th>
            <th>Actual</th>
            <th>Error Type</th>
        </tr>
        {% for d in discrepancies %}
        <tr class="error-{{ d.error_type }}">
            <td><code>{{ d.field_path }}</code></td>
            <td>{{ d.expected }}</td>
            <td>{{ d.actual }}</td>
            <td>{{ d.error_type }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

### Pattern 5: Iteration Tracking with File-Based Storage

**What:** Store evaluation results as JSON files in iteration-numbered directories, enabling tracking of improvement across iterations and rollback.

**When to use:** From Phase 1 onward—every evaluation run should be persisted for iteration tracking.

**Structure:**
```
evals/
└── lamb-adu/
    └── results/
        ├── iteration-001/
        │   ├── extracted.json        # Raw extraction output
        │   ├── eval-results.json     # Structured eval results
        │   └── eval-report.html      # Human-readable report
        ├── iteration-002/
        │   └── ...
        └── aggregate.json            # Metrics across all iterations
```

```python
# src/verifier/persistence.py
from pathlib import Path
import json
from datetime import datetime

class EvalStore:
    def __init__(self, evals_dir: Path = Path("evals")):
        self.evals_dir = evals_dir

    def get_next_iteration(self, eval_id: str) -> int:
        """Get next iteration number for this eval."""
        results_dir = self.evals_dir / eval_id / "results"
        if not results_dir.exists():
            return 1

        existing = [d.name for d in results_dir.iterdir() if d.is_dir()]
        iterations = [int(d.split('-')[1]) for d in existing if d.startswith('iteration-')]
        return max(iterations, default=0) + 1

    def save_evaluation(self, eval_id: str, iteration: int, extracted: Dict, results: Dict, report_html: str):
        """Save evaluation results for this iteration."""
        iter_dir = self.evals_dir / eval_id / "results" / f"iteration-{iteration:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        # Save extracted JSON
        (iter_dir / "extracted.json").write_text(json.dumps(extracted, indent=2))

        # Save eval results
        results['metadata'] = {
            'eval_id': eval_id,
            'iteration': iteration,
            'timestamp': datetime.now().isoformat()
        }
        (iter_dir / "eval-results.json").write_text(json.dumps(results, indent=2))

        # Save HTML report
        (iter_dir / "eval-report.html").write_text(report_html)

        # Update aggregate metrics
        self._update_aggregate(eval_id, iteration, results)

    def _update_aggregate(self, eval_id: str, iteration: int, results: Dict):
        """Update aggregate.json with metrics from this iteration."""
        agg_path = self.evals_dir / eval_id / "results" / "aggregate.json"

        if agg_path.exists():
            aggregate = json.loads(agg_path.read_text())
        else:
            aggregate = {'iterations': []}

        aggregate['iterations'].append({
            'iteration': iteration,
            'timestamp': results['metadata']['timestamp'],
            'precision': results['metrics']['precision'],
            'recall': results['metrics']['recall'],
            'f1': results['metrics']['f1'],
            'total_errors': len(results['discrepancies']),
            'errors_by_type': results['errors_by_type']
        })

        agg_path.write_text(json.dumps(aggregate, indent=2))
```

### Anti-Patterns to Avoid

- **Hardcoding instructions in agent definitions:** Prevents critic from proposing improvements. Always separate instructions into external files.
- **Passing judgment without field-level detail:** "Extraction failed" is useless. Always report specific field discrepancies with expected vs. actual values.
- **Computing metrics incorrectly:** Precision/recall/F1 must be computed at field level, not document level. Each field is a binary classification (correct/incorrect).
- **Database for 5 eval cases:** Massive overkill. File-based JSON storage is simpler, easier to inspect, and version-controllable with git.
- **Complex diff algorithms:** String fields need simple exact match (case-insensitive, trimmed). Numeric fields need tolerance-based comparison. Don't overcomplicate.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom validator with isinstance() checks | Pydantic BaseModel | Field-level validation, automatic type coercion, rich error messages, JSON schema export |
| HTML template rendering | String concatenation or f-strings | Jinja2 | Template inheritance, auto-escaping, loops/conditionals, industry standard |
| CLI argument parsing | sys.argv parsing | click or argparse | Automatic help generation, type conversion, validation, subcommands |
| CSV parsing | Manual split() and strip() | pandas.read_csv() | Handles edge cases (quoted commas, newlines in fields, encoding), provides rich data manipulation |
| Precision/recall/F1 computation | Manual formula implementation | scikit-learn metrics (for validation) | Well-tested, handles edge cases (division by zero), but still implement custom for field-level granularity |

**Key insight:** Use libraries for infrastructure (validation, templating, CLI, CSV), implement custom logic only for domain-specific comparison (field-level extraction comparison is unique to your problem).

## Common Pitfalls

### Pitfall 1: Agent Definition Bloat

**What goes wrong:** Instructions get embedded in agent definitions, making them long and rigid. Critic cannot modify behavior without touching agent code.

**Why it happens:** It's easier to write everything in one file initially. Separation of concerns requires upfront design.

**How to avoid:**
- Agent definitions should be <50 lines, mostly metadata and file references
- All behavioral instructions go in .claude/instructions/{agent}/ directory
- Agent reads instruction files in workflow section

**Warning signs:**
- Agent definition file >100 lines
- Critic proposing edits to .claude/agents/*.md files
- Instructions contain domain knowledge (should be in separate files)

### Pitfall 2: Metric Computation Errors

**What goes wrong:** Computing precision/recall/F1 at document level instead of field level, or using wrong formulas, leading to misleading metrics.

**Why it happens:** Confusion between document-level classification (is this a building plan?) and field-level extraction (did we extract window_count correctly?).

**How to avoid:**
- Each field is a binary classification: correct (1) or incorrect (0)
- Precision = # correct fields / # fields in extracted JSON
- Recall = # correct fields / # fields in ground truth
- F1 = 2 * (P * R) / (P + R)
- Compute aggregate F1 as average across all fields

**Warning signs:**
- F1 scores that don't match intuition (50% fields wrong but 90% F1)
- Precision + recall > 1.0 (impossible)
- Cannot explain metric to non-technical stakeholder

### Pitfall 3: CSV/JSON Impedance Mismatch

**What goes wrong:** Ground truth CSV is flat (comma-separated values with header row), but extraction output is nested JSON. Field paths like `project.climate_zone` don't map cleanly to CSV columns like `Climate Zone`.

**Why it happens:** CSV is legacy format from CBECC-Res tool, JSON is modern extraction format.

**How to avoid:**
- Define explicit mapping from CSV column names to JSON field paths
- Store mapping in `schemas/field_mapping.yaml`:
  ```yaml
  csv_to_json:
    "Climate Zone": "project.climate_zone"
    "Conditioned Floor Area": "envelope.conditioned_floor_area"
    "Bedrooms": "project.bedrooms"
  ```
- Use mapping in comparison logic to navigate between formats

**Warning signs:**
- Comparison code has hardcoded column names scattered throughout
- Adding new field requires changes in 5+ places
- Cannot easily explain which CSV column maps to which JSON field

### Pitfall 4: Tolerance Specification for Numeric Fields

**What goes wrong:** Using exact equality for floating-point comparisons, causing false negatives when ground truth is `0.311` and extraction is `0.3109999`.

**Why it happens:** Floating-point representation, unit conversions, rounding in different tools.

**How to avoid:**
- Define tolerance per field type in schema:
  ```python
  class NumericField(BaseModel):
      value: float
      tolerance_percent: float = 0.5  # ±0.5%
      tolerance_absolute: float = 0.01  # ±0.01 units

  def values_match_numeric(expected: float, actual: float, tolerance: NumericField) -> bool:
      abs_diff = abs(expected - actual)
      rel_diff = abs_diff / expected if expected != 0 else abs_diff

      return (rel_diff <= tolerance.tolerance_percent / 100 or
              abs_diff <= tolerance.tolerance_absolute)
  ```

**Warning signs:**
- Discrepancies for values like `1200.0` vs `1200` (formatting issue)
- Failures for `0.311` vs `0.31` (precision issue)
- Different tolerances needed for different field types (area vs. ratio)

### Pitfall 5: Iteration Tracking Gaps

**What goes wrong:** Evaluation results are generated but not persisted, or persisted without metadata (timestamp, instruction version), making it impossible to track improvement or rollback.

**Why it happens:** Focus on generating reports, not on storing results for future analysis.

**How to avoid:**
- EVERY evaluation run saves:
  - Raw extracted JSON
  - Evaluation results JSON (discrepancies, metrics, metadata)
  - HTML report
  - Timestamp and instruction file hashes
- Use iteration-numbered directories (iteration-001, iteration-002)
- Generate aggregate.json tracking metrics across iterations

**Warning signs:**
- Cannot answer "how has F1 changed over the last 10 iterations?"
- No way to identify which instruction version produced which results
- Rollback requires manual memory of what changed when

### Pitfall 6: Report Generation Performance

**What goes wrong:** Generating HTML reports for large discrepancy lists (1000+ errors) becomes slow or produces multi-MB HTML files that browsers struggle to render.

**Why it happens:** Rendering every single discrepancy in HTML, no pagination or filtering.

**How to avoid:**
- Limit HTML report to top N discrepancies per error type (e.g., 50 omissions, 50 hallucinations)
- Full discrepancy list goes in JSON output (eval-results.json)
- Add filtering UI in HTML (show/hide error types)
- Consider summary view by default with expandable details

**Warning signs:**
- Report generation takes >5 seconds
- HTML file >5MB
- Browser tab freezes when opening report

## Code Examples

Verified patterns from official sources:

### Field-Level F1 Computation

```python
# src/verifier/metrics.py
from typing import Dict, List

def compute_field_level_metrics(discrepancies: List[FieldDiscrepancy], total_fields_gt: int, total_fields_extracted: int) -> Dict[str, float]:
    """
    Compute precision, recall, F1 at field level.

    Each field is a binary classification:
    - True Positive (TP): field present in both, values match
    - False Positive (FP): field in extracted but wrong/hallucinated
    - False Negative (FN): field in ground truth but omitted
    """
    # Count error types
    omissions = sum(1 for d in discrepancies if d.error_type == "omission")
    hallucinations = sum(1 for d in discrepancies if d.error_type == "hallucination")
    wrong_values = sum(1 for d in discrepancies if d.error_type in ["wrong_value", "format_error"])

    # True positives: fields in ground truth that were correctly extracted
    true_positives = total_fields_gt - omissions - wrong_values

    # False positives: hallucinations + wrong values
    false_positives = hallucinations + wrong_values

    # False negatives: omissions
    false_negatives = omissions

    # Compute metrics with zero-division handling
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'total_fields': total_fields_gt,
        'correct_fields': true_positives
    }
```
*Source: Standard precision/recall/F1 formulas adapted for field-level extraction*

### CLI for Running Verifier

```python
# src/verifier/cli.py
import click
from pathlib import Path
from .compare import compare_fields
from .metrics import compute_field_level_metrics
from .report import EvalReport
from .persistence import EvalStore

@click.group()
def cli():
    """Takeoff v2 Verifier - Evaluate extraction quality against ground truth."""
    pass

@cli.command()
@click.argument('eval_id')
@click.argument('extracted_json', type=click.Path(exists=True))
@click.option('--output-dir', type=click.Path(), default=None, help='Output directory for report')
def verify_one(eval_id: str, extracted_json: str, output_dir: str):
    """
    Run verification on a single extraction result.

    Example:
        python -m verifier verify-one lamb-adu results/extracted.json
    """
    store = EvalStore()

    # Load ground truth
    ground_truth_path = Path("evals") / eval_id / "ground_truth.csv"
    ground_truth = load_ground_truth_csv(ground_truth_path)

    # Load extracted JSON
    extracted = json.loads(Path(extracted_json).read_text())

    # Compare
    discrepancies = compare_fields(ground_truth, extracted, BuildingSpec)

    # Compute metrics
    metrics = compute_field_level_metrics(
        discrepancies,
        len(flatten_dict(ground_truth)),
        len(flatten_dict(extracted))
    )

    # Generate report
    iteration = store.get_next_iteration(eval_id)
    report = EvalReport(eval_id, iteration, discrepancies, metrics)

    output_path = Path(output_dir or f"evals/{eval_id}/results/iteration-{iteration:03d}")
    output_path.mkdir(parents=True, exist_ok=True)

    report.generate_html(output_path / "eval-report.html")

    # Save results
    store.save_evaluation(eval_id, iteration, extracted, {
        'discrepancies': [d.__dict__ for d in discrepancies],
        'metrics': metrics,
        'errors_by_type': categorize_errors(discrepancies)
    }, (output_path / "eval-report.html").read_text())

    click.echo(f"✓ Verification complete for {eval_id}")
    click.echo(f"  F1: {metrics['f1']:.3f} | Precision: {metrics['precision']:.3f} | Recall: {metrics['recall']:.3f}")
    click.echo(f"  Report: {output_path / 'eval-report.html'}")

@cli.command()
@click.option('--evals-dir', type=click.Path(exists=True), default='evals', help='Evals directory')
def verify_all(evals_dir: str):
    """
    Run verification on all 5 evals and show aggregate metrics.

    Example:
        python -m verifier verify-all
    """
    from .loader import load_manifest

    manifest = load_manifest(Path(evals_dir) / "manifest.yaml")
    results = []

    for eval_id, eval_config in manifest['evals'].items():
        # Find latest extraction result
        results_dir = Path(evals_dir) / eval_id / "results"
        if not results_dir.exists():
            click.echo(f"⚠ No results for {eval_id}, skipping")
            continue

        latest_iter = max([d for d in results_dir.iterdir() if d.is_dir()],
                         key=lambda p: p.name)
        extracted_path = latest_iter / "extracted.json"

        if not extracted_path.exists():
            click.echo(f"⚠ No extracted.json for {eval_id}, skipping")
            continue

        # Run verification (reuse verify_one logic)
        # ... (omitted for brevity)

        results.append({
            'eval_id': eval_id,
            'f1': metrics['f1'],
            'precision': metrics['precision'],
            'recall': metrics['recall']
        })

    # Aggregate metrics
    avg_f1 = sum(r['f1'] for r in results) / len(results)
    avg_precision = sum(r['precision'] for r in results) / len(results)
    avg_recall = sum(r['recall'] for r in results) / len(results)

    click.echo("\n=== Aggregate Metrics Across All Evals ===")
    click.echo(f"Average F1:        {avg_f1:.3f}")
    click.echo(f"Average Precision: {avg_precision:.3f}")
    click.echo(f"Average Recall:    {avg_recall:.3f}")
    click.echo("\nPer-Eval Breakdown:")
    for r in results:
        click.echo(f"  {r['eval_id']:20s} F1: {r['f1']:.3f}")

if __name__ == '__main__':
    cli()
```
*Source: Click CLI patterns from official documentation*

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded prompts in agent code | Dynamic instructions in external files (.claude/instructions/) | Claude Code 2.0 (2025) | Enables automated improvement loops to modify agent behavior without code changes |
| Document-level pass/fail | Field-level precision/recall/F1 | LLM evaluation best practices (2024-2025) | Enables targeted improvements (e.g., "window extraction needs work" vs. "extraction failed") |
| Manual report generation | Automated HTML reports with Jinja2 templates | pytest-html pattern (established 2020+, refined 2025) | Reduces reporting overhead from hours to seconds, enables iteration tracking |
| Database for eval storage | File-based JSON with git versioning | Shift toward simplicity in R&D (2025-2026) | Simpler, more inspectable, easier rollback with git |

**Deprecated/outdated:**
- **Embedding prompts in agent definitions:** Claude Code 2.0 progressive disclosure pattern supersedes this. Always use external instruction files.
- **pytest-json:** Still used, but pytest-json-report (2023+) provides richer structured output with metadata.

## Open Questions

Things that couldn't be fully resolved:

1. **CSV column to JSON field mapping strategy**
   - What we know: Ground truth CSV has human-readable column names ("Climate Zone"), extraction uses JSON field paths (project.climate_zone)
   - What's unclear: Best way to maintain mapping—hardcoded dict, YAML config, or inferred from schema annotations?
   - Recommendation: Start with YAML config file (schemas/field_mapping.yaml) for explicit control, refactor to schema annotations if mapping becomes complex

2. **Numeric tolerance specification per field**
   - What we know: Different fields need different tolerances (area ±10 sq ft vs. ratio ±0.01)
   - What's unclear: Should tolerances be in schema, config file, or inferred from value magnitude?
   - Recommendation: Add tolerance as Field() parameter in Pydantic schema with sensible defaults, override in config for special cases

3. **Aggregate vs. per-eval F1 computation**
   - What we know: Can compute F1 per eval then average, or pool all fields across evals then compute F1
   - What's unclear: Which better represents system performance when eval difficulty varies?
   - Recommendation: Compute both, report macro-F1 (average of per-eval F1s) as primary metric, include pooled F1 in reports

4. **Iteration tracking across instruction file changes**
   - What we know: Need to link eval results to instruction file versions
   - What's unclear: Store git commit hash, file content hash, or manual version numbers?
   - Recommendation: Store git commit hash in eval metadata (git rev-parse HEAD), enables exact reproduction

## Sources

### Primary (HIGH confidence)

- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices) - Agent architecture patterns
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents) - Subagent patterns and file references
- [Using CLAUDE.MD files - Claude Blog](https://claude.com/blog/using-claude-md-files) - CLAUDE.md three-tier memory hierarchy
- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills) - Progressive disclosure pattern for external files
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) - Field-level validation and schema customization
- [Pydantic Fields](https://docs.pydantic.dev/latest/concepts/fields/) - Field() function for customization
- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/) - Template syntax and patterns
- [pytest-html PyPI](https://pypi.org/project/pytest-html/) - HTML report generation for pytest
- [Click Documentation](https://click.palletsprojects.com/) - CLI framework patterns

### Secondary (MEDIUM confidence)

- [Learning Claude Code - Multi-Agent Workflows](https://medium.com/@aayushmnit/learning-claude-code-from-context-engineering-to-multi-agent-workflows-4825e216403f) - Multi-agent patterns and context management
- [DeepJSONEval: Benchmarking Complex Nested JSON Data Mining](https://arxiv.org/html/2509.25922v1) - JSON ground truth evaluation patterns
- [Tensorlake JSON F1 Evaluation](https://www.tensorlake.ai/blog/benchmarks) - Field-level precision/recall/F1 for JSON extraction
- [DeepEval - LLM Evaluation Framework](https://github.com/confident-ai/deepeval) - Pytest-based LLM evaluation patterns
- [MLflow Evaluating LLMs/Agents](https://mlflow.org/docs/latest/genai/eval-monitor/) - Evaluation tracking and persistence
- [W&B Weave Documentation](https://docs.wandb.ai/models/track/public-api-guide) - Iteration tracking and lineage
- [Classification: Accuracy, recall, precision - Google ML](https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall) - Metric computation formulas

### Tertiary (LOW confidence)

- [GitHub: awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) - Community patterns and examples
- [Optimizing Agentic Coding: How to Use Claude Code in 2026](https://research.aimultiple.com/agentic-coding/) - High-level best practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All recommended libraries are official, actively maintained, with extensive documentation and large user bases (Pydantic 30M+/month downloads, pytest industry standard)
- Architecture: HIGH - Claude Code patterns verified from official Anthropic documentation, Pydantic/Jinja2 patterns from official docs
- Pitfalls: MEDIUM - Based on general software engineering practices and LLM evaluation best practices, domain-specific validation needed during implementation

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (60 days - stable technologies with established patterns)
