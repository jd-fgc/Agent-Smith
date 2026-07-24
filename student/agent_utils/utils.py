from openai import OpenAI
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv
import os


class Tool:
    '''
    This class is used to create object that will be given to build
    the LLM prompt.
    '''
    def __init__(self, name: str, signature: str, description: str) -> None:
        self.name = name
        self.signature = signature
        self.description = description


def load_model(key: str, provider_url: str) -> OpenAI:
    '''
    This function loads the model used openai package.
    the key {key} must be from {provider_url}.

    It returns an OpenAI object.
    '''
    load_dotenv()
    client = OpenAI(
        api_key=key,
        base_url=provider_url,
        timeout=30.0
    )
    return client


def respond(llm: OpenAI, model: str, prompt: str) -> ChatCompletion:
    '''
    This function is where the LLM will generate his answers.

    It'll use the given llm to answer to {prompt} and will be using
    {model}.

    It returns a ChatCompletion object.
    Useful to retrieve some informations, such as the number of input and output
    tokens.
    '''
    response = llm.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        timeout=30
    )
    return response


def load_keys() -> list[str]:
    '''
    This function is used to load all the API keys

    It returns a list with all the keys.
    '''
    load_dotenv()
    keys = []
    for i in range(5):
        keys.append(os.getenv(f"OPENAI_API_KEY_{i+1}"))
    return keys


def load_tools() -> dict[str, Tool]:
    '''
    This function is used to load all the Tools and store them in a dictionnary
    with Tool.name as key and Tool as value.
    '''
    result = {}
    Tools = []
    Tools.append(Tool(
        name="read_file",
        signature="read_file(filepath: str,"
        "start_line: int, end_line: int)",
        description="Read the content of a file between start_line and"
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
        description="list all files in directory ending by pattern.\n"
        "\tFor example list_files('./', '*.py') will list all files "
        "in ./ ending by .py."
    ))
    Tools.append(Tool(
        name="search_code",
        signature="search_code(pattern: str, file_pattern: str)",
        description="Search for specific pattern of code in file ending "
        "in file_pattern."
    ))
    Tools.append(Tool(
        name="search_function_or_class_definition_in_code",
        signature="search_function_or_class_definition_in_code"
        "(name: str)",
        description="Search in all files for the function, or class, "
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
        description="Run the following command git -c core.fileMode=false"
        "diff and return the output."
    ))
    Tools.append(Tool(
        name="run_command",
        signature="run_command(command: str, workdir: str)",
        description="Run the command given as parameter in workdir"
    ))
    Tools.append(Tool(
        name="finish_exploration",
        signature="finish_exploration()",
        description="Call this when you have gathered enough information "
        "and are ready to start editing."
    ))
    Tools.append(Tool(
        name="finish_editing",
        signature="finish_editing()",
        description="Use this tool only when you believe the "
        "implementation is complete and no further file edits are needed."
    ))

    for tool in Tools:
        result[tool.name] = tool
    return result
