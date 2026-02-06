#!/bin/bash
# Parallel extraction with caching - runs 3 at a time
set -e

EVALS="chamberlin-circle canterbury-rd martinez-adu poonian-adu lamb-adu"
MAX_JOBS=${1:-3}

echo "Extracting all evals (max $MAX_JOBS parallel)..."
START=$(date +%s)

# Run in parallel with job control
for eval_id in $EVALS; do
    while [ $(jobs -rp | wc -l) -ge $MAX_JOBS ]; do
        sleep 2
    done
    echo "  Starting $eval_id..."
    python3 run_extract.py "$eval_id" &
done

# Wait for all
wait
END=$(date +%s)
echo ""
echo "Total wall-clock time: $((END - START))s"
