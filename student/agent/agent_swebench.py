from ..models.swe_models import SWEBenchTaskInput, StepMetrics, SolutionOutput
from agent_utils import load_keys, load_model, respond, load_tools, Tool
from openai import OpenAI, RateLimitError
from code_parser import ToolCall, tool_call_reformer, extract_code
from typing import Any
import json
import docker


class Phases:
    def __init__(self) -> None:
        self.phase = "explore"

    def get_possible_func(self) -> list[str]:
        if self.phase == "explore" or self.phase == "read":
            return [
                "read_file",
                "list_files",
                "search_code",
                "search_function_or_class_definition_in_code",
                "find_references",
                "run_command"
            ]
        elif self.phase == "edit":
            return [
                "edit_file",
                "run_tests"
            ]
        elif self.phase == "patch":
            return [
                "get_patch"
            ]
        else:
            return []


def load_task(path: str) -> SWEBenchTaskInput:
    try:
        with open(path, "r") as file:
            task = json.load(file)
        return SWEBenchTaskInput(
            instance_id=task["instance_id"],
            problem_statement=task["problem_statement"],
            docker_image=task["docker_image"],
            eval_script=task["eval_script"],
            hints_text=task["hints_text"],
            repo=task["repo"]
        )
    except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
        raise Exception(e)


def build_prompt(task: SWEBenchTaskInput, tools: list[str], history: list[dict[str, Any]],
                 state: str, tools_def: dict[str, Tool]) -> str:
    prompt = []
    prompt.append("Issue:\n")
    prompt.append(task.problem_statement + "\n\n")
    prompt.append("Historique:\n\n")
    for i, step in enumerate(history, start=1):
        prompt.append(f"Action {i}\n")
        prompt.append(f"Tool: {step['action']['tool']}\n")

        if step["action"]["args"]:
            prompt.append("Arguments:\n")
            for k, v in step["action"]["args"].items():
                prompt.append(f"- {k}: {v}\n")

        prompt.append("Observation:\n")
        prompt.append(step["observation"]["result"])
    prompt.append("Choose exactly ONE tool.")
    prompt.append("Here are the available tools\n")
    for tool in tools:
        try:
            prompt.append(f"- {tools_def[tool].signature}")
            prompt.append(f"\t{tools_def[tool].description}")
        except KeyError:
            continue
    if state == "edit" and task.hints_text != "":
        prompt.append("Here are hints to help you fix the code:\n\n")
        prompt.append(f"{task.hints_text}\n")
    prompt.append("Never assume file names")
    prompt.append("Don't add unnecessary text. Be consise.")
    prompt.append("Respond only with a single tool call")
    prompt.append("Answer in JSON format")
    return "\n".join(prompt)


def build_history(tool: str, observation: str) -> dict[str, Any]:
    result = {}
    result.update({"action": {}})
    func_name = tool.split("(")[0]
    args = tool.split("(", 1)[1].split(")")[0].split(",")
    result["action"].update({
        "tool": func_name
    })
    result["action"].update({
        "args": {}
    })
    for arg in args:
        name, value = arg.split("=")
        result["action"]["args"].update({
            name: value
        })
    result.update({
        "observation": {"result": observation}
    })
    return result


def agent_loop_swebench(tasks: SWEBenchTaskInput, model: str,
                        keys: list[str], client: OpenAI,
                        max_iteration: int) -> SolutionOutput:
    agent_phase = Phases()
    current_key = 0
    key_usage = 0
    metrics = []
    history = []
    success = False
    iteration = 0
    tools = load_tools()
    while iteration < max_iteration and success is False:
        available_func = agent_phase.get_possible_func()
        try:
            message = build_prompt(tasks, available_func, history, agent_phase.phase, tools)
            answer = respond(client, model, message)
            print(answer.choices[0].message.content)
            code = extract_code(answer.choices[0].message.content)
            if isinstance(code, ToolCall):
                code = tool_call_reformer(code)
            print(code)
            iteration += 1
        except (RateLimitError, Exception) as e:
            print(e)
            iteration += 1


if __name__ == "__main__":
    task = SWEBenchTaskInput(
        instance_id="1",
        problem_statement="The function add(a: int, b: int) does not return anything",
        docker_image="BBBBB",
        eval_script="CCCCC",
        hints_text="DDDDD",
        repo="EEEEE"
    )
    keys = load_keys()
    client = load_model(keys[0], "https://openrouter.ai/api/v1")
    model = "poolside/laguna-xs-2.1:free"
    agent_loop_swebench(task, model, keys, client, 1)
