from pathlib import Path


def read_file(filepath, start_line, end_line):
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


def edit_file(filepath, old_str, new_str):
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()

        with open(filepath, "w") as file:
            for line in lines:
                line = line.replace(old_str, new_str)
                file.write(line)
    except (PermissionError, FileNotFoundError) as e:
        raise Exception(e)


def list_files(directory, pattern):
    try:
        folder = Path(directory)
        result = []
        for file in folder.glob("*"):
            if file.suffix == pattern or pattern == "*" or pattern == "":
                result.append(file.as_posix())
        return result
    except (FileNotFoundError, PermissionError) as e:
        raise Exception(e)
