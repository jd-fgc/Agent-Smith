#!/bin/bash
# Benchmark automation script for BENCHMARK_REPORT.md
# Runs N models x 3 fixed tasks, dumps each task once, saves each solution.json
# with a name that identifies model + task for easy comparison afterwards.
#
# Usage: ./run_benchmark.sh
# Edit MODELS below to match what's actually available on OpenRouter today.

set -uo pipefail

PROVIDER_URL="https://openrouter.ai/api/v1"

# --- Edit this list after checking openrouter.ai/models for current free availability ---
MODELS=(
    "poolside/laguna-xs-2.1:free"
    "openai/gpt-oss-20b:free"
    "google/gemma-4-31b-it:free"
    "nvidia/nemotron-3-super-120b-a12b:free"
    "cohere/north-mini-code:free"
)

# Fixed task instance IDs (already validated to work with the agent loop)
TASKS=(
    "django__django-11066"
    "pydata__xarray-4629"
    "sympy__sympy-13480"
)

BENCH_DIR="benchmark_runs/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$BENCH_DIR"

echo "Benchmark output directory: $BENCH_DIR"
echo ""

for task_id in "${TASKS[@]}"; do
    echo "=== Dumping task: $task_id ==="
    TASK_FILE="$BENCH_DIR/${task_id}_task.json"
    (cd moulinette && uv run moulinette_eval dump swebench --output "../$TASK_FILE" --task-id "$task_id")

    if [ ! -f "$TASK_FILE" ]; then
        echo "WARNING: failed to dump $task_id, skipping"
        continue
    fi

    for model in "${MODELS[@]}"; do
        SAFE_MODEL=$(echo "$model" | tr '/:' '__')
        SOLUTION_FILE="$BENCH_DIR/${task_id}__${SAFE_MODEL}_solution.json"

        echo ""
        echo "--- Running model=$model task=$task_id ---"
        START=$(date +%s)

        uv run python -m student.agent_swebench \
            --task-file "$TASK_FILE" \
            --output "$SOLUTION_FILE" \
            --model-name "$model" \
            --provider-url "$PROVIDER_URL" \
            > "$BENCH_DIR/${task_id}__${SAFE_MODEL}_stdout.log" \
            2> "$BENCH_DIR/${task_id}__${SAFE_MODEL}_stderr.log"

        END=$(date +%s)
        DURATION=$((END - START))

        if [ -f "$SOLUTION_FILE" ]; then
            SUCCESS=$(python3 -c "import json; print(json.load(open('$SOLUTION_FILE'))['success'])" 2>/dev/null || echo "unknown")
            ITER=$(python3 -c "import json; print(json.load(open('$SOLUTION_FILE'))['iterations'])" 2>/dev/null || echo "?")
            echo "Result: success=$SUCCESS iterations=$ITER duration=${DURATION}s"
        else
            echo "Result: NO SOLUTION FILE PRODUCED (duration=${DURATION}s) — check stderr.log"
        fi
    done
done

echo ""
echo "=== Benchmark complete ==="
echo "All results saved under: $BENCH_DIR"
echo "Inspect with: cat $BENCH_DIR/<task>__<model>_solution.json | python3 -m json.tool"