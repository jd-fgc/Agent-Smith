from argparse import ArgumentParser
import asyncio


# def REPL():
#     while True:
#         try:
#             code = input(">>> ")
#             if code == "exit":
#                 break
#             result = await sandbox.execute(code)
#             print(result["output"])
#         except EOFError:
#             break


def do_args():
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


def main():
    parser = do_args()
    args = parser.parse_args()
    print(args)


if __name__ == "__main__":
    main()
