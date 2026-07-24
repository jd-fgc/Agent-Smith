import ast
import docker
import subprocess
from docker.models.containers import Container
from typing import Any


class DockerSandbox:
    def __init__(self, image: str):
        self.image = image
        self.client = docker.from_env()
        self.container: Container | None = None

    def start(self) -> None:
        self.container = self.client.containers.run(
            image=self.image,
            command="sleep infinity",
            detach=True,
            tty=True,
            working_dir="/testbed",
            network_mode="none"
        )

    def execute(self, tool_call: str) -> dict[str, Any]:
        """Parse et exécute un tool_call dans le container Docker."""
        if self.container is None:
            raise RuntimeError("Sandbox not started")

        func_name = tool_call.split("(")[0].strip()
        args_str = tool_call.split("(", 1)[1].rsplit(")", 1)[0]
        args = self._parse_args(args_str)

        if func_name == "read_file":
            return self._read_file(**args)
        elif func_name == "edit_file":
            return self._edit_file(**args)
        elif func_name == "list_files":
            return self._list_files(**args)
        elif func_name == "search_code":
            return self._search_code(**args)
        elif func_name == "search_function_or_class_definition_in_code":
            return self._search_definition(**args)
        elif func_name == "find_references":
            return self._find_references(**args)
        elif func_name == "get_patch":
            return self._get_patch()
        elif func_name == "run_command":
            return self._run_command(**args)
        else:
            return {"output": f"Unknown tool: {func_name}"}

    def _run_docker(self, cmd: str, workdir: str = "/testbed") -> dict[str, Any]:
        """Exécute une commande dans le container."""
        result = self.container.exec_run(
            cmd=["bash", "-c", cmd],
            workdir=workdir
        )
        return {"output": result.output.decode("utf-8", errors="replace")}

    def _parse_args(self, args_str: str) -> dict[str, Any]:
        """Parse les arguments key=value d'un tool call."""
        args = {}
        if not args_str.strip():
            return args

        try:
            parsed = ast.parse(f"dict({args_str})", mode='eval')
            for keyword in parsed.body.keywords:
                key = keyword.arg
                try:
                    value = ast.literal_eval(keyword.value)
                except Exception:
                    value = ast.unparse(keyword.value)
                args[key] = value
        except Exception:
            # fallback simple
            import re
            parts = re.split(r',\s*(?=\w+=)', args_str)
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    args[key.strip()] = value.strip().strip('"').strip("'")
        return args

    def _read_file(self, filepath: str, start_line: str = "1", end_line: str = "50") -> dict[str, Any]:
        cmd = f"sed -n '{start_line},{end_line}p' {filepath} | cat -n"
        return self._run_docker(cmd)

    def _edit_file(self, filepath: str, old_str: str, new_str: str) -> dict[str, Any]:
        script = f"""
import sys
with open('{filepath}', 'r') as f:
    content = f.read()
content = content.replace('''{old_str}''', '''{new_str}''', 1)
with open('{filepath}', 'w') as f:
    f.write(content)
print('OK')
"""
        result = self.container.exec_run(
            cmd=["python3", "-c", script],
            workdir="/testbed"
        )
        return {"output": result.output.decode("utf-8", errors="replace")}

    def _list_files(self, directory: str, pattern: str = "*") -> dict[str, Any]:
        cmd = f"find {directory} -name '{pattern}' -type f"
        return self._run_docker(cmd)

    def _search_code(self, pattern: str, file_pattern: str = "*.py") -> dict[str, Any]:
        cmd = f"grep -rn '{pattern}' --include='{file_pattern}' /testbed"
        return self._run_docker(cmd)

    def _search_definition(self, name: str) -> dict[str, Any]:
        cmd = f"grep -rn 'def {name}\\|class {name}' --include='*.py' /testbed"
        return self._run_docker(cmd)

    def _find_references(self, name: str, filepath: str = "", line: str = "0") -> dict[str, Any]:
        cmd = f"grep -rn '{name}' --include='*.py' /testbed"
        return self._run_docker(cmd)

    def _get_patch(self) -> dict[str, Any]:
        result = self.container.exec_run(
            cmd=["git", "-c", "core.fileMode=false", "diff"],
            workdir="/testbed"
        )
        return {"output": result.output.decode("utf-8", errors="replace")}

    def _run_command(self, command: str, workdir: str = "/testbed") -> dict[str, Any]:
        return self._run_docker(command, workdir=workdir)

    def stop(self) -> None:
        if self.container:
            self.container.remove(force=True)
            self.container = None
