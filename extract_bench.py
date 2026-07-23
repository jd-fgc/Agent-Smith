import json
import glob
import os

KNOWN_TASKS = ["django__django-11066", "pydata__xarray-4629", "sympy__sympy-13480"]

results = []

for filepath in sorted(glob.glob("benchmark_runs/*/*_solution.json")):
    filename = os.path.basename(filepath).replace("_solution.json", "")

    task_id = None
    model_part = None
    for t in KNOWN_TASKS:
        prefix = t + "__"
        if filename.startswith(prefix):
            task_id = t
            model_part = filename[len(prefix):]
            break

    if task_id is None:
        task_id = "UNKNOWN"
        model_part = filename

    try:
        with open(filepath) as f:
            data = json.load(f)
        success = data.get("success", False)
        iterations = data.get("iterations", "?")
        input_tokens = data.get("total_input_tokens", "?")
        output_tokens = data.get("total_output_tokens", "?")
        time_seconds = data.get("total_time_seconds", "?")
        solution_len = len(data.get("solution", "") or "")
        error = data.get("error")
    except Exception as e:
        success = f"ERROR: {e}"
        iterations = input_tokens = output_tokens = time_seconds = solution_len = "?"
        error = str(e)

    results.append({
        "task": task_id,
        "model": model_part,
        "success": success,
        "iterations": iterations,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "time_seconds": round(time_seconds, 1) if isinstance(time_seconds, (int, float)) else time_seconds,
        "patch_length": solution_len,
        "error": error,
    })

print("| Model | Task | Success | Iterations | Input Tokens | Output Tokens | Time (s) | Patch Length |")
print("|---|---|---|---|---|---|---|---|")
for r in results:
    print(f"| {r['model']} | {r['task']} | {r['success']} | {r['iterations']} | {r['input_tokens']} | {r['output_tokens']} | {r['time_seconds']} | {r['patch_length']} |")

print()
print("=== Errors encountered ===")
for r in results:
    if r["error"]:
        print(f"{r['model']} / {r['task']}: {r['error']}")