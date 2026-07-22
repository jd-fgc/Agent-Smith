from typing import List
from pathlib import Path
import fnmatch


def read_file(filepath: str, start_line: int, end_line: int) -> List[str]:
    """Read lines from a file with line number prefixes.

    Output format matches cat -n: "<line_number>: <content>".

    Args:
        filepath: Absolute path to the file.
        start_line: First line to read (0-indexed).
        end_line: Last line to read (0-indexed, inclusive).

    Returns:
        List of formatted strings with line numbers.

    Raises:
        Exception: On FileNotFoundError or PermissionError.
    """
    try:
        current_line = 0
        result = []
        with open(filepath, "r") as file:
            for line in file:
                if current_line >= start_line and current_line <= end_line:
                    result.append(
                        f"{current_line}: {line}"
                    )
                if current_line > end_line:
                    break
                current_line += 1
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)


def edit_file(filepath: str, old_str: str, new_str: str) -> None:
    """Replace an exact string in a file, line by line.

    Args:
        filepath: Path to the file to modify.
        old_str: Exact string to replace.
        new_str: Replacement string.

    Raises:
        Exception: On PermissionError or FileNotFoundError.
    """
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()

        with open(filepath, "w") as file:
            for line in lines:
                line = line.replace(old_str, new_str)
                file.write(line)
    except (PermissionError, FileNotFoundError) as e:
        raise Exception(e)


def list_files(directory: str, pattern: str) -> List[str]:
    """List files in a directory matching a glob pattern.

    Args:
        directory: Directory path to list.
        pattern: Glob pattern (e.g. *.py) or empty string / * for all files.

    Returns:
        List of file paths as strings.

    Raises:
        Exception: On FileNotFoundError or PermissionError.
    """
    try:
        folder = Path(directory)
        result = []
        for file in folder.glob("*"):
            if pattern == "*" or pattern == "" or fnmatch.fnmatch(file.name, pattern):
                result.append(file.as_posix())
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)
