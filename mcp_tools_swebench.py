from typing import List
from argparse import ArgumentParser
from asyncio import CancelledError
import sys
import os
import json


TESTBED_PATH = os.environ.get("TESTBED_PATH", "/testbed")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp"))

from mcp.server.fastmcp import FastMCP
from tools.file_system_tools import read_file as fs_read_file, edit_file as fs_edit_file, list_files as fs_list_files
from tools.code_search_tools import (search_code as cs_search_code,
                                     search_function_or_class_definition_in_code as cs_search_func,
                                     find_references as cs_find_refs)
from tools.execution_tools import get_patch as ex_get_patch, run_command as ex_run_command, run_tests as ex_run_tests


mcp = FastMCP("agent-smith")


@mcp.tool()
def read_file(filepath: str, start_line: int, end_line: int) -> str:
    real_path = filepath.replace("/testbed", TESTBED_PATH)
    result = fs_read_file(real_path, start_line, end_line)
    return "\n".join(result)

# # avec Docker
# @mcp.tool()
# def tool_read_file(filepath, start_line, end_line):
#     cmd = f"docker exec {CONTAINER_ID} cat -n {filepath}"
#     result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
#     return result.stdout


@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> None:
    fs_edit_file(filepath, old_str, new_str)
    return


@mcp.tool()
def list_files(directory: str, pattern: str) -> str:
    real_dir = directory.replace("/testbed", TESTBED_PATH)
    result = fs_list_files(real_dir, pattern)
    return "\n".join(f.replace(TESTBED_PATH, "/testbed") for f in result)


@mcp.tool()
def search_code(pattern: str, file_pattern: str) -> str:
    result = cs_search_code(pattern, file_pattern, base_dir=TESTBED_PATH)
    return "\n".join(result).replace(TESTBED_PATH, "/testbed")


@mcp.tool()
def search_function_or_class_definition_in_code(name: str) -> str:
    result = cs_search_func(name)
    return "\n".join(result)


@mcp.tool()
def find_references(name: str, filepath: str, line: int) -> str:
    result = cs_find_refs(name, filepath, line)
    return "\n".join(result)


@mcp.tool()
def get_patch() -> str:
    result = ex_get_patch()
    return f"stdout: {result['stdout']}\nstderr: \
{result['stderr']}\nexitcode: {result['output']}"


@mcp.tool()
def run_command(command: str, workdir: str) -> str:
    real_workdir = workdir.replace("/testbed", TESTBED_PATH)
    result = ex_run_command(command, real_workdir)
    return f"stdout: {result['stdout']}\nstderr: {result['stderr']}\nexitcode: {result['output']}"


@mcp.tool()
def run_tests(solution_code: str = "", test_list: List[str] = [],
              test_imports: List[str] = [], code: str = "") -> str:
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
