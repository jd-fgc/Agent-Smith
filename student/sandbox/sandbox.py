from __future__ import annotations
from ..models.sandbox_config import SandboxConfig
from typing import Any, Optional
from contextlib import AsyncExitStack
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from pathlib import Path
import nest_asyncio
import multiprocessing
import resource
import asyncio
import socket
import sys
import io
import os
import sys as _sys
import tempfile
nest_asyncio.apply()


def block_network() -> None:
    """Block all network access by replacing socket.socket with a stub
    that raises PermissionError on any connection attempt."""
    def blocked(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("Network access denied")

    socket.socket = blocked  # type: ignore[misc, assignment]


class FlushFile:
    """File-like wrapper that flushes after every write.

    Used as sys.stdout replacement in the worker process to ensure
    partial output is written to disk before a timeout kill.
    """
    def __init__(self, f):
        self.f = f

    def write(self, text):
        self.f.write(text)
        self.f.flush()

    def flush(self):
        self.f.flush()


def worker(code, namespace, output_file, max_memory_mb):
    """Execute Python code in an isolated worker process.

    Sets memory limits via resource.setrlimit, blocks network access,
    redirects stdout to output_file via FlushFile, then runs exec().
    Catches MemoryError and generic exceptions and writes them to the file.

    Args:
        code: Python source code to execute.
        namespace: Execution namespace dict.
        output_file: Path to temporary file for capturing stdout.
        max_memory_mb: Maximum RAM in MB allowed for this process.
    """
    restricted_memory = max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (restricted_memory, restricted_memory))
    block_network()

    with open(output_file, 'w') as f:
        sys.stdout = FlushFile(f)
        try:
            exec(code, namespace)
        except MemoryError:
            sys.stdout = sys.__stdout__
            f.write("\nMEMORY LIMIT EXCEEDED")
            f.flush()
        except Exception as e:
            sys.stdout = sys.__stdout__
            f.write(str(e))
            f.flush()
        finally:
            sys.stdout = sys.__stdout__


class Sandbox:
    """Secure Python execution environment with MCP tool integration.

    Connects to an MCP server (stdio or HTTP), discovers available tools,
    injects them into a restricted execution namespace, and runs LLM-generated
    code with import restrictions, filesystem limits, network blocking,
    timeout enforcement and memory limits.
    """
    def __init__(self, config: SandboxConfig, mcp_stdio: str | None = None, mcp_url: str | None = None) -> None:
        """Initialize the Sandbox.

        Args:
            config: SandboxConfig with security constraints.
            mcp_stdio: Shell command to launch an MCP server via stdio.
            mcp_url: URL of an HTTP MCP server to connect to.
        """
        self.config = config
        self.mcp_stdio = mcp_stdio
        self.mcp_url = mcp_url
        self.tools: dict[str, Any] = {}
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self.answer: Optional[str] = None

    async def connect(self) -> None:
        """Connect to the MCP server and discover available tools.

        Uses stdio_client or streamablehttp_client depending on configuration.
        Populates self.tools with the server's tool descriptors.
        Does nothing if neither mcp_stdio nor mcp_url is set.
        """
        self._exit_stack = AsyncExitStack()

        if self.mcp_stdio:
            parts = self.mcp_stdio.split()
            flags = [p for p in parts[1:] if p.startswith("--")]
            non_flags = [p for p in parts[1:] if not p.startswith("--")]
            script = " ".join(non_flags)
            params = StdioServerParameters(
                command=_sys.executable,
                args=[script] + flags,
                env={**os.environ, "PYTHONPATH": "."}
            )
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
        assert self.session is not None
        await self.session.initialize()

        tools = await self.session.list_tools()
        for tool in tools.tools:
            self.tools[tool.name] = tool

    async def disconnect(self) -> None:
        """Close the MCP connection and release all async resources."""
        assert self._exit_stack is not None
        await self._exit_stack.aclose()

    def safe_import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Custom __import__ that enforces the authorized_imports allowlist.

        Args:
            name: Module name to import.

        Returns:
            The imported module if authorized.

        Raises:
            ImportError: If the module is not in authorized_imports.
        """
        if name in self.config.authorized_imports:
            return __import__(name, *args, **kwargs)
        else:
            raise ImportError(f"Import '{name}' not autorised")

    def safe_open(self, filepath: str, *args: Any, **kwargs: Any) -> Any:
        """Custom open() that enforces filesystem directory restrictions.

        Args:
            filepath: Path to open.

        Returns:
            File object if path is in allowed_directories.

        Raises:
            PermissionError: If the resolved path is outside allowed directories.
        """
        path = Path(filepath).resolve()

        for allowed in self.config.allowed_directories:
            if str(path).startswith(allowed):
                return open(filepath, *args, **kwargs)
        raise PermissionError(f"ACCESS DENIED: {filepath}")

    def _make_tool_wrapper(self, tool_name: str) -> Any:
        """Create a synchronous wrapper for an async MCP tool call.

        Args:
            tool_name: Name of the MCP tool to wrap.

        Returns:
            A callable that invokes the MCP tool synchronously and returns
            the text content of the result.
        """
        def wrapper(**kwargs: Any) -> Any:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self.session.call_tool(tool_name, kwargs)  # type: ignore[union-attr]
            )
            if result.content:
                return result.content[0].text
            return ""
        return wrapper

    def _final_answer(self, answer: str) -> None:
        """Capture the agent's final answer and signal task completion.

        Args:
            answer: The solution string produced by the agent.
        """
        self.answer = answer

    def _build_namespace(self) -> dict[str, Any]:
        """Build the restricted execution namespace for exec().

        Returns a dict with:
        - __builtins__: allowlisted Python builtins
        - safe_import as __import__
        - safe_open as open
        - MCP tools injected by name
        - final_answer function

        Returns:
            The namespace dict to pass to exec().
        """
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
            "AssertionError": AssertionError,
            "ImportError": ImportError,
            "dir": dir,
            "ZeroDivisionError": ZeroDivisionError,
            "MemoryError": MemoryError,
            "all": all,
            "any": any,
            "bytearray": bytearray,
            "bytes": bytes,
        }

        for tools_name in self.tools:
            namespace[tools_name] = self._make_tool_wrapper(tools_name)

        namespace["final_answer"] = self._final_answer  # type: ignore[assignment]

        return namespace

    async def execute(self, code: str, namespace: dict[str, Any] | None = None,
                      repl_mode: bool = False) -> dict[str, Any]:
        """Execute Python code in the sandbox.

        In repl_mode: runs exec() directly in the current process,
        capturing stdout via StringIO. Suitable for interactive use with MCP tools.

        In non-repl mode: spawns a worker process with memory limits,
        network blocking and timeout enforcement. Output is captured via
        a temporary file to preserve partial output on timeout.

        Args:
            code: Python source code to execute.
            namespace: Execution namespace. Built fresh if None.
            repl_mode: If True, run in-process without multiprocessing.

        Returns:
            Dict with keys 'success' (bool) and 'output' (str).
        """
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
            # créer un fichier temporaire pour capturer l'output
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp_path = tmp.name

            process = multiprocessing.Process(
                target=worker,
                args=(code, namespace, tmp_path, self.config.max_memory_mb)
            )
            process.start()
            process.join(timeout=self.config.max_execution_time_seconds)

            if process.is_alive():
                process.terminate()
                process.join()

            # lire l'output même partiel
            try:
                with open(tmp_path, 'r') as f:
                    output = f.read()
            except Exception:
                output = ""
            os.unlink(tmp_path)

            if not output and process.exitcode != 0:
                return {"success": False, "output": "TIMEOUT"}
            return {"success": True, "output": output}
