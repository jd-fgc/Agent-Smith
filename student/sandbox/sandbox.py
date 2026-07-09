import argparse
import asyncio


def REPL():
    while True:
        try:
            code = input(">>> ")
            if code == "exit":
                break
            result = await sandbox.execute(code)
            print(result["output"])
        except EOFError:
            break
