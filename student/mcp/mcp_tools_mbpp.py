from mcp.server.fastmcp import FastMCP
from tools.execution_tools import run_tests


mcp = FastMCP("agent-smith")


@mcp.tool()
def tool_run_tests():
    pass


if __name__ == "__main__":
    mcp.run()
