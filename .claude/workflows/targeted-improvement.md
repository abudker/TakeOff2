# Targeted Improvement Workflow

This document describes how to run focused improvement loops on specific extractors (e.g., orientation-extractor) to rapidly iterate on instruction quality.

## Overview

The standard improvement pipeline (`python3 -m improvement improve`) runs the full extraction and verification cycle, which takes 15-20 minutes per iteration. For focused work on a single extractor, we use a lightweight pipeline that:

1. Caches discovery results (run once, reuse forever)
2. Runs only the target extractor
3. Tests in parallel across evaluations
4. Reduces iteration time to ~3-4 minutes

## Prerequisites

Ensure preprocessed images exist for all evaluations:
```bash
ls evals/*/preprocessed/*/page-*.png
```

## Scripts

### `test_orientation_fast.py`

Fast orientation testing with caching and parallelism.

```bash
# Test only failing evals (fastest iteration)
python3 test_orientation_fast.py

# Test all 5 evals
python3 test_orientation_fast.py --all

# Clear discovery cache and re-run
python3 test_orientation_fast.py --clear-cache

# Test specific evals
python3 test_orientation_fast.py --evals lamb-adu martinez-adu
```

Output: `orientation_test_results.json`

### `improve_orientation_fast.py`

Automated improvement loop with critic agent.

```bash
# Run single iteration (test → critique → apply)
python3 improve_orientation_fast.py --single

# Run up to N iterations
python3 improve_orientation_fast.py --max-iterations 10

# Test all evals (not just failing ones)
python3 improve_orientation_fast.py --test-all
```

Output: `orientation_improvement_log.json`

## Manual Improvement Workflow

When automated improvements plateau, switch to manual analysis:

### Step 1: Run Fast Test

```bash
python3 test_orientation_fast.py --all
```

Review results to identify failing cases.

### Step 2: Analyze Failing Cases

For each failing eval, examine the site plan images:

```bash
# Find the site plan page (usually page 3-4)
cat evals/.cache/{eval_id}_discovery.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('Drawing pages:', d['drawing_pages'])"
```

Then read the site plan image in Claude:
- Look for north arrow location and direction
- Identify the building front (street-facing for homes, entry-facing for ADUs)
- Calculate expected orientation manually

### Step 3: Update Instructions

Edit the extractor instructions based on findings:

```bash
# Instructions location
.claude/instructions/{extractor-name}/instructions.md
```

Key sections to modify:
- Add worked examples for failing cases
- Add rules for edge cases (e.g., ADUs)
- Clarify ambiguous guidance

### Step 4: Re-test

```bash
python3 test_orientation_fast.py --all
```

Compare before/after accuracy.

### Step 5: Commit if Improved

```bash
git add .claude/instructions/orientation-extractor/instructions.md
git commit -m "feat(instructions): improve orientation-extractor accuracy

- Added ADU-specific guidance
- Added worked examples for difficult cases
- Accuracy: X/5 → Y/5"
```

## Troubleshooting

### High Run-to-Run Variability

If the same instructions produce wildly different results across runs:
- The issue is visual interpretation, not instruction clarity
- Try adding more explicit angle measurement guidance
- Consider few-shot examples with annotated images

### Instructions Getting Bloated

After many automated iterations, instructions accumulate cruft:
- Check version number in instructions header
- If > 20 iterations since last cleanup, consider manual rewrite
- Keep instructions focused and < 300 lines

### Discovery Cache Issues

If page classifications seem wrong:
```bash
rm -rf evals/.cache/
python3 test_orientation_fast.py --all
```

## Extending to Other Extractors

To create a fast test for another extractor (e.g., windows):

1. Copy `test_orientation_fast.py` as template
2. Replace `run_orientation_async()` with call to target extractor
3. Update ground truth values and comparison logic
4. Update the async extraction prompt

Key functions to reuse:
- `get_cached_discovery()` / `save_discovery_cache()`
- `run_parallel_*_test()` pattern
- `angular_distance()` for circular metrics

## Session Handoff Template

When starting a new context window, provide this context:

```
I'm working on improving the {extractor-name} extractor.

Current status:
- Accuracy: X/Y correct
- Failing cases: {list}
- Instructions version: vX.Y.Z

Previous findings:
- {key insight 1}
- {key insight 2}

To continue:
1. Run: python3 test_{extractor}_fast.py --all
2. Analyze failing cases
3. Update instructions at .claude/instructions/{extractor-name}/instructions.md
4. Re-test

See .claude/workflows/targeted-improvement.md for full workflow.
```
