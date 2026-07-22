from typing import List
from pathlib import Path
import fnmatch


def search_code(pattern: str, file_pattern: str, base_dir: str = "./") -> List[str]:
    """Search for a string pattern in files matching a glob pattern.

    Args:
        pattern: String to search for in file content.
        file_pattern: Glob pattern to filter files (e.g. *.py, *).
        base_dir: Root directory to search recursively. Defaults to "./".

    Returns:
        List of matches in "/path:line content" format.

    Raises:
        Exception: On FileNotFoundError or PermissionError.
    """
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


def search_function_or_class_definition_in_code(name: str, base_dir: str = "./") -> List[str]:
    """Find function or class definitions matching a name in Python files.

    Args:
        name: Name of the function or class to find.
        base_dir: Root directory to search recursively. Defaults to "./".

    Returns:
        List of matching definition lines in "/path:line content" format.

    Raises:
        Exception: On FileNotFoundError or PermissionError.
    """
    try:
        folder = Path(base_dir)
        result = []
        for file in folder.rglob("*"):
            if file.suffix == ".py":
                current_line = 0
                with open(file.as_posix(), "r") as f:
                    for line in f:
                        if f"def {name}" in line or f"class {name}" in line:
                            result.append(f"{file.as_posix()}: {current_line} {line}")
                        current_line += 1
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)


def find_references(name: str, filepath: str, line: int, base_dir: str = "./") -> List[str]:
    """Find all occurrences of a symbol name in Python files.

    Args:
        name: Symbol name to search for.
        filepath: File where the symbol is defined (unused, for API compatibility).
        line: Line number of the definition (unused, for API compatibility).
        base_dir: Root directory to search recursively. Defaults to "./".

    Returns:
        List of all lines containing the symbol in "/path:line content" format.

    Raises:
        Exception: On FileNotFoundError or PermissionError.
    """
    try:
        folder = Path(base_dir)
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
