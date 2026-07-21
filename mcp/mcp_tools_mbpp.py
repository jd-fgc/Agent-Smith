from argparse import ArgumentParser
from typing import List
from mcp.server.fastmcp import FastMCP
from tools.execution_tools import run_tests as ex_run_tests
from asyncio import CancelledError
import json

mcp = FastMCP("agent-smith")


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
