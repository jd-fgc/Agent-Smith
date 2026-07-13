import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
import multiprocessing
from pathlib import Path
import socket
import resource
import sys
import io


def block_network():
    def blocked(*args, **kwargs):
        raise PermissionError("Network access denied")

    socket.socket = blocked


def worker(code, namespace, result_queue, max_memory_mb):
    restricted_memory = max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (restricted_memory,
                                            restricted_memory))
    block_network()

    captured_stdout = io.StringIO()
    sys.stdout = captured_stdout
    try:
        exec(code, namespace)
        result_queue.put({"success": True,
                          "output": captured_stdout.getvalue()})
    except MemoryError:
        sys.stdout = sys.__stdout__
        result_queue.put({"success": False, "output": "MEMORY LIMIT EXCEEDED"})
    except Exception as e:
        result_queue.put({"success": False, "output": str(e)})
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
                stdio_client(params)
            )
        elif self.mcp_url:
            read, write, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(self.mcp_url)
            )
        else:
            return

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

    def safe_open(self, filepath, *args, **kwargs):
        path = Path(filepath).resolve()

        for allowed in self.config.allowed_directories:
            if str(path).startswith(allowed):
                return open(filepath, *args, **kwargs)
        raise PermissionError(f"ACCESS DENIED: {filepath}")

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
            "open": self.safe_open,
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

    async def execute(self, code, namespace=None, repl_mode=False):
        if namespace is None:
            namespace = self._build_namespace()

        if repl_mode:
            captured_stdout = io.StringIO()
            sys.stdout = captured_stdout
            try:
                exec(code, namespace)
                output = captured_stdout.getvalue()
                return {"success": True, "output": output}
            except Exception as e:
                return {"success": False, "output": str(e)}
            finally:
                sys.stdout = sys.__stdout__
        else:
            result_queue = multiprocessing.Queue()

            process = multiprocessing.Process(
                target=worker,
                args=(code, namespace, result_queue, self.config.max_memory_mb)
            )
            process.start()
            process.join(timeout=self.config.max_execution_time_seconds)
            if process.is_alive():
                process.terminate()
                return {"success": False, "output": "TIMEOUT"}
            else:
                if result_queue.empty():
                    return {
                        "success": False,
                        "output": f"PROCESS KILLED (exitcode: {process.exitcode})",
                    }
                return result_queue.get()
