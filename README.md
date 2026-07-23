*This project has been created as part of the 42 curriculum by jogamber, nisalmon.*

# Agent Smith

An autonomous coding agent capable of reasoning, writing code, executing it in a sandboxed environment, and iterating until a solution is found. Agent Smith targets two benchmarks: **MBPP** (algorithmic Python problems) and **SWE-bench** (real-world bug fixing in production repositories).

---

## Description

Agent Smith implements an agentic framework built around a **Thought → Code → Observation** loop. The agent receives a coding task, queries a Large Language Model (LLM) to generate a tool call, runs that call in a secure sandbox (or, for SWE-bench, inside a Docker container), observes the result, and iterates until the task is solved or resource limits are reached.

The project introduces three core concepts:
- **Code Agents**: LLM-driven autonomous systems that write and execute code
- **Model Context Protocol (MCP)**: a standardized protocol for exposing tools to the agent
- **Controlled code execution**: a sandboxed Python environment with strict security constraints, and a Dockerized execution environment for SWE-bench

---

## System Architecture

### MBPP

```
LLM API (OpenRouter)
    ↓ generates Python code / tool call
Agent / Orchestrator
    ↓ extracts code block
Sandbox (secure execution)
    ↓ tool call via MCP client
MCP Server (tools)
    ↓ executes tool (read_file, run_tests, etc.)
    ↑ returns result
Sandbox
    ↑ returns observation
Agent / Orchestrator
    ↑ feeds observation back to LLM
```

### SWE-bench

Instead of routing through the MCP-connected sandbox, the SWE-bench agent talks directly to a `DockerSandbox` that wraps a running container for the target repository:

```
LLM API (OpenRouter)
    ↓ generates a tool call (JSON)
Agent loop (agent_swebench)
    ↓ parses tool call, tracks phase (explore / edit / patch)
DockerSandbox
    ↓ docker exec into the running container
Container (real repo, e.g. django/django)
    ↑ returns command output
Agent loop
    ↑ feeds observation back to LLM
    ↓ on finish_editing() → calls get_patch() automatically
    ↓ returns unified git diff as the solution
```

Each task pulls and starts its own Docker image (from the SWE-bench dataset), executes the full agent loop inside it, and tears the container down at the end (`sandbox.stop()` in a `finally` block) so no containers are left running.

**Project structure:**
```
student/
    agent_mbpp/
        loop_mbpp.py           # MBPP agent loop
        __main__.py             # MBPP CLI
    agent_swebench/
        loop_swebench.py        # SWE-bench agent loop (explore/edit/patch phases)
        __main__.py              # SWE-bench CLI
    agent_utils/
        utils.py                 # LLM client, key loading, tool descriptions
    code_parser/
        parser.py                # Multi-format tool-call extraction (JSON, XML, ReAct, code blocks)
    mcp/
        tools/
            execution_tools.py
            file_system_tools.py
            code_search_tools.py
    sandbox/
        sandbox.py                # Sandbox class + worker (MBPP / interactive REPL)
    models/
        MBPP_models.py            # Pydantic models for MBPP
        SWE_models.py              # Pydantic models for SWE-bench
        sandbox_config.py          # SandboxConfig
        DockerSandbox.py            # Docker-backed sandbox for SWE-bench
    __main__.py                    # sandbox CLI entry point
mcp/
    mcp_tools_mbpp.py               # MCP server for MBPP (run_tests)
mcp_tools_swebench.py                # MCP server for SWE-bench (all tools)
```

---

## Agent Loop Explanation

### MBPP

The agent operates through a structured loop:

1. **Thought**: the LLM receives the task description and tool documentation, and generates a reasoning step
2. **Code**: the LLM produces a tool call (JSON, XML, ReAct, or Python code block)
3. **Observation**: the sandbox executes the call and returns stdout/stderr
4. The observation is appended to the conversation history and the loop repeats

The agent supports multiple LLM output formats through a unified code extraction layer (`code_parser/parser.py`).

The loop terminates when the agent calls `final_answer()`, or when iteration/token/time limits are reached.

### SWE-bench

The SWE-bench loop is split into three phases, each exposing a different subset of tools to keep the LLM focused:

- **explore**: `read_file`, `list_files`, `search_code`, `search_function_or_class_definition_in_code`, `run_command`, `finish_exploration`
- **edit**: same tools plus `edit_file`, `run_tests`, `finish_editing`
- **patch**: same as edit plus `get_patch`

The LLM is expected to call `finish_exploration()` once it has located the bug, and `finish_editing()` once the fix is applied. If the LLM stays in the explore phase for more than 10 iterations without progressing, the phase is force-advanced to `edit`. When `finish_editing()` is called, the agent automatically invokes `get_patch()` and returns the resulting git diff as the solution — the LLM does not need to explicitly call the patch tool itself.

API keys are rotated automatically on `RateLimitError`, cycling through up to 5 keys loaded from environment variables.

---

## Sandbox Design

The sandbox is a secure Python execution environment implemented using standard library only (no RestrictedPython).

**Security constraints:**
- **Import restrictions**: only modules from `authorized_imports` allowlist may be imported, enforced via a custom `safe_import()` replacing `__builtins__["__import__"]`
- **Filesystem restrictions**: file access is limited to `allowed_directories`, enforced via a custom `safe_open()` that resolves absolute paths and checks against the allowlist
- **Network blocking**: `socket.socket` is replaced with a function that raises `PermissionError`
- **Execution timeout**: code runs in a separate process via `multiprocessing.Process`; if it exceeds `max_execution_time_seconds`, the process is terminated
- **Memory limit**: `resource.setrlimit(RLIMIT_AS)` limits RAM usage inside the worker process

**Execution flow:**
```
sandbox.execute(code)
    → spawn worker process
    → worker sets memory limit + blocks network
    → worker runs exec(code, namespace), output captured to a temp file (flushed live, so partial output survives a timeout kill)
    → parent reads the temp file after the process exits or is terminated
    → returns TIMEOUT / MEMORY LIMIT EXCEEDED / success with output
```

The sandbox also provides an **interactive REPL mode** (`uv run sandbox`) where variables persist between executions using a shared namespace, and a **pipe mode** (`cat script.py | uv run sandbox config.json`) that reads and executes an entire script at once, correctly handling multi-line blocks via `codeop.compile_command`.

**MCP integration**: the sandbox connects to an MCP server (via stdio or HTTP) and dynamically discovers available tools, injecting them as callable Python functions into the execution namespace.

**SWE-bench Docker sandbox**: for SWE-bench, `DockerSandbox` (in `student/models/DockerSandbox.py`) starts a container from the task's Docker image (`network_mode="none"`) and executes each tool call via `container.exec_run()`, parsing the LLM's tool-call string into the corresponding shell command (`grep`, `sed`, `find`, `git diff`, etc.) run inside the container's `/testbed` working directory.

---

## Tool Implementation Details

Tools are exposed via two MCP servers (used for MBPP and the interactive sandbox):

### `mcp_tools_mbpp.py`
- `run_tests(solution_code, test_list, test_imports)`: builds a Python script combining the solution and test assertions, returns it as a JSON result

### `mcp_tools_swebench.py`

**File System Tools:**
- `read_file(filepath, start_line, end_line)`: reads a file with line numbers (cat -n format)
- `edit_file(filepath, old_str, new_str)`: replaces an exact string in a file
- `list_files(directory, pattern)`: lists files matching a glob pattern

**Code Search Tools:**
- `search_code(pattern, file_pattern)`: grep-like search in the codebase
- `search_function_or_class_definition_in_code(name)`: finds function/class definitions
- `find_references(name, filepath, line)`: finds all usages of a symbol

**Execution Tools:**
- `run_tests()`: executes the evaluation script
- `get_patch()`: retrieves the unified git diff
- `run_command(command, workdir)`: executes a shell command, returns stdout/stderr/exitcode

Both servers support **stdio** (default) and **streamable HTTP** transports. All filesystem-facing tools map the client-visible `/testbed` path to the real `TESTBED_PATH` environment variable, so the same tool interface works whether pointed at a local checkout or a container mount.

For SWE-bench, the equivalent tools (`tool_read_file`, `run_command`, `tool_get_patch`, etc.) are re-implemented in `DockerSandbox` to run inside the task's Docker container via `docker exec`, rather than via MCP.

---

## Instructions

### Requirements
- Python 3.10
- uv (package manager)
- Docker (for SWE-bench)

### Installation
```bash
git clone <repo>
cd Agent-Smith
uv sync
```

### Running the sandbox REPL
```bash
# Interactive sandbox (no MCP)
uv run sandbox

# With config file
uv run sandbox sandbox_template.json

# With MBPP MCP tools (stdio)
uv run sandbox --mcp-stdio "python mcp/mcp_tools_mbpp.py" sandbox_template.json

# With MCP tools (HTTP)
uv run sandbox --mcp-server http://127.0.0.1:8000/mcp

# Pipe mode (runs a whole script non-interactively)
cat script.py | uv run sandbox sandbox_template.json
```

### Running the MBPP agent
```bash
cd moulinette
uv run moulinette_eval dump mbpp --output ../cache/MBPP.json

cd ../student
uv run python -m agent_mbpp run_agent \
    --task_file ../cache/MBPP.json \
    --output ../cache/MBPP_Solution.json \
    --model_name "poolside/laguna-xs-2.1:free" \
    --provider_url "https://openrouter.ai/api/v1" \
    --max_iteration 10

cd ../moulinette
uv run moulinette_eval validate mbpp ../cache/MBPP.json ../cache/MBPP_Solution.json
```

### Running the SWE-bench agent
```bash
cd moulinette
uv run moulinette_eval dump swebench --output ../cache/SWE.json

cd ..
uv run python -m student.agent_swebench \
    --task-file cache/SWE.json \
    --output cache/SWE_solution.json \
    --model-name "poolside/laguna-xs-2.1:free" \
    --provider-url "https://openrouter.ai/api/v1"

cd moulinette
uv run moulinette_eval validate swebench ../cache/SWE.json ../cache/SWE_solution.json
```

### Running the exam scripts
```bash
./exams/exam_sandbox.sh --student-path student --moulinette-path moulinette --env-file .env
./exams/exam_mbpp.sh --student-path student --moulinette-path moulinette --env-file .env
./exams/exam_swebench.sh --student-path student --moulinette-path moulinette --env-file .env \
    --model-name "poolside/laguna-xs-2.1:free" --provider-url "https://openrouter.ai/api/v1"
./exams/exam_anticheat.sh --student-path student
```

### Environment variables
API keys must be loaded from a `.env` file at the project root:
```
OPENAI_API_KEY_1=sk-or-...
OPENAI_API_KEY_2=sk-or-...
OPENAI_API_KEY_3=sk-or-...
OPENAI_API_KEY_4=sk-or-...
OPENAI_API_KEY_5=sk-or-...
```
Multiple keys let the agent rotate to a fresh key when one hits a rate limit. Note: OpenRouter free-tier models are capped at 50 requests/day per account by default; a small credit top-up on the OpenRouter account raises this to 1000/day.

---

## Benchmark Results and Analysis

Sandbox exam (`exam_sandbox.sh`): **14/14 tests passing**, including import/filesystem/network restrictions, timeout and memory enforcement, MCP stdio and HTTP transport, dynamic tool discovery, and sandbox manual generation.

SWE-bench end-to-end run (3 randomly selected tasks, `poolside/laguna-xs-2.1:free`): all 3 agent runs completed successfully and produced a git patch (agent durations: 222s, 890s, 313s — all well within the 900s limit). For `django__django-11066`, the agent's patch was functionally identical to the accepted upstream fix.

Full 5-model × 3-task comparison is documented in `BENCHMARK_REPORT.md`.

---

## Resources

- [Model Context Protocol documentation](https://modelcontextprotocol.io/docs)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [SWE-bench](https://www.swebench.com/)
- [MBPP dataset](https://huggingface.co/datasets/google-research-datasets/mbpp)
- [OpenRouter](https://openrouter.ai)
- [SWE agent](https://swe-agent.com/latest/)
- [Creer un Serveur MCP avec FastMCP](https://blog.stephane-robert.info/docs/developper/programmation/python/mcp-serveur/)
- [Assertion guide](https://www.pythoniste.fr/python/linstruction-dassertion-en-python-assert/)
- [What is a Python MCP Client](https://modelcontextprotocol.io/docs/getting-started/intro)
- [Testing a MCP server](https://realpython.com/videos/testing-mcp-servers-mcp-client-overview/)
- [AI Coding agents Guide](https://realpython.com/ai-coding-agents-guide/)

### AI usage
Claude (Anthropic) was used as a coding assistant throughout this project:
- Debugging async/await patterns with the MCP client
- Debugging the agent loop, code parser, and rate-limit handling
