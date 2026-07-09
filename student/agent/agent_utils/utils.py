from openai import OpenAI
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import json
import ast
import os


class Tool:
    def __init__(self, name: str, signature: str, description: str) -> None:
        self.name = name
        self.signature = signature
        self.description = description


def load_model(key: str, provider_url: str) -> OpenAI:
    load_dotenv()
    client = OpenAI(api_key=key,
                    base_url=provider_url)
    return client


def respond(llm: OpenAI, model: str, prompt: str) -> ChatCompletion:
    response = llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
    )
    return response


def load_keys() -> list[str]:
    load_dotenv()
    keys = []
    for i in range(5):
        keys.append(os.getenv(f"OPENAI_API_KEY_{i+1}"))
    return keys


def load_tools() -> dict[str, Tool]:
    result = {}
    Tools = []
    Tools.append(Tool(
        name="read_file",
        signature="read_file(filepath: str, start_line: int, end_line: int)",
        description="Read the content of a file between start_line and" + \
            " end_line."
    ))
    Tools.append(Tool(
        name="edit_file",
        signature="edit_file(filepath: str, old_str: str, new_str: str)",
        description="Replace in a file every occurences of old_str by new_str"
    ))
    Tools.append(Tool(
        name="list_files",
        signature="list_files(directory: str, pattern: str)",
        description="list all files in directory ending by pattern.\n" + \
            "\tFor example list_files('./', '*.py') will list all files " + \
            "in ./ ending by .py."
    ))
    Tools.append(Tool(
        name="search_code",
        signature="search_code(pattern: str, file_pattern: str)",
        description="Search for specific pattern of code in file ending " + \
            "in file_pattern."
    ))
    Tools.append(Tool(
        name="search_function_or_class_definition_in_code",
        signature="search_function_or_class_definition_in_code(name: str)",
        description="Search in all files for the function, or class, " + \
            "definition of name."
    ))
    Tools.append(Tool(
        name="find_references",
        signature="find_references(name: str, filepath: str, line: int)",
        description="Find references of name in filepath at line."
    ))
    Tools.append(Tool(
        name="get_patch",
        signature="get_patch()",
        description="Run the following command git -c core.fileMode=false" + \
            "diff and return the output."
    ))
    Tools.append(Tool(
        name="run_command",
        signature="run_command(command: str, workdir: str)",
        description="Run the command given as parameter in workdir"
    ))

    for tool in Tools:
        result[tool.name] = tool
    return result


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, str]


def extract_code(text: str) -> str | ToolCall:
    if text.startswith("{"):
        return dict_format(text)
    elif "```" in text:
        return python_block(text)
    elif "<tool_call>" in text:
        return JSON_block(text)
    elif "<invoke" in text:
        return XML_block(text)
    elif "Action:" in text:
        return ReAct_block(text)
    else:
        return text


def python_block(text: str) -> str | None:
    lines = text.splitlines()
    in_block = False
    code = []

    for line in lines:
        if not in_block:
            if line.lower().startswith("```"):
                in_block = True
            continue
        if line.strip() == "```":
            return "\n".join(code)
        code.append(line)

    return None


def ReAct_block(text: str) -> ToolCall:
    lines = text.splitlines()
    tool = ""
    arguments = []
    in_dict = False
    for line in lines:
        if line.startswith("Action:"):
            tool = line.split(":", 1)[1].strip()
        elif line.startswith("Action Input"):
            in_dict = True
            continue
        elif line.startswith(("Observation:", "Final Answer:")):
            in_dict = False
        elif in_dict:
            arguments.append(line)

    raw_args = "\n".join(arguments).strip()
    try:
        args = json.loads(raw_args)
    except Exception:
        args = ast.literal_eval(raw_args)
    return ToolCall(tool=tool, arguments=args)


def XML_block(text: str) -> ToolCall:
    root = ET.fromstring(text)
    tool = root.attrib.get("name")
    arguments = {}
    for param in root.findall(".//parameter"):
        name = param.attrib.get("name")
        value = (param.text or "").strip()
        arguments[name] = value
    return ToolCall(tool=tool, arguments=arguments)


def JSON_block(text: str) -> ToolCall:
    content = text.split("<tool_call>", 1)[1].split("</tool_call>", 1)[0].strip()
    try:
        data = json.loads(content)
    except Exception:
        data = ast.literal_eval(content)

    return ToolCall(tool=data["name"], arguments=data.get("arguments", {}))


def tool_call_reformer(call: ToolCall) -> str:
    result = []
    result.append(f"{call.tool}(")
    args = len(call.arguments)
    curr_arg = 1
    for key, value in call.arguments.items():
        result.append(f"{key}={value!r}")
        if curr_arg < args:
            result.append(",")
        curr_arg += 1
    result.append(")")
    func_call = "".join(result)
    return func_call


def dict_format(text: str) -> ToolCall:
    try:
        data = json.loads(text)
    except Exception:
        data = ast.literal_eval(text)

    try:
        return ToolCall(tool=data["tool"], arguments=data.get("arguments", {}))
    except KeyError:
        return ToolCall(tool=data["tool"], arguments=data.get("parameters", {}))
