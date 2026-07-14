from argparse import ArgumentParser
from mcp.server.fastmcp import FastMCP
from tools.file_system_tools import read_file, edit_file, list_files
from tools.code_search_tools import (
    search_code,
    search_function_or_class_definition_in_code,
    find_references,
)
from tools.execution_tools import get_patch, run_command
from asyncio import CancelledError


mcp = FastMCP("agent-smith")


@mcp.tool()
def tool_read_file(filepath: str, start_line: int, end_line: int) -> str:
    result = read_file(filepath, start_line, end_line)
    return "\n".join(result)


@mcp.tool()
def tool_edit_file(filepath: str, old_str: str, new_str: str) -> None:
    edit_file(filepath, old_str, new_str)
    return


@mcp.tool()
def tool_list_file(directory: str, pattern: str) -> str:
    result = list_files(directory, pattern)
    return "\n".join(result)


@mcp.tool()
def tool_search_code(pattern: str, file_pattern: str) -> str:
    result = search_code(pattern, file_pattern)
    return "\n".join(result)


@mcp.tool()
def tool_search_function_or_class_definition_in_code(name: str) -> str:
    result = search_function_or_class_definition_in_code(name)
    return "\n".join(result)


@mcp.tool()
def tool_find_references(name: str, filepath: str, line: int) -> str:
    result = find_references(name, filepath, line)
    return "\n".join(result)


@mcp.tool()
def tool_get_patch() -> str:
    result = get_patch()
    return f"stdout: {result['stdout']}\nstderr: \
{result['stderr']}\nexitcode: {result['output']}"


@mcp.tool()
def tool_run_command(command: str, workdir: str) -> str:
    result = run_command(command, workdir)
    return f"stdout: {result['stdout']}\nstderr: \
{result['stderr']}\nexitcode: {result['output']}"


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
