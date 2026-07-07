import subprocess
from typing import List


def run_tests(solution_code: str, test_list: List[str],
              test_imports: List[str]) -> str:
    script = ""
    imp = ""
    tests = ""
    for impt in test_imports:
        imp += f"import {impt}\n"
    for tst in test_list:
        escaped = tst.replace("'", "\"")
        tests += f"try:\n    {tst}\n    print('PASS: {escaped}')\n\
except AssertionError:\n    print('FAIL: {escaped}')\n"
    script = imp + solution_code + "\n" + tests

    return script


def get_patch():
    sub = subprocess.run("git -c core.fileMode=false diff",
                         shell=True,
                         capture_output=True,
                         text=True)

    return {
        "stdout": sub.stdout,
        "stderr": sub.stderr,
        "output": sub.returncode
    }


def run_command(command, workdir):
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


if __name__ == "__main__":
    script = run_tests(
        solution_code="def add(a, b):\n    return a + b",
        test_list=["assert add(2, 3) == 5", "assert add(0, 0) == 0"],
        test_imports=[]
    )
    print(script)
    exec(script)