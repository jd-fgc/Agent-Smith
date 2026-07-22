from typing import Dict, List
import subprocess
import os

TESTBED_PATH = os.environ.get("TESTBED_PATH", "/testbed")


def run_tests(solution_code: str, test_list: List[str],
              test_imports: List[str]) -> str:
    """Build a Python test script combining solution code and assertions.

    Wraps each assertion in a try/except block to print PASS or FAIL.
    The resulting script is intended to be executed by the sandbox.

    Args:
        solution_code: Python source code of the function to test.
        test_list: List of assert statements (e.g. ["assert f(1) == 2"]).
        test_imports: List of module names to import at the top of the script.

    Returns:
        A Python script as a string ready for exec().
    """
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
    """Get the unified git diff of all changes in TESTBED_PATH.

    Returns:
        Dict with keys 'stdout' (diff output), 'stderr' and 'output' (exit code).
    """

    sub = subprocess.run("git -c core.fileMode=false diff",
                         shell=True,
                         cwd=TESTBED_PATH,
                         capture_output=True,
                         text=True)

    return {
        "stdout": sub.stdout,
        "stderr": sub.stderr,
        "output": sub.returncode
    }


def run_command(command: str, workdir: str) -> Dict[str, str | int]:
    """Execute a shell command in the specified working directory.

    Args:
        command: Shell command string to execute.
        workdir: Working directory path.

    Returns:
        Dict with keys 'stdout', 'stderr' and 'output' (exit code).
    """
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
