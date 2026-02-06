# Architecture & Style Review — TakeOff2

## Executive Summary

TakeOff2 is a ~7,700-line Python system for extracting building specifications from Title 24 architectural PDFs using Claude Code agents. The codebase is well-conceived at the system level — the multi-agent extraction pipeline, self-improvement loop, and CV sensor integration are strong architectural choices. However, a number of structural and stylistic issues have accumulated that will impede maintainability, testability, and reliability as the system matures.

This review identifies **40+ concrete issues** organized into 10 categories, ranked by impact.

---

## Table of Contents

1. [Critical: God Object Orchestrator](#1-critical-god-object-orchestrator)
2. [Critical: No Test Infrastructure](#2-critical-no-test-infrastructure)
3. [High: Pervasive Code Duplication](#3-high-pervasive-code-duplication)
4. [High: Redundant Root-Level Scripts](#4-high-redundant-root-level-scripts)
5. [High: Untyped Intermediate Results](#5-high-untyped-intermediate-results)
6. [Medium: Inconsistent Error Handling](#6-medium-inconsistent-error-handling)
7. [Medium: Schema Design Gaps](#7-medium-schema-design-gaps)
8. [Medium: Build Configuration Issues](#8-medium-build-configuration-issues)
9. [Low: Style Inconsistencies](#9-low-style-inconsistencies)
10. [Low: Magic Numbers and Hardcoded Values](#10-low-magic-numbers-and-hardcoded-values)

---

## 1. Critical: God Object Orchestrator

**File:** `src/agents/orchestrator.py` — 1,822 lines, 71 KB

This file is the single largest structural problem in the codebase. It handles **seven distinct responsibilities** in one module:

| Responsibility | Key Functions |
|---|---|
| PDF discovery | `discover_source_pdfs` |
| CV sensor orchestration | `run_cv_sensors`, `_convert_numpy_types` |
| Page routing / domain mapping | `get_relevant_pages_for_domain`, `build_pdf_read_instructions` |
| Agent invocation (sync + async) | `invoke_claude_agent`, `invoke_claude_agent_async` |
| Orientation extraction (6 functions) | `run_orientation_extraction`, `run_orientation_pass_async`, `verify_orientation_passes`, `run_orientation_twopass_async`, `run_orientation_twopass`, `_azimuth_to_direction` |
| Result merging | `merge_extractions`, `merge_to_takeoff_spec`, `deduplicate_by_name` |
| Main pipeline + caching | `run_extraction` (235 lines alone) |

### Specific issues

- **`run_extraction`** (lines 1588–1822) is 235 lines long and manages PDF discovery, three separate caching strategies, two nested async closures, parallel extraction, merging, transformation, legacy conflict detection, orientation injection, logging, timing, and result dict construction — all in one function.

- **Dual `asyncio.run()` calls** (lines 1713 and 1735) within the same synchronous function. Each creates and destroys an event loop. Calling `asyncio.run()` when a loop is already running (e.g., if the caller is async) will raise `RuntimeError`. The module-level `EXTRACTION_SEMAPHORE` (line 47) is bound to no specific loop, making it ineffective across separate `asyncio.run()` invocations.

- **Legacy + new code paths run simultaneously** (lines 1748–1760): Both `merge_to_takeoff_spec` and `merge_extractions` are called on the same data. The legacy merge result is discarded (`_`), with only conflict detection and status kept. This is wasteful double-processing from an incomplete migration.

- **`numpy` imported for a single helper** (line 30): `import numpy as np` exists solely for the `_convert_numpy_types` function, which is a CV sensor concern, not an orchestration concern.

### Recommended decomposition

```
agents/invoke.py       — invoke_claude_agent, invoke_claude_agent_async, extract_json_from_response, extract_with_retry
agents/discovery.py    — discover_source_pdfs, run_discovery (already partially exists)
agents/orientation.py  — all orientation-related functions (6 functions, ~360 lines)
agents/routing.py      — get_relevant_pages_for_domain, build_pdf_read_instructions, build_domain_prompt
agents/merge.py        — merge_extractions, merge_to_takeoff_spec, deduplicate_by_name
agents/orchestrator.py — only run_extraction (the pipeline conductor), substantially simplified
```

---

## 2. Critical: No Test Infrastructure

Despite `pytest>=8.3` being listed as a dev dependency, there are **zero pytest-compatible test files** anywhere in the project. The `test_*.py` files at the project root are standalone scripts with `if __name__ == "__main__"` entry points that produce human-readable output via `print()`.

### What's missing

| Area | Impact |
|---|---|
| No `tests/` directory | No conventional test location |
| No `[tool.pytest.ini_options]` in `pyproject.toml` | `pytest` cannot discover tests or resolve imports |
| No unit tests for `verifier/compare.py` | Field comparison logic (the core correctness guarantee) is untested |
| No unit tests for `verifier/metrics.py` | Metric computation (F1/precision/recall) is untested |
| No unit tests for `schemas/transform.py` | Schema transformation (TakeoffSpec → BuildingSpec) is untested |
| No unit tests for `improvement/apply.py` | Proposal application and version bumping logic is untested |
| No unit tests for `cv_sensors/` | Angle computation (including circular math) is untested |
| No CLI tests via Click's `CliRunner` | Exit codes, argument parsing, and error messages are untested |
| No schema validation tests | Pydantic model round-trip (dump → validate) correctness is unverified |

### Existing "test" scripts are problematic

- **Not collected by pytest**: They use bare `assert` inside `try/except Exception` blocks (`test_cv_sensors.py` lines 56–63), which swallows assertion failures.
- **Hardcoded relative paths**: Every script opens with `sys.path.insert(0, str(Path(__file__).parent / "src"))` and uses `Path("evals")` — they only work from the project root.
- **Not idempotent**: The orientation tests invoke live Claude agents, which are non-deterministic and slow.

### Recommendation

Create a `tests/` directory with proper pytest structure. Prioritize unit tests for pure functions (`angular_distance`, `values_match`, `compare_fields`, `compute_field_level_metrics`, `_transform_wall`, `parse_instruction_version`, `bump_version`). These functions have well-defined inputs and outputs and require no mocking.

---

## 3. High: Pervasive Code Duplication

### 3a. Ground truth dictionary duplicated 4–6 times

The `GROUND_TRUTH` orientation dict appears identically in `test_orientation.py`, `test_orientation_fast.py`, `test_orientation_twopass.py`, and `improve_orientation.py`. The eval list in `run_extract_all.py` and `test_cv_sensors.py` are further representations of the same data. Adding a sixth eval case requires editing 6+ files.

### 3b. `angular_distance` function duplicated 4 times

Identical implementations exist in all four orientation-related scripts. This is a pure function that belongs in a shared utility module.

### 3c. Cache read/write pattern duplicated 3 times in orchestrator

`run_extraction` (lines 1640–1728) repeats the same cache-load pattern for discovery, orientation, and project data:
```python
cache_file = cache_dir / f"{eval_name}_TYPE.json"
if cache_file.exists():
    try:
        with open(cache_file) as cf:
            cache_data = json.load(cf)
        ...
    except Exception:
        ...
```
This should be a single `load_json_cache(path) -> Optional[dict]` helper.

### 3d. CV hints section injection duplicated twice

Lines 655–663 and 759–767 in `orchestrator.py` contain character-for-character identical code blocks building the CV hints prompt section.

### 3e. Orientation data injection duplicated 3 times

The same three-field injection (`front_orientation`, `orientation_confidence`, `orientation_verification`) occurs at lines 1076–1080, 1743–1746, and 1768–1771 in the orchestrator.

### 3f. `compare_fields` and `compare_all_fields` share ~80% logic

In `verifier/compare.py`, these two functions duplicate the error-type determination block verbatim (lines 244–253 vs. 310–320). `compare_fields` could be a one-line filter over `compare_all_fields` results.

### 3g. Discrepancy-to-dict conversion duplicated 3 times in verifier CLI

`verifier/cli.py` contains three identical dict-comprehension blocks converting `FieldDiscrepancy` objects to dicts (lines 256–268, 281–289, 437–448).

### 3h. Iteration save/report logic duplicated between verify_one and verify_all

Lines 273–346 (`verify_one`) and 494–535 (`verify_all`) contain near-identical EvalStore/EvalReport construction and save logic.

### 3i. `find_latest_iteration` implemented twice

`critic.py` has `find_latest_iteration` (lines 11–41) using regex matching, while `cli.py` has `get_latest_iteration` (lines 31–42) using string splitting. Same purpose, different implementations, different fragility profiles.

### 3j. Error type constants hardcoded in 3 places

The list `["omission", "hallucination", "wrong_value", "format_error"]` appears in `critic.py:120`, `improvement/cli.py:77-80`, and `review.py:178`. Should be a shared constant.

### 3k. Duplicate enums across schema files

`ComponentStatus` and `ZoneType` are character-for-character identical in both `building_spec.py` (lines 34–43) and `takeoff_spec.py` (lines 36–46). These should live in a shared `enums.py`.

### 3l. `ProjectInfo` vs `TakeoffProjectInfo` share ~15 identical fields

Both models define the same fields (`run_id`, `run_title`, `address`, `city`, `climate_zone`, `fuel_type`, `house_type`, `dwelling_units`, `stories`, `bedrooms`, `front_orientation`, etc.) with identical types and descriptions. There is no shared base class.

---

## 4. High: Redundant Root-Level Scripts

Eight root-level scripts duplicate functionality already available in the CLI modules:

| Script | Redundant With | Should Be |
|---|---|---|
| `run_extract.py` | `extractor extract-one` | Deleted |
| `run_extract_all.py` | `extractor extract-all` | Deleted (add `--workers N` flag to CLI) |
| `run_extract_all.sh` | `run_extract_all.py` | Deleted |
| `improve_orientation.py` | `improvement improve --focus orientation-extractor` | Deleted |
| `improve_orientation_fast.py` | `improvement improve` | Deleted (has forked `apply_proposal` that will drift) |
| `test_orientation.py` | Superseded by twopass variant | Deleted |
| `test_orientation_fast.py` | Superseded by twopass variant | Folded into proper test |
| `test_orientation_twopass.py` | Should be CLI command or pytest | Refactored into `tests/` or CLI |

`improve_orientation_fast.py` is particularly concerning — it contains a 95-line reimplementation of `apply_proposal` and its own `extract_json_from_response`, bypassing the library versions. These forks will inevitably drift from the canonical implementations.

---

## 5. High: Untyped Intermediate Results

Approximately 8 functions in the orchestrator and multiple functions across the verifier and improvement modules return `Dict[str, Any]` or bare `dict` for well-structured data. This defeats the purpose of having Pydantic schemas elsewhere.

### Examples

| Function | Returns | Actually Contains |
|---|---|---|
| `run_cv_sensors` | `Dict[str, Any]` | `{north_arrow_angle, confidence, method, wall_edges}` |
| `run_orientation_extraction` | `Dict[str, Any]` | `{front_orientation, confidence, verification, notes}` |
| `verify_orientation_passes` | `Dict[str, Any]` | `{final_orientation, confidence, verification, notes}` |
| `run_extraction` | `dict` | `{eval_name, building_spec, takeoff_spec, timing, error, ...}` |
| `compute_field_level_metrics` | `Dict[str, float]` | Actually `Dict[str, Union[float, int, Dict[str, int]]]` |
| `compute_aggregate_metrics` | `Dict[str, float]` | Contains `List[Dict]` and `int` values |
| `aggregate_failure_analysis` | `Dict[str, Any]` | Well-documented structure in docstring |
| `load_aggregate_metrics` | `dict` | `{f1, precision, recall, errors_by_type}` |

### Recommendation

Define dataclasses or Pydantic models for these results: `CVSensorResult`, `OrientationResult`, `PipelineResult`, `FieldMetrics`, `AggregateMetrics`, `FailureAnalysis`. This provides IDE autocompletion, catches key-name typos at development time, and serves as documentation.

---

## 6. Medium: Inconsistent Error Handling

The codebase uses three incompatible error strategies:

### Strategy 1: Return a default value on failure

`orchestrator.py` line 708–718 (`run_orientation_extraction`):
```python
except Exception as e:
    logger.warning(f"Orientation extraction failed: {e}, using default orientation")
    return {"front_orientation": 0.0, ...}
```

### Strategy 2: Raise a RuntimeError

`orchestrator.py` line 1084–1087 (`run_project_extraction`):
```python
except Exception as e:
    raise RuntimeError(f"Project extractor returned invalid response: {e}")
```

### Strategy 3: Return an error dict

`orchestrator.py` line 1814–1822 (`run_extraction`):
```python
except Exception as e:
    return {"eval_name": eval_name, "error": str(e), "building_spec": None, ...}
```

The caller must remember which strategy each function uses. There is no type-system enforcement.

### Additional error handling issues

- **Swallowed exceptions with no logging**: Cache load failures at lines 1651, 1674, 1684 catch `except Exception` with zero diagnostic output.
- **Over-broad catches**: `discover_source_pdfs` (line 81) catches `Exception` for PDF read failures, which would also catch `MemoryError`.
- **`sys.exit(1)` instead of Click exceptions**: `improvement/cli.py` uses bare `sys.exit(1)` in 11 places rather than `click.ClickException`, making functions untestable without catching `SystemExit`.
- **`metrics.py` can produce negative true_positives**: Line 38 computes `true_positives = total_fields_gt - omissions - wrong_values - format_errors` with no clamping guard.
- **Variable shadowing**: `verifier/cli.py` line 304 reassigns `extracted_json` from its original meaning (file path parameter) to a JSON string.

---

## 7. Medium: Schema Design Gaps

### 7a. Eight enums defined but never used as field types

`building_spec.py` defines `FuelType`, `HouseType`, `RunScope`, `ComponentStatus`, `ZoneType`, `HVACSystemType`, `WaterHeaterType`, and `WaterHeaterFuel`, but every corresponding model field uses `Optional[str]` instead:

```python
class FuelType(str, Enum):          # Defined at line 15
    ALL_ELECTRIC = "All Electric"

class ProjectInfo(BaseModel):
    fuel_type: Optional[str] = ...  # Uses str at line 88, not FuelType
```

This means no validation is performed on these values. Either use the enums or remove them.

### 7b. No cross-field validators

Neither schema file uses `@field_validator` or `@model_validator`. For example:
- `OrientationWall` has `gross_wall_area` and `net_wall_area` but no check that `net <= gross`
- `FenestrationEntry` has `height`, `width`, and `area` but no consistency check

### 7c. Inconsistent nullability semantics

`TakeoffProjectInfo.attached_garage` is `bool` with `default=False`, while `ProjectInfo.attached_garage` is `Optional[bool]` with `default=None`. The transform silently converts `False` (possibly meaning "unknown") into a concrete `False`.

`building_spec.py` uses `default=None` for most optional fields but `default=0.0` for some (`addition_conditioned_floor_area`, `underground_wall_area`). `None` means "not provided" in some fields and `0.0` means "not applicable" in others, without a documented convention.

### 7d. Hardcoded assumptions in transform

`transform.py` hardcodes `status="New"` (lines 157–158, 176) and `tilt=90.0` (line 94) during zone and wall transformation. The source schemas don't carry these fields, so the assumptions are baked in with no override mechanism.

---

## 8. Medium: Build Configuration Issues

### 8a. `improvement` package missing from wheel

`pyproject.toml` line 34 lists packages:
```toml
packages = ["src/verifier", "src/schemas", "src/preprocessor", "src/agents", "src/cv_sensors"]
```
`src/improvement` is missing. The `telemetry` module is also absent.

### 8b. No CLI entry point for improvement

Three entry points are defined (`verifier`, `preprocessor`, `extractor`) but `improver` is missing. Users must invoke it via `python3 -m improvement`, which only works with `sys.path` manipulation.

### 8c. Project name mismatch

The project is named `takeoff-verifier` in `pyproject.toml`, but the package includes the full extraction and improvement pipeline — not just the verifier. The name is misleading.

### 8d. Missing dev tool configuration

No `[tool.pytest.ini_options]` section, no linter configuration (`ruff`, `flake8`), no type checker configuration (`mypy`), no `pytest-asyncio` for async test support.

---

## 9. Low: Style Inconsistencies

### 9a. Import organization

Imports throughout the codebase do not follow PEP 8 grouping (stdlib → third-party → local). Third-party imports (`pydantic`, `numpy`) are interleaved with local imports. Several files have delayed imports inside function bodies (`import re` in `verifier/cli.py:43`, `import fitz` in `orchestrator.py:63`, `import shutil` in `improvement/cli.py:507`).

### 9b. Mixed typing syntax

Some files use `List[Path]` (typing module), others use `list[Path]` (Python 3.9+ builtins). `takeoff_spec.py` line 158 mixes both in one annotation: `List[tuple[str, OrientationWall]]`. The project requires Python 3.11+, so the modern lowercase syntax should be used consistently.

### 9c. Mixed output mechanisms

- `improvement/cli.py`: Uses `click.echo()` with broken Rich markup literals like `[green]...[/green]` that `click.echo` renders as literal text
- `improvement/review.py`: Uses `rich.console.Console` (correct for Rich markup)
- `improvement/cli.py` `context` command: Uses bare `print()`
- `agents/cli.py`: Uses `click.echo()` + `logging`

### 9d. Dataclass vs Pydantic inconsistency

`verifier/compare.py` uses `@dataclass` for `FieldDiscrepancy` and `FieldComparison`, then manually converts them to dicts in `cli.py`. The rest of the codebase uses Pydantic `BaseModel` with `.model_dump()`. Picking one approach and being consistent would reduce boilerplate.

### 9e. Inconsistent separator characters

`telemetry.py` uses Unicode box-drawing characters (`\u2500`) at width 52, `agents/cli.py` uses both `"=" * 60` and `"\u2500" * 60` in the same function, and `verifier/cli.py` uses `"=" * 60`.

---

## 10. Low: Magic Numbers and Hardcoded Values

The codebase contains dozens of undocumented magic numbers. A representative sample:

### Orchestrator timeouts and limits

| Location | Value | Purpose |
|---|---|---|
| `orchestrator.py:47` | `Semaphore(4)` | Max concurrent extractions (module-level global) |
| `orchestrator.py:50` | `20` | Max PDF pages per read |
| `orchestrator.py:358` | `300` | Sync agent timeout (seconds) |
| `orchestrator.py:404` | `600` | Async agent timeout (seconds) |
| `orchestrator.py:842` | `20` | Angular agreement threshold (degrees) |
| `orchestrator.py:863` | `70, 110` | Side/front confusion range |
| `orchestrator.py:873` | `160, 200` | Front/back confusion range |

### CV sensor thresholds

| Location | Value | Purpose |
|---|---|---|
| `north_arrow.py:48` | `0.25` | Corner margin ratio |
| `north_arrow.py:93` | `50` | Hough threshold |
| `north_arrow.py:108` | `30, 250` | Min/max arrow length |
| `north_arrow.py:278` | `20` | Angle agreement tolerance |
| `wall_detection.py:56` | `100` | Hough threshold |
| `wall_detection.py:66` | `50, 800` | Min/max wall length |

### Verifier/improvement constants

| Location | Value | Purpose |
|---|---|---|
| `verifier/cli.py:247` | `20` | Max discrepancies to display |
| `compare.py:196` | `0.5, 0.01` | Default tolerances (percent, absolute) |
| `critic.py:168` | `20` | Sample discrepancies limit |
| `critic.py:323` | `300` | Critic agent timeout |
| `review.py:155` | `0.001` | Delta significance threshold |

### Recommendation

Create a `constants.py` or `config.py` module with named constants grouped by domain. Alternatively, make them configurable via a YAML config file that the CLI loads.

---

## Architectural Recommendations (Prioritized)

### Phase 1: Foundation (highest impact)

1. **Split the orchestrator** into 5–6 focused modules as described in section 1
2. **Create a `tests/` directory** with pytest configuration and unit tests for pure functions
3. **Define typed result models** for the ~8 functions returning `Dict[str, Any]`
4. **Extract shared constants** (ground truth, error types, metric names, tolerance) into a single module

### Phase 2: Cleanup

5. **Delete redundant root scripts** (`run_extract.py`, `run_extract_all.py`, `run_extract_all.sh`, `improve_orientation.py`, `improve_orientation_fast.py`, `test_orientation.py`)
6. **Consolidate orientation testing** into a proper CLI command or pytest test
7. **Fix build configuration** — add `improvement` and `telemetry` to packages, add `improver` entry point
8. **Extract shared schema base** — create base `ProjectInfoBase` for shared fields, shared `enums.py`

### Phase 3: Polish

9. **Standardize error handling** — pick one strategy (Result types or exceptions) and apply consistently
10. **Standardize output** — use either Click styling or Rich, not both
11. **Use enums as field types** or remove the dead enum definitions
12. **Add cross-field validators** to Pydantic models
13. **Normalize import style** — PEP 8 grouping, consistent typing syntax

### Phase 4: Infrastructure

14. **Add linter and type checker** configuration (`ruff`, `mypy`)
15. **Introduce an agent invocation interface** — replace direct `subprocess.run(["claude", ...])` with a protocol to enable testing and alternative runtimes
16. **Extract caching into a reusable abstraction** — replace the 3x duplicated JSON file cache with a `JsonCache` class
17. **Complete the TakeoffSpec migration** — eliminate the legacy double-merge in `run_extraction`

---

## Positive Aspects Worth Preserving

- **Multi-agent architecture** is well-designed with clear separation of extraction domains
- **Dynamic instruction loading** (`.claude/instructions/`) allows prompt iteration without code changes
- **CV sensor integration** provides deterministic geometric measurements as a complement to LLM extraction
- **Evaluation infrastructure** with ground truth, field-level metrics, and iteration tracking is comprehensive
- **Self-improvement loop** (extract → evaluate → critique → improve → repeat) is architecturally sound
- **Pydantic schema design** for `TakeoffSpec` and `BuildingSpec` captures the domain well despite the gaps noted above
- **`telemetry.py`** is clean, focused, and well-implemented — a good example of single-responsibility design
