#!/usr/bin/env python3
"""Parallel extraction across all evals with caching."""
import json
import sys
import time
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.orchestrator import run_extraction

EVALS = ["chamberlin-circle", "canterbury-rd", "martinez-adu", "poonian-adu", "lamb-adu"]


def extract_one(eval_id: str) -> dict:
    """Extract a single eval, return result summary."""
    eval_dir = Path(f"evals/{eval_id}")
    t0 = time.monotonic()
    try:
        result = run_extraction(eval_id, eval_dir)
        elapsed = time.monotonic() - t0

        if result.get("error"):
            return {"id": eval_id, "status": "failed", "error": result["error"], "elapsed": elapsed}

        spec = result["building_spec"]
        out = eval_dir / "extracted.json"
        with open(out, "w") as f:
            json.dump(spec, f, indent=2)

        timing = result.get("timing", {})
        return {
            "id": eval_id,
            "status": "success",
            "elapsed": elapsed,
            "timing": timing,
            "zones": len(spec.get("zones", [])),
            "walls": len(spec.get("walls", [])),
            "windows": len(spec.get("windows", [])),
        }
    except Exception as e:
        elapsed = time.monotonic() - t0
        return {"id": eval_id, "status": "error", "error": str(e), "elapsed": elapsed}


def main():
    max_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    evals = sys.argv[2:] if len(sys.argv) > 2 else EVALS

    print(f"Extracting {len(evals)} evals with {max_workers} workers...", flush=True)
    t_start = time.monotonic()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_one, eid): eid for eid in evals}
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r["status"] == "success":
                print(f"  [{r['id']}] SUCCESS ({r['elapsed']:.0f}s) - Z:{r['zones']} W:{r['walls']} Win:{r['windows']}", flush=True)
            else:
                print(f"  [{r['id']}] {r['status'].upper()}: {r.get('error', '?')} ({r['elapsed']:.0f}s)", flush=True)

    total = time.monotonic() - t_start
    print(f"\nTotal wall-clock time: {total:.0f}s ({total/60:.1f} min)")


if __name__ == "__main__":
    main()
