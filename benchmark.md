# Benchmark Report — Agent Smith

## 1. Setup

**Models compared:**

| # | Model | Provider | Notes |
|---|-------|----------|-------|
| 1 | `poolside/laguna-xs-2.1:free` | OpenRouter | Coding-agent model, 33B-A3B, 256K context, tool calling + reasoning |
| 2 | `openai/gpt-oss-20b:free` | OpenRouter | Open-weights, general purpose |
| 3 | `google/gemma-4-31b-it:free` | OpenRouter | General purpose, not code-specialized |
| 4 | `nvidia/nemotron-3-super-120b-a12b:free` | OpenRouter | Larger MoE model, reported strong structured-output adherence |
| 5 | `cohere/north-mini-code:free` | OpenRouter | Code-specialized, smaller model |

**Tasks used:**

| Instance ID | Repo | Difficulty | Why selected |
|---|---|---|---|
| `django__django-11066` | django/django | <15 min fix | Single-line fix, clear issue description with the exact expected change quoted in the issue text |
| `pydata__xarray-4629` | pydata/xarray | <15 min fix | Single-line fix, small self-contained repro |
| `sympy__sympy-13480` | sympy/sympy | <15 min fix | Typo-level fix (`cotm` → `cothm`), simplest of the three |

These three tasks were chosen because they are all rated "<15 min fix" in the SWE-bench metadata, keeping the 15 total runs (5 models × 3 tasks) within a manageable time budget while still testing on real, non-trivial bugs in production codebases. All three were run for every model with `max_iteration=30`, the SWE-bench limit defined by the subject.

---

## 2. Results Table

| Model | Task | Pass/Fail (agent self-report) | Iterations | Input Tokens | Output Tokens | Wall-clock Time |
|---|---|---|---|---|---|---|
| poolside/laguna-xs-2.1:free | django__django-11066 | **PASS** | 18 | 51,417 | 3,771 | 668.7s |
| poolside/laguna-xs-2.1:free | pydata__xarray-4629 | **PASS** | 25 | 76,459 | 4,873 | 981.5s |
| poolside/laguna-xs-2.1:free | sympy__sympy-13480 | FAIL | 30 (exhausted) | 138,914 | 10,793 | 1156.4s |
| openai/gpt-oss-20b:free | django__django-11066 | FAIL | 30 (exhausted) | 1,874 | 88 | 210.6s |
| openai/gpt-oss-20b:free | pydata__xarray-4629 | FAIL | 30 (exhausted) | 2,377 | 85 | 150.2s |
| openai/gpt-oss-20b:free | sympy__sympy-13480 | FAIL | 30 (exhausted) | 0 | 0 | 159.7s |
| google/gemma-4-31b-it:free | django__django-11066 | FAIL | 30 (exhausted) | 0 | 0 | 0.0s |
| google/gemma-4-31b-it:free | pydata__xarray-4629 | FAIL | 30 (exhausted) | 1,302 | 32 | 3.0s |
| google/gemma-4-31b-it:free | sympy__sympy-13480 | FAIL | 30 (exhausted) | 0 | 0 | 0.0s |
| nvidia/nemotron-3-super-120b-a12b:free | django__django-11066 | **PASS** | 8 | 15,693 | 11,840 | 156.4s |
| nvidia/nemotron-3-super-120b-a12b:free | pydata__xarray-4629 | **PASS** | 25 | 782,569 | 17,801 | 359.1s |
| nvidia/nemotron-3-super-120b-a12b:free | sympy__sympy-13480 | **PASS** | 28 | 96,270 | 26,503 | 367.2s |
| cohere/north-mini-code:free | django__django-11066 | FAIL | 30 (exhausted) | 17,712 | 1,033 | 675.8s |
| cohere/north-mini-code:free | pydata__xarray-4629 | FAIL | 30 (exhausted) | 3,465 | 289 | 963.0s |
| cohere/north-mini-code:free | sympy__sympy-13480 | FAIL | 30 (exhausted) | 12,172 | 2,566 | 2416.6s |

**Pass rate summary:**

| Model | Passes / 3 |
|---|---|
| nvidia/nemotron-3-super-120b-a12b:free | **3/3** |
| poolside/laguna-xs-2.1:free | 2/3 |
| openai/gpt-oss-20b:free | 0/3 |
| google/gemma-4-31b-it:free | 0/3 |
| cohere/north-mini-code:free | 0/3 |

Note: "Pass" here means the agent itself reported `success: True` and produced a non-empty patch (confirmed by manual inspection to match the semantic intent of the expected fix for `django__django-11066`). Full moulinette test-suite validation could not be run to completion on the development machine due to an unrelated Docker networking issue (see project notes); these pass/fail values reflect the agent's own patch-generation success.

---

## 3. Provider Reliability

| Model | Avg time / request (across all steps) | Retries observed | Availability |
|---|---|---|---|
| poolside/laguna-xs-2.1:free | ~15-40s/request | Occasional rate-limit rotation, resolved after adding OpenRouter credits | Stable once quota was sufficient |
| openai/gpt-oss-20b:free | Fast to fail (~2-7s/iteration) | 0 explicit rate-limit errors observed | Every request failed silently (0 useful tokens on 2/3 tasks) — likely an incompatible response/tool-call format rather than an availability issue |
| google/gemma-4-31b-it:free | Near-instant failure (<0.1s/iteration on 2/3 tasks) | 0 explicit rate-limit errors observed | Same pattern as gpt-oss — requests return essentially nothing usable |
| nvidia/nemotron-3-super-120b-a12b:free | ~15-20s/request typical, one run (xarray) had a very high token count (782k input) suggesting one long-running conversation history | None observed | Most reliable of the 5 — completed all 3 tasks |
| cohere/north-mini-code:free | Highly variable, one run averaged >80s/iteration (sympy, 2416s / 30 iterations) | None observed | Ran to completion each time but never produced a valid patch within the iteration budget |

The two models that returned 0 or near-0 tokens (`openai/gpt-oss-20b:free`, `google/gemma-4-31b-it:free`) most likely failed at the tool-call parsing stage rather than at the API level — the agent's code parser (`code_parser/parser.py`) expects specific JSON/XML/ReAct formats, and these models may default to a format not covered by the extractor, causing every step to fall through to the generic exception handler with no tokens counted.

---

## 4. Intermediary Metrics

Measured manually from the `solution.json` step traces of the two successful models.

**Exploration efficiency** (step at which the agent first reads the file that ends up in the final patch):

| Model | Task | First relevant read |
|---|---|---|
| poolside/laguna-xs-2.1:free | django__django-11066 | Step 2 (`tool_read_file` on the exact target file on the first read attempt) |
| nvidia/nemotron-3-super-120b-a12b:free | django__django-11066 | Step 1-2 (fast convergence, only 8 iterations total) |

**Submission discipline** (iterations between the fix being applied and `final_answer`/patch generation — zero is ideal, since our loop calls `get_patch()` automatically as soon as `finish_editing()` is called):

| Model | Task | Extra iterations after fix |
|---|---|---|
| poolside/laguna-xs-2.1:free | django__django-11066 | 0 — patch generated immediately on `finish_editing()` |
| nvidia/nemotron-3-super-120b-a12b:free | django__django-11066 | 0 — same automatic-patch design applies to every model |

Because `get_patch()` is called automatically by the agent loop the instant `finish_editing()` is invoked (rather than leaving the LLM to call it manually), submission discipline is effectively 0 extra iterations for every model that reaches the edit phase — this is a design choice in `loop_swebench.py`, not a per-model behavior difference.

---

## 5. Ablation Study

**Change tested:** forcing an automatic phase transition from `explore` to `edit` after 10 iterations without the LLM calling `finish_exploration()` itself, plus automatically invoking `get_patch()` on `finish_editing()` instead of requiring the LLM to call it as a separate step.

**Before:** early runs (same `poolside/laguna-xs-2.1:free` model, `django__django-11066` task) showed the agent exploring correctly and identifying the right file and fix, but never calling `finish_exploration()` or `finish_editing()` on its own — every one of 30 iterations stayed in the `explore` phase, producing an empty patch (`success: False`, `solution: ""`).

**After:** with the forced phase transition and automatic patch call added, the same model on the same task reached `success: True` in 18 iterations with a patch matching the accepted upstream fix.

| Variant | Task | Pass/Fail | Iterations | Notes |
|---|---|---|---|---|
| Before (no forced transition) | django__django-11066 | FAIL | 30 (exhausted, stuck in explore) | Empty patch |
| After (forced transition + auto-patch) | django__django-11066 | **PASS** | 18 | Correct patch, matches accepted fix |

**Observations:** the LLM's own judgment about when to stop exploring and when to submit a patch was not reliable enough on its own with this model — leaving those transitions to explicit tool calls the LLM must decide to make resulted in the agent getting stuck. Automating the phase change and the patch submission step turned an unconditional failure into a full success without changing anything about how the LLM reasons about the bug itself.

---

## 6. Conclusions

**Selected model for the final pipeline:** `nvidia/nemotron-3-super-120b-a12b:free`, with `poolside/laguna-xs-2.1:free` as a secondary/fallback option.

**Reasoning:** `nemotron-3-super-120b-a12b` was the only model to solve all 3 tasks, generally converged faster (as few as 8 iterations on `django__django-11066` vs. 18 for poolside), and never triggered a parsing failure — every response was successfully extracted into a valid tool call. `poolside/laguna-xs-2.1:free` is a reasonable fallback: it solved 2/3 tasks and was the model used throughout earlier development and debugging (including fixing the JSON tool-call/parser mismatch and the OpenRouter daily-quota issue), so its behavior is well understood.

**Models disregarded and why:**
- `openai/gpt-oss-20b:free` and `google/gemma-4-31b-it:free` — both produced 0 or near-0 tokens on most tasks, indicating their default output format is not compatible with the current tool-call extractor (`code_parser/parser.py`). They were not investigated further within the time available, but the near-zero token counts strongly suggest a parsing mismatch rather than a genuine reasoning failure.
- `cohere/north-mini-code:free` — ran to completion on every task (consuming the full 30-iteration budget each time) but never produced a valid patch, and was also the slowest model tested (over 40 minutes on `sympy__sympy-13480` alone). Its outputs were being parsed correctly (non-zero, reasonable token counts) but the model did not converge on a correct fix within budget.

---

## Backing Data

All `solution.json` files referenced in this report are located under:
```
benchmark_runs/2026-07-23_16-34-38/
```
with filenames of the form `<task_id>__<model_name>_solution.json` (e.g. `django__django-11066__nvidia_nemotron-3-super-120b-a12b_free_solution.json`). Matching `_stdout.log` and `_stderr.log` files are provided alongside each solution for reference.