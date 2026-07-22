from argparse import ArgumentParser
from typing import List
from mcp.server.fastmcp import FastMCP
from tools.execution_tools import run_tests as ex_run_tests
from asyncio import CancelledError
import json

"""MCP server for MBPP benchmark.

Exposes a single tool: run_tests, which builds and returns a Python
test script combining solution code and assertions.

Launch modes:
    uv run python mcp_tools_mbpp.py          # stdio (default)
    uv run python mcp_tools_mbpp.py --http   # streamable HTTP on port 8000
"""

mcp = FastMCP("agent-smith")


@mcp.tool()
def run_tests(solution_code: str = "", test_list: List[str] = [],
              test_imports: List[str] = [], code: str = "") -> str:
    """Build a Python test script and return it as a JSON result.

    Accepts either solution_code or code (alias) as the function source.
    Wraps each assertion in a try/except block to report PASS/FAIL per test.

    Args:
        solution_code: Python function source code.
        test_list: List of assert statements to run.
        test_imports: List of module names to import before running tests.
        code: Alias for solution_code (used when LLM passes 'code' key).

    Returns:
        JSON string with keys 'success' (bool) and 'output' (str or None).
    """
    actual_code = solution_code or code
    result = ex_run_tests(actual_code, test_list, test_imports)
    return json.dumps({"success": True, "output": result})


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--http", action="store_true")
    args = parser.parse_args()

    try:
        if args.http:
            mcp.run(transport="streamable-http")
        else:
            mcp.run()
    except (KeyboardInterrupt, CancelledError):
        print("\nServer stopped.")
    except Exception as e:
        print(f"Server error: {e}")
