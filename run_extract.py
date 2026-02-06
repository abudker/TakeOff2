#!/usr/bin/env python3
"""Quick single-eval extraction script for parallel runs."""
import json
import sys
from pathlib import Path

# Must run from project root (src/ in sys.path)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.orchestrator import run_extraction

def main():
    eval_id = sys.argv[1]
    eval_dir = Path(f"evals/{eval_id}")

    print(f"Starting {eval_id}...", flush=True)
    result = run_extraction(eval_id, eval_dir)

    if result.get("error"):
        print(f"FAILED: {result['error']}")
        sys.exit(1)

    spec = result["building_spec"]
    out = eval_dir / "extracted.json"
    with open(out, "w") as f:
        json.dump(spec, f, indent=2)

    timing = result.get("timing", {})
    total = timing.get("total", "?")
    zones = len(spec.get("zones", []))
    walls = len(spec.get("walls", []))
    windows = len(spec.get("windows", []))
    print(f"SUCCESS ({total}s) - Zones: {zones}, Walls: {walls}, Windows: {windows}")
    print(f"Timing: {json.dumps(timing)}")

if __name__ == "__main__":
    main()
