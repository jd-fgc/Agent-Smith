import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
import multiprocessing
import sys
import io

from pydantic import BaseModel
from typing import List


def worker(code, namespace, result_queue):
    captured_stdout = io.StringIO()
    sys.stdout = captured_stdout
    try:
        exec(code, namespace)
        result_queue.put({
            "success": True,
            "output": captured_stdout.getvalue()})
    except Exception as e:
        result_queue.put({
            "success": False,
            "output": str(e)})
    finally:
        sys.stdout = sys.__stdout__


class Sandbox:
    def __init__(self, config, mcp_stdio=None, mcp_url=None):
        self.config = config
        self.mcp_stdio = mcp_stdio
        self.mcp_url = mcp_url
        self.tools = {}
        self.session = None
        self._exit_stack = None
        self.answer = None

    async def connect(self):
        self._exit_stack = AsyncExitStack()

        if self.mcp_stdio:
            command, *args = self.mcp_stdio.split()
            params = StdioServerParameters(command=command, args=args)
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(params))
        elif self.mcp_url:
            read, write, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(self.mcp_url)
            )

        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()

        tools = await self.session.list_tools()
        for tool in tools.tools:
            self.tools[tool.name] = tool

    async def disconnect(self):
        await self._exit_stack.aclose()

    def safe_import(self, name, *args, **kwargs):
        if name in self.config.authorized_imports:
            return __import__(name, *args, **kwargs)
        else:
            raise ImportError(f"Import '{name}' not autorised")

    def _make_tool_wrapper(self, tool_name):
        def wrapper(**kwargs):
            return asyncio.run(self.session.call_tool(tool_name, kwargs))

        return wrapper

    def _final_answer(self, answer):
        self.answer = answer

    def _build_namespace(self):
        namespace = {}

        namespace["__builtins__"] = {
            "__import__": self.safe_import,
            "print": print,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "type": type,
            "repr": repr,
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "round": round,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "StopIteration": StopIteration,
        }

        for tools_name in self.tools:
            namespace[tools_name] = self._make_tool_wrapper(tools_name)

        namespace["final_answer"] = self._final_answer

        return namespace

    def execute(self, code):
        namespace = self._build_namespace()
        result_queue = multiprocessing.Queue()

        process = multiprocessing.Process(
            target=worker,
            args=(code, namespace, result_queue)
        )
        process.start()
        process.join(timeout=self.config.max_execution_time_seconds)
        if process.is_alive():
            process.terminate()
            return {"success": False, "output": "TIMEOUT"}
        else:
            return result_queue.get()
