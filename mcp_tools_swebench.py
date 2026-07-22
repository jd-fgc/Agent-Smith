from typing import List
from argparse import ArgumentParser
from asyncio import CancelledError
import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp"))

from mcp.server.fastmcp import FastMCP
from tools.file_system_tools import read_file as fs_read_file, edit_file as fs_edit_file, list_files as fs_list_files
from tools.code_search_tools import (search_code as cs_search_code,
                                     search_function_or_class_definition_in_code as cs_search_func,
                                     find_references as cs_find_refs)
from tools.execution_tools import get_patch as ex_get_patch, run_command as ex_run_command, run_tests as ex_run_tests


"""MCP server for SWE-bench benchmark.

Exposes filesystem, code search and execution tools for exploring and
modifying a testbed repository. Supports two modes:
- Local mode: maps /testbed paths to TESTBED_PATH env variable.
- Docker mode: routes commands through docker exec CONTAINER_ID.

Environment variables:
    TESTBED_PATH: Local path to the testbed directory (default: /testbed).
    CONTAINER_ID: Docker container ID for Docker mode (optional).

Launch modes:
    uv run python mcp_tools_swebench.py          # stdio
    uv run python mcp_tools_swebench.py --http   # HTTP on port 8000
"""

mcp = FastMCP("agent-smith")


TESTBED_PATH = os.environ.get("TESTBED_PATH", "/testbed")
CONTAINER_ID = os.environ.get("CONTAINER_ID", None)


@mcp.tool()
def read_file(filepath: str, start_line: int, end_line: int) -> str:
    """Read a file with line numbers from the testbed.

    In Docker mode, uses docker exec to read inside the container.
    In local mode, maps /testbed to TESTBED_PATH.

    Args:
        filepath: Path starting with /testbed.
        start_line: First line to read (0-indexed).
        end_line: Last line to read (0-indexed).

    Returns:
        File content with line numbers in cat -n format.
    """
    if CONTAINER_ID:
        cmd = f"docker exec {CONTAINER_ID} cat -n {filepath}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    else:
        real_path = filepath.replace("/testbed", TESTBED_PATH)
        result = fs_read_file(real_path, start_line, end_line)
        return "\n".join(result).replace(TESTBED_PATH, "/testbed")


@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> None:
    """Replace an exact string in a file within the testbed.

    Args:
        filepath: Path to the file to edit.
        old_str: Exact string to find and replace.
        new_str: Replacement string.
    """
    fs_edit_file(filepath, old_str, new_str)
    return


@mcp.tool()
def list_files(directory: str, pattern: str) -> str:
    """List files in a testbed directory matching a glob pattern.

    Args:
        directory: Directory path (e.g. /testbed).
        pattern: Glob pattern (e.g. *.py, *).

    Returns:
        Newline-separated list of matching file paths under /testbed.
    """
    real_dir = directory.replace("/testbed", TESTBED_PATH)
    result = fs_list_files(real_dir, pattern)
    return "\n".join(f.replace(TESTBED_PATH, "/testbed") for f in result)


@mcp.tool()
def search_code(pattern: str, file_pattern: str) -> str:
    """Search for a pattern in files within the testbed.

    Args:
        pattern: String to search for in file content.
        file_pattern: Glob pattern to filter files (e.g. *.py).

    Returns:
        Matching lines in /path:line content format.
    """
    result = cs_search_code(pattern, file_pattern, base_dir=TESTBED_PATH)
    return "\n".join(result).replace(TESTBED_PATH, "/testbed")


@mcp.tool()
def search_function_or_class_definition_in_code(name: str) -> str:
    """Find function or class definitions by name in the testbed.

    Args:
        name: Function or class name to search for.

    Returns:
        Matching definition lines in /path:line content format.
    """
    result = cs_search_func(name, base_dir=TESTBED_PATH)
    return "\n".join(result).replace(TESTBED_PATH, "/testbed")


@mcp.tool()
def find_references(name: str, filepath: str, line: int) -> str:
    """Find all usages of a symbol in the testbed codebase.

    Args:
        name: Symbol name to search for.
        filepath: File where the symbol is defined (for context).
        line: Line number of the definition (for context).

    Returns:
        All lines containing the symbol in /path:line content format.
    """
    real_filepath = filepath.replace("/testbed", TESTBED_PATH)
    result = cs_find_refs(name, real_filepath, line, base_dir=TESTBED_PATH)
    return "\n".join(result).replace(TESTBED_PATH, "/testbed")


@mcp.tool()
def get_patch() -> str:
    """Get the unified git diff of all changes in the testbed.

    Returns:
        Formatted string with stdout, stderr and exit code of git diff.
    """
    result = ex_get_patch()
    return f"stdout: {result['stdout']}\nstderr: \
{result['stderr']}\nexitcode: {result['output']}"


@mcp.tool()
def run_command(command: str, workdir: str) -> str:
    """Execute a shell command in a testbed directory.

    Args:
        command: Shell command to execute.
        workdir: Working directory (e.g. /testbed).

    Returns:
        Formatted string with stdout, stderr and exit code.
    """
    real_workdir = workdir.replace("/testbed", TESTBED_PATH)
    result = ex_run_command(command, real_workdir)
    return f"stdout: {result['stdout']}\nstderr: {result['stderr']}\nexitcode: {result['output']}"


@mcp.tool()
def run_tests(solution_code: str = "", test_list: List[str] = [],
              test_imports: List[str] = [], code: str = "") -> str:
    """Build and return a Python test script as JSON.

    Args:
        solution_code: Python function source code.
        test_list: List of assert statements.
        test_imports: List of imports needed.
        code: Alias for solution_code.

    Returns:
        JSON string with keys 'success' and 'output'.
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
