from pathlib import Path


def search_code(pattern, file_pattern):
    try:
        folder = Path("./")
        result = []
        for file in folder.rglob("*"):
            if file.suffix == file_pattern:
                current_line = 0
                with open(file.as_posix(), "r") as f:
                    for line in f:
                        if pattern in line:
                            result.append(
                                f"{file.as_posix()}: {current_line} {line}"
                            )
                        current_line += 1
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)


def search_function_or_class_definition_in_code(name):
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


def find_references(name, filepath, line):
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
