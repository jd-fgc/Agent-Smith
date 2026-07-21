from typing import List
from pathlib import Path
import fnmatch


def search_code(pattern: str, file_pattern: str, base_dir: str = "./") -> List[str]:
    try:
        folder = Path(base_dir)
        result = []
        for file in folder.rglob("*"):
            if file.is_file() and (file_pattern == "*" or fnmatch.fnmatch(file.name, file_pattern)):
                current_line = 0
                try:
                    with open(file.as_posix(), "r") as f:
                        for line in f:
                            if pattern in line:
                                result.append(f"{file.as_posix()}: {current_line} {line}")
                            current_line += 1
                except (UnicodeDecodeError, PermissionError):
                    pass
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)


def search_function_or_class_definition_in_code(name: str) -> List[str]:
    try:
        folder = Path("./")
        result = []
        for file in folder.rglob("*"):
            if file.suffix == ".py":
                current_line = 0
                with open(file.as_posix(), "r") as f:
                    for line in f:
                        if f"def {name}" in line or f"class {name}" in line:
                            result.append(
                                f"{file.as_posix()}: {current_line} {line}"
                            )
                        current_line += 1
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)


def find_references(name: str, filepath: str, line: int) -> List[str]:
    try:
        folder = Path("./")
        result = []
        for file in folder.rglob("*"):
            if file.suffix == ".py":
                current_line = 0
                with open(file.as_posix(), "r") as f:
                    for li in f:
                        if name in li:
                            result.append(
                                f"{file.as_posix()}: {current_line} {li}"
                            )
                        current_line += 1
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)
