from student.models.SWE_models import SWEBenchTaskInput, StepMetrics, SolutionOutput
from student.agent_utils import load_keys, load_model, respond, load_tools, Tool
from openai import OpenAI, RateLimitError
from student.code_parser import ToolCall, tool_call_reformer, extract_code
from typing import Any
import time
import json


class Phases:
    '''
    This class is used for the LLM to switch Phases and to keep track
    of where he is to fixing the given task.
    '''
    def __init__(self) -> None:
        self.phase = "explore"

    def get_possible_func(self) -> list[str]:
        '''
        This method return all the possible action the LLM can choose
        depending on what phase he currently he's on.
        '''
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
    '''
    This function load the JSON file stored at {path} and
    return the content into a SWEBenchTaskInput object.
    '''
    try:
        with open(path, "r") as file:
            task = json.load(file)
        return SWEBenchTaskInput(
            instance_id=task["instance_id"],
            problem_statement=task["problem_statement"],
            docker_image=task.get("docker_image", task.get("dockerhub_image_name", "")),
            eval_script=task["eval_script"],
            hints_text=task["hints_text"],
            repo=task["repo"]
        )
    except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
        raise Exception(e)


def build_prompt(task: SWEBenchTaskInput, tools: list[str], history: list[dict[str, Any]],
                 state: str, tools_def: dict[str, Tool]) -> str:
    '''
    This function builds the prompt that the LLM will receive.
    It'll be called before every iteration to change the given prompt
    so that way the LLM can keep track of what he has done previously.
    '''
    prompt = []
    prompt.append("You are an autonomous software engineer fixing a bug in a real repository.\n")
    prompt.append("Issue:\n")
    prompt.append(task.problem_statement + "\n\n")

    if history:
        prompt.append("History:\n\n")
        for i, step in enumerate(history, start=1):
            prompt.append(f"Step {i}:\n")
            prompt.append(f"Tool: {step['action']['tool']}\n")
            if step["action"]["args"]:
                prompt.append("Arguments:\n")
                for k, v in step["action"]["args"].items():
                    prompt.append(f"  {k}: {v}\n")
            prompt.append("Observation:\n")
            prompt.append(str(step["observation"]["result"]) + "\n\n")

    prompt.append("Available tools:\n")
    for tool in tools:
        try:
            prompt.append(f"- {tools_def[tool].signature}\n")
            prompt.append(f"  {tools_def[tool].description}\n")
        except KeyError:
            continue

    if state == "edit" and task.hints_text != "":
        prompt.append("\nHints:\n")
        prompt.append(f"{task.hints_text}\n")

    if state == "explore":
        prompt.append("\nIMPORTANT: Once you have identified the file and line to fix, call finish_exploration() "
                      "immediately. Do not keep exploring.\n")
    elif state == "edit":
        prompt.append("\nIMPORTANT: Once you have made all edits, call finish_editing() immediately.\n")

    prompt.append("\nRules:\n")
    prompt.append("- Never assume file names, always explore first.\n")
    prompt.append("- Choose exactly ONE tool per response.\n")
    prompt.append("- Return ONLY valid JSON, no explanation, no markdown.\n")
    prompt.append("\nResponse format:\n")
    prompt.append('{"tool": "<tool_name>", "arguments": {"<arg>": "<value>"}}\n')
    prompt.append("\nExamples:\n")
    prompt.append('{"tool": "run_command", "arguments": {"command": "ls /testbed", "workdir": "/testbed"}}\n')
    prompt.append('{"tool": "tool_read_file", "arguments": {"filepath": "/testbed/django/core/paginator.py", '
                  '"start_line": "1", "end_line": "50"}}\n')

    return "\n".join(prompt)


def build_history(tool: str, observation: str) -> dict[str, Any]:
    '''
    This function builds a dictionnary of the current action and the output
    that the LLM choosed to execute.
    This will then be added to the prompt.
    '''
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
        if "=" in arg:
            name, value = arg.split("=", 1)
            result["action"]["args"].update({
                name.strip(): value.strip()
            })
    result.update({
        "observation": {"result": observation}
    })
    return result


def build_eval_script(script: str, file_path: str) -> None:
    '''
    This function builds the script {script} to evaluate the Task output
    and store's it into {file_path}.
    '''
    try:
        with open(file_path, "w") as file:
            file.write(script)
    except Exception:
        raise Exception("An error occured during the creation of the script.")


def agent_loop_swebench(tasks: SWEBenchTaskInput, model: str,
                        keys: list[str], client: OpenAI,
                        max_iteration: int, sandbox) -> SolutionOutput:
    '''
    This function is the main loop.
    It'll run as long as there is no success or the number of iteration is lower
    then {max_iteration}.

    === LOOP ===

    A single iteration work as follow:
        The prompt is build and given to the LLM.
        From the LLM's answer, we extract the code he gave.
        (if it is not return as a ToolCall object, we continue into the next iteration.)
        Then, the code is executed into the sandbox.
        If the LLM asked get_patch() and this function return something, we assume he fixed
        the problem, the loop is stopped.
        If not, we use build_history() to expend the LLM's actions history
        and another iteration takes place.

        Upon completion (fail or success),
        we fill a SolutionOutput object and return it.
    '''
    agent_phase = Phases()
    key_index = 0
    metrics = []
    history = []
    message = ""
    success = False
    patch = ""
    iteration = 0
    tools = load_tools()
    build_eval_script(tasks.eval_script, "./script.sh")
    while iteration < max_iteration and success is False:
        print(f"Iteration {iteration + 1}/{max_iteration}, phase: {agent_phase.phase}")
        available_func = agent_phase.get_possible_func()
        if agent_phase.phase == "explore" and iteration > 10:
            agent_phase.phase = "edit"
            print("Forcing phase change to edit after 10 iterations")
        iteration += 1
        start = time.time()
        try:
            tool_call = ""
            tool_result = {}
            message = build_prompt(tasks, available_func, history, agent_phase.phase, tools)
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

                patch_result = sandbox.execute("tool_get_patch()")
                patch = patch_result.get("output", "")
                if patch:
                    success = True
                break
            else:
                tool_result = sandbox.execute(tool_call)
            if code.tool == "get_patch":
                if tool_result["output"].strip():
                    success = True
                    patch = tool_result.get("output", "")
                    metrics.append(StepMetrics(
                        step=len(metrics)+1,
                        input_tokens=answer.usage.prompt_tokens,
                        output_tokens=answer.usage.completion_tokens,
                        request_time_ms=request_time,
                        api_url=str(client.base_url),
                        model_name=model,
                        llm_output=raw_response,
                        sandbox_input=tool_call,
                        sandbox_output=tool_result.get("output", ""),
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
                        sandbox_output=tool_result.get("output", ""),
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
                sandbox_output=tool_result.get("output", ""),
                retries=iteration
            ))
        except RateLimitError:
            key_index = (key_index + 1) % len(keys)
            client = load_model(keys[key_index], str(client.base_url))
            time.sleep(5)
        except Exception:
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
        task_id=tasks.instance_id,
        benchmark="swebench",
        success=success,
        solution=patch,
        iterations=iteration,
        total_requests=len(metrics),
        total_input_tokens=sum(inputs.input_tokens for inputs in metrics),
        total_output_tokens=sum(inputs.output_tokens for inputs in metrics),
        total_time_seconds=sum(inputs.request_time_ms for inputs in metrics) / 1000,
        steps=metrics,
        system_prompt=message
    )


if __name__ == "__main__":
    task = load_task("../cache/SWE.json")
    keys = load_keys()
    client = load_model(keys[0], "https://openrouter.ai/api/v1")
    model = "poolside/laguna-xs-2.1:free"
    agent_loop_swebench(task, model, keys, client, 1, sandbox="")
