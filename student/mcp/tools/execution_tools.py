from typing import Dict
import subprocess


def run_tests():
    # Run test.sh
    pass


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


def run_command(command, workdir) -> Dict[str, str | int]:
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
