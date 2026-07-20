from typing import Dict, List
import subprocess


def run_tests(solution_code: str, test_list: List[str],
              test_imports: List[str]) -> str:
    script = ""
    imp = ""
    tests = ""
    for impt in test_imports:
        imp += f"import {impt}\n"
    for tst in test_list:
        escaped = tst.replace("'", '"')
        block = "try:\n"
        block += f"    {tst}\n"
        block += f"    print('PASS: {escaped}')\n"
        block += "except AssertionError:\n"
        block += f"    print('FAIL: {escaped}')\n"
        tests += block
    script = imp + solution_code + "\n" + tests

    return exec(script)


def get_patch() -> Dict[str, str | int]:
    sub = subprocess.run("git -c core.fileMode=false diff",
                         shell=True,
                         capture_output=True,
                         text=True)

    return {
        "stdout": sub.stdout,
        "stderr": sub.stderr,
        "output": sub.returncode
    }


def run_command(command: str, workdir: str) -> Dict[str, str | int]:
    sub = subprocess.run(command,
                         shell=True,
                         cwd=workdir,
                         capture_output=True,
                         text=True)

    return {
        "stdout": sub.stdout,
        "stderr": sub.stderr,
        "output": sub.returncode
    }
