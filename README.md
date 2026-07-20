*This project has been created as part of the 42 curriculum by jogamber, nisalmon.*

# Agent Smith

An autonomous coding agent capable of reasoning, writing code, executing it in a sandboxed environment, and iterating until a solution is found. Agent Smith targets two benchmarks: **MBPP** (algorithmic Python problems) and **SWE-bench** (real-world bug fixing in production repositories).

---

## Description

Agent Smith implements an agentic framework built around a **Thought → Code → Observation** loop. The agent receives a coding task, queries a Large Language Model (LLM) to generate executable Python code, runs that code in a secure sandbox, observes the result, and iterates until the task is solved or resource limits are reached.

The project introduces three core concepts:
- **Code Agents**: LLM-driven autonomous systems that write and execute code
- **Model Context Protocol (MCP)**: a standardized protocol for exposing tools to the agent
- **Controlled code execution**: a sandboxed Python environment with strict security constraints

---

## System Architecture

```
LLM API (OpenRouter)
    ↓ generates Python code
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

**Project structure:**
```
student/
    agent/
        agent_mbpp.py         # MBPP agent loop + CLI
        agent_swebench.py     # SWE-bench agent loop + CLI
        agent_utils/
            utils.py          # LLM client, code parser, key management
    mcp/
        mcp_tools_mbpp.py     # MCP server for MBPP (run_tests)
        mcp_tools_swebench.py # MCP server for SWE-bench (all tools)
        tools/
            execution_tools.py
            file_system_tools.py
            code_search_tools.py
    sandbox/
        sandbox.py            # Sandbox class + worker
    models/
        mbpp_models.py        # Pydantic models for MBPP
        swe_models.py         # Pydantic models for SWE-bench
        sandbox_config.py     # SandboxConfig
    __main__.py               # sandbox CLI entry point
```

---

## Agent Loop Explanation

The agent operates through a structured loop:

1. **Thought**: the LLM receives the task description and tool documentation, and generates a reasoning step
2. **Code**: the LLM produces executable Python code (or a tool call in various formats)
3. **Observation**: the sandbox executes the code and returns stdout/stderr
4. The observation is appended to the conversation history and the loop repeats

The agent supports multiple LLM output formats (Python code blocks, XML tool calls, JSON/Hermes tool calls, ReAct format) through a unified code extraction layer.

The loop terminates when:
- The agent calls `final_answer()` 
- Maximum iterations are reached
- Token or time limits are exceeded

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
    → worker runs exec(code, namespace)
    → stdout captured via io.StringIO
    → result sent back via multiprocessing.Queue
    → parent reads result or returns TIMEOUT/MEMORY LIMIT EXCEEDED
```

The sandbox also provides an **interactive REPL mode** (`uv run sandbox`) where variables persist between executions using a shared namespace.

**MCP integration**: the sandbox connects to an MCP server (via stdio or HTTP) and dynamically discovers available tools, injecting them as callable Python functions into the execution namespace.

---

## Tool Implementation Details

Tools are exposed via two MCP servers:

### `mcp_tools_mbpp.py`
- `run_tests(solution_code, test_list, test_imports)`: builds a Python script combining the solution and test assertions, returns it for sandbox execution

### `mcp_tools_swebench.py`

**File System Tools:**
- `read_file(filepath, start_line, end_line)`: reads a file with line numbers (cat -n format)
- `edit_file(filepath, old_str, new_str)`: replaces an exact string in a file
- `list_files(directory, pattern)`: lists files matching a pattern

**Code Search Tools:**
- `search_code(pattern, file_pattern)`: grep-like search in the codebase
- `search_function_or_class_definition_in_code(name)`: finds function/class definitions
- `find_references(name, filepath, line)`: finds all usages of a symbol

**Execution Tools:**
- `run_tests()`: executes the evaluation script
- `get_patch()`: retrieves the unified git diff
- `run_command(command, workdir)`: executes a shell command, returns stdout/stderr/exitcode

Both servers support **stdio** (default) and **streamable HTTP** transports.

---

## Instructions

### Requirements
- Python 3.10
- uv (package manager)
- Docker (for SWE-bench)

### Installation
```bash
git clone <repo>
cd Agent_Smith
uv sync
```

### Running the sandbox REPL
```bash
# Interactive sandbox (no MCP)
uv run sandbox

# With config file
uv run sandbox sandbox_template.json

# With MBPP MCP tools (stdio)
uv run sandbox --mcp-stdio "python student/mcp/mcp_tools_mbpp.py" sandbox_template.json

# With MCP tools (HTTP)
uv run sandbox --mcp-server http://127.0.0.1:8000/mcp
```

### Running the MBPP agent
```bash
cd moulinette
uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json

cd ..
uv run python -m student.agent.agent_mbpp \
    --task-file cache/mbpp_task.json \
    --output cache/mbpp_solution.json \
    --model-name "poolside/laguna-xs-2.1:free" \
    --provider-url "https://openrouter.ai/api/v1"

cd moulinette
uv run moulinette_eval validate mbpp ../cache/mbpp_task.json ../cache/mbpp_solution.json
```

### Running the SWE-bench agent
```bash
cd moulinette
uv run moulinette_eval dump swebench --output ../cache/swebench_task.json

cd ..
uv run python -m student.agent.agent_swebench \
    --task-file cache/swebench_task.json \
    --output cache/swebench_solution.json \
    --model-name "poolside/laguna-xs-2.1:free" \
    --provider-url "https://openrouter.ai/api/v1"
```

### Environment variables
API keys must be loaded from a `.env` file:
```
OPENROUTER_API_KEY_1=sk-or-...
OPENROUTER_API_KEY_2=sk-or-...
```

---

## Benchmark Results and Analysis

> ⚠️ This section will be completed after running the full benchmark suite. See `BENCHMARK_REPORT.md` for detailed results.

---

## Resources

- [Model Context Protocol documentation](https://modelcontextprotocol.io/docs)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [SWE-bench](https://www.swebench.com/)
- [MBPP dataset](https://huggingface.co/datasets/google-research-datasets/mbpp)
- [OpenRouter](https://openrouter.ai)

### AI usage
Claude (Anthropic) was used as a coding assistant throughout this project:
- Designing the sandbox architecture and security mechanisms
- Implementing the MCP server and client connection logic
- Debugging async/await patterns with the MCP client
- Writing and reviewing type annotations
- Generating this README structure

All technical decisions, architecture choices, and final implementations were reviewed, understood, and validated by the team.