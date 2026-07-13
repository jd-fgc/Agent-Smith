from argparse import ArgumentParser
from typing import List
from mcp.server.fastmcp import FastMCP
from tools.execution_tools import run_tests
from asyncio import CancelledError

mcp = FastMCP("agent-smith")


@mcp.tool()
def tool_run_tests(solution_code: str, test_list: List[str],
                   test_imports: List[str]) -> str:
    result = run_tests(solution_code, test_list, test_imports)
    return result


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
