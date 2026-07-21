from pydantic import BaseModel
import json
import ast
import xml.etree.ElementTree as ET
from typing import Any
import re


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any]


def extract_code(text: str) -> str | ToolCall:
    if text.startswith("{"):
        return dict_format(text)
    elif "<tool_call>" in text:
        return JSON_block(text)
    elif "<invoke" in text:
        return XML_block(text)
    elif "Action:" in text:
        return ReAct_block(text)
    elif "```" in text:
        code = python_block(text)
        if code.startswith("{"):
            return dict_format(code)
        return code
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
    return ToolCall(
        tool=tool,
        arguments=args
    )


def XML_block(text: str) -> ToolCall:
    root = ET.fromstring(text)
    tool = root.attrib.get("name")
    arguments = {}
    for param in root.findall(".//parameter"):
        name = param.attrib.get("name")
        value = (param.text or "").strip()
        arguments[name] = value
    return ToolCall(
        tool=tool,
        arguments=arguments
    )


def JSON_block(text: str) -> ToolCall:
    content = text.split("<tool_call>", 1)[1]
    if "<arg_key>" not in text:
        if "</tool_call>" in text:
            content = content.split("</tool_call>", 1)[0].strip()
        try:
            data = json.loads(content)
        except Exception:
            data = ast.literal_eval(content)
    else:
        name = content.split("<arg_key>", 1)[0].strip()
        data = {
            "name": name,
            "arguments": {}
        }
        pairs = re.findall(
            r"<arg_key>(.*?)</arg_key>\s*<arg_value>(.*?)</arg_value>",
            content,
            re.DOTALL
        )
        for key, value in pairs:
            data["arguments"][key.strip()] = value.strip()
    return ToolCall(
            tool=data["name"],
            arguments=data.get("arguments", {})
        )




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
        return ToolCall(
            tool=data["tool"],
            arguments=data.get("arguments", {})
        )
    except KeyError:
        return ToolCall(
            tool=data["tool"],
            arguments=data.get("parameters", {})
        )


# if __name__ == "__main__":
#     test = """
#     Bien sûr je vais répondre...
#     <tool_call>
#     read_file
#     <arg_key>tool</arg_key>
#     <arg_value>search_function_or_class_definition_in_code</arg_value>
#     <arg_key>name</arg_key>
#     <arg_value>RenameContentType</arg_value>
#     """
#     extracted_code = extract_code(test)
#     if isinstance(extracted_code, ToolCall):
#         result = tool_call_reformer(extracted_code)
#         print(result)
#     else:
#         print(extracted_code)