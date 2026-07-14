from typing import Any
from argparse import ArgumentParser
from .models.sandbox_config import SandboxConfig
from .sandbox.sandbox import Sandbox
from pydantic import ValidationError
import asyncio
from json import load


def sanitize_config(config: SandboxConfig) -> SandboxConfig:
    if config.max_memory_mb <= 50 or config.max_memory_mb >= 4096:
        config.max_memory_mb = 512

    if config.max_execution_time_seconds <= 0:
        config.max_execution_time_seconds = 30
    elif config.max_execution_time_seconds >= 900:
        config.max_execution_time_seconds = 900

    import_unauthorized = ["os", "sys", "subprocess", "shutil", "socket",
                           "ctypes", "importlib", "builtins", "pickle"]
    config.authorized_imports = [(imp for imp in config.authorized_imports if
                                  imp not in import_unauthorized)]

    system_dirs = ["/etc", "/bin", "/sbin", "/usr", "/boot",
                   "/root", "/proc", "/sys", "/dev"]
    config.allowed_directories = [
        d for d in config.allowed_directories
        if not any(d.startswith(sys_dir) for sys_dir in system_dirs)
    ]

    return config


async def repl(config: SandboxConfig, mcp_stdio: str | None = None,
               mcp_url: str | None = None) -> None:
    sandbox = Sandbox(config=config, mcp_stdio=mcp_stdio, mcp_url=mcp_url)
    await sandbox.connect()
    namespace = sandbox._build_namespace()

    while True:
        try:
            code = input(">>> ")
            if code == "exit":
                break
            result = await sandbox.execute(code, namespace, repl_mode=True)
            print(result["output"])
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nC'est un vilain Ctrl + C ca mon chaton !")
            break
    await sandbox.disconnect()


def load_file(file: str) -> Any:
    with open(file, "r") as f:
        return load(f)


def do_args() -> ArgumentParser:
    parser = ArgumentParser(
        prog="uv run",
        description="A project by Nisalmon and Jogamber",
        epilog="Qu'est-ce que le réel ? Quel est ta définition du réel ?!"
    )
    parser.add_argument(
        "--mcp-stdio",
        help="Launch the sandbox with the stdio server",
        required=False
    )
    parser.add_argument(
        "--mcp-server",
        help="Launch the sandbox with the http server",
        required=False
    )
    parser.add_argument(
        "config_file",
        nargs="?",  # option for say 0 or 1 arg
        help="Path to sandbox config JSON file",
    )
    return parser


def main() -> None:
    try:
        parser = do_args()
        args = parser.parse_args()

        if args.config_file:
            try:
                config_data = load_file(args.config_file)
                config = SandboxConfig(**config_data)
                config = sanitize_config(config)
            except ValidationError as e:
                print(f"Config invalide : {e}")
                exit(1)
        else:
            config = SandboxConfig()
        asyncio.run(repl(config, mcp_stdio=args.mcp_stdio,
                         mcp_url=args.mcp_server))
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
