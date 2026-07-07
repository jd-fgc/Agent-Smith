from pydantic import BaseModel
import json
import ast
import xml.etree.ElementTree as ET


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, str]


def extract_code(text: str) -> str | ToolCall:
    if "```" in text:
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
    content = text.split("<tool_call>", 1)[1].split("</tool_call>", 1)[0].strip()
    try:
        data = json.loads(content)
    except Exception:
        data = ast.literal_eval(content)
    
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


# if __name__ == "__main__":
    # code = "```python\n" + \
    # "def addition(a, b):\n" + \
    # "   return a + b\n" + \
    # "```"
    # code = "Action: calculator\n" + \
    #     "Action Input:\n" + \
    #     "{\n" + \
    #         '"expression": "2+2"\n' + \
    #     "}"
    # code = '<invoke name="search">\n' + \
    #         '<parameter name="query">Paris weather</parameter>\n' + \
    #         '</invoke>'
    # extracted_code = extract_code(code)
    # if isinstance(extracted_code, ToolCall):
    #     result = tool_call_reformer(extracted_code)
    #     print(result)
    # else:
    #     print(extracted_code)