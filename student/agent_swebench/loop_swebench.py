from models.SWE_models import SWEBenchTaskInput, StepMetrics, SolutionOutput
from agent_utils import load_keys, load_model, respond, load_tools, Tool
from openai import OpenAI, RateLimitError
from code_parser import ToolCall, tool_call_reformer, extract_code
from typing import Any
import time
import json


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
                "run_command",
                "finish_exploration"
            ]
        elif self.phase == "edit":
            return [
                "read_file",
                "list_files",
                "search_code",
                "search_function_or_class_definition_in_code",
                "run_command",
                "edit_file",
                "run_tests",
                "finish_editing"
            ]
        elif self.phase == "patch":
            return [
                "read_file",
                "list_files",
                "search_code",
                "search_function_or_class_definition_in_code",
                "run_command",
                "edit_file",
                "run_tests",
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
    prompt.append("Choose exactly ONE function.")
    prompt.append("Here are the available functions\n")
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
    prompt.append("Return ONLY ONE valid JSON using the following schema.")
    prompt.append("Schema:")
    prompt.append("{")
    prompt.append("\t'tool': '<tool_name>',")
    prompt.append("\t'arguments': '{")
    prompt.append("\t...")
    prompt.append("\t}")
    prompt.append("}")
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


def build_eval_script(script: str, file_path: str) -> None:
    try:
        with open(file_path, "w") as file:
            file.write(script)
    except Exception:
        raise Exception("An error occured during the creation of the script.")



def agent_loop_swebench(tasks: SWEBenchTaskInput, model: str,
                        keys: list[str], client: OpenAI,
                        max_iteration: int, sandbox) -> SolutionOutput:
    agent_phase = Phases()
    current_key = 0
    key_usage = 0
    metrics = []
    history = []
    success = False
    patch = ""
    iteration = 0
    tools = load_tools()
    build_eval_script(tasks.eval_script, "./script.sh")
    while iteration < max_iteration and success is False:
        available_func = agent_phase.get_possible_func()
        iteration += 1
        try:
            tool_call = ""
            tool_result = {}
            message = build_prompt(tasks, available_func, history, agent_phase.phase, tools)
            start = time.time()
            answer = respond(client, model, message)
            request_time = round((time.time() - start) * 1000, 2)
            raw_response = answer.choices[0].message.content
            code = extract_code(raw_response)
            if not isinstance(code, ToolCall):
                history.append({
                    "action": {
                        "tool": "invalid",
                        "args": {}
                    },
                    "observation": {
                        "result": raw_response
                    }
                })
                metrics.append(StepMetrics(
                    step=len(metrics)+1,
                    input_tokens=answer.usage.prompt_tokens,
                    output_tokens=answer.usage.completion_tokens,
                    request_time_ms=request_time,
                    api_url=str(client.base_url),
                    model_name=model,
                    llm_output=raw_response,
                    sandbox_input="",
                    sandbox_output="",
                    retries=iteration
                ))
                continue
            tool_call = tool_call_reformer(code)
            if code.tool == "finish_exploration":
                agent_phase.phase = "edit"
                tool_result["output"] = "Switching to edit mode"
            elif code.tool == "finish_editing":
                agent_phase.phase = "patch"
                tool_result["output"] = "Switching to patch mode"
            else:
                tool_result = sandbox.execute(tool_call)
            if code.tool == "get_patch":
                if tool_result["output"].strip():
                    success = True
                    patch = tool_result
                    metrics.append(StepMetrics(
                        step=len(metrics)+1,
                        input_tokens=answer.usage.prompt_tokens,
                        output_tokens=answer.usage.completion_tokens,
                        request_time_ms=request_time,
                        api_url=str(client.base_url),
                        model_name=model,
                        llm_output=raw_response,
                        sandbox_input=tool_call,
                        sandbox_output=tool_result["output"],
                        retries=iteration
                    ))
                    break
                else:
                    history.append({
                        "action": {
                            "tool": "get_patch",
                            "args": {}
                        },
                        "observation": {
                            "result": "The git diff is empty. No changes have been made yet."
                        }
                    })
                    metrics.append(StepMetrics(
                        step=len(metrics)+1,
                        input_tokens=answer.usage.prompt_tokens,
                        output_tokens=answer.usage.completion_tokens,
                        request_time_ms=request_time,
                        api_url=str(client.base_url),
                        model_name=model,
                        llm_output=raw_response,
                        sandbox_input=tool_call,
                        sandbox_output=tool_result["output"],
                        retries=iteration
                    ))
                    continue
            history.append({
                "action": {
                    "tool": code.tool,
                    "args": code.arguments
                },
                "observation": {
                    "result": tool_result
                }
            })
            metrics.append(StepMetrics(
                step=len(metrics)+1,
                input_tokens=answer.usage.prompt_tokens,
                output_tokens=answer.usage.completion_tokens,
                request_time_ms=request_time,
                api_url=str(client.base_url),
                model_name=model,
                llm_output=raw_response,
                sandbox_input=tool_call,
                sandbox_output=tool_result["output"],
                retries=iteration
            ))
        except(RateLimitError, Exception) as e:
            request_time = round((time.time() - start) * 1000, 2)
            print(e)
            metrics.append(StepMetrics(
                step=len(metrics) + 1,
                input_tokens=0,
                output_tokens=0,
                request_time_ms=request_time,
                api_url=str(client.base_url),
                model_name=model,
                llm_output="",
                sandbox_input="",
                sandbox_output="",
                retries=iteration
                ))
    return SolutionOutput(
        task_id=task.instance_id,
        benchmark="swebench",
        success=success,
        solution=patch,
        iterations=iteration,
        total_requests=len(metrics),
        total_input_tokens=sum(inputs.input_tokens for inputs in metrics),
        total_output_tokens=sum(inputs.output_tokens for inputs in metrics),
        total_time_seconds=sum(inputs.request_time_ms for inputs in metrics),
        steps=metrics,
        system_prompt=message
    )


if __name__ =="__main__":
    task = load_task("../cache/SWE.json")
    keys = load_keys()
    client = load_model(keys[0], "https://openrouter.ai/api/v1")
    model = "poolside/laguna-xs-2.1:free"
    agent_loop_swebench(task, model, keys, client, 1, sandbox="")
