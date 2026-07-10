from .agent_utils.utils import (
    extract_code,
    tool_call_reformer,
    ToolCall,
    load_model,
    load_keys,
    respond,
)
from ..models.mbpp_models import StepMetrics, SolutionOutput, MBPPTaskInput
from ..models.sandbox_config import SandboxConfig
from ..sandbox.Sandbox_models import Sandbox
from ..mcp.tools.execution_tools import run_tests
from openai import OpenAI, RateLimitError
from typing import Any
import time
import json


def load_tasks(path) -> MBPPTaskInput:
    try:
        with open(path, "r") as file:
            task = json.load(file)
        return MBPPTaskInput(
            task_id=task["task_id"],
            task_definition=task["task_definition"],
            function_definition=task["function_definition"],
            test_imports=task["test_imports"],
            test_list=task["test_list"]
        )
    except (FileNotFoundError, PermissionError, Exception) as e:
        print(e)
        return []


def get_task_from_id(tasks: list[dict[str, Any]], id: int) -> dict[str, Any]:
    for task in tasks:
        if task["task_id"] == id:
            return task
    return {}


def agent_loop_mbpp(tasks: MBPPTaskInput, model: str,
                    keys: list[str], client: OpenAI,
                    max_iteration: int) -> SolutionOutput:
    current_key = 0
    iteration = 0
    original_prompt = tasks.task_definition + f" The function is declared as follow: {tasks.function_definition}"+" Only give the function."
    key_usage = 0
    metrics = []
    success = False
    code = ""
    config = SandboxConfig()
    sandbox = Sandbox(config=config)
    prompt = original_prompt
    while iteration < max_iteration and not success:
        try:
            start = time.time()
            answer = respond(client, model, prompt)
            request_time = round((time.time() - start) * 1000, 2)
            code = extract_code(answer.choices[0].message.content)
            if isinstance(code, ToolCall):
                code = tool_call_reformer(code)
            script = run_tests(
                code,
                tasks.test_list,
                tasks.test_imports
            )
            output = sandbox.execute(script)
            if output["success"] is False:
                iteration += 1
                prompt = original_prompt + \
                    "\n\nHere is your previously generated " + \
                    f"function:\n{script}\n\n" + \
                    f"And here is the terminal output:\n{output['output']}"
            else:
                success = True
            iteration += 1
            key_usage += 1
            if key_usage > 2:
                current_key += 1
                client.api_key=keys[current_key%len(keys)]
                key_usage = 0
            metrics.append(StepMetrics(
                step=len(metrics)+1,
                input_tokens=answer.usage.prompt_tokens,
                output_tokens=answer.usage.completion_tokens,
                request_time_ms=request_time,
                api_url=str(client.base_url),
                model_name=model,
                llm_output=answer.choices[0].message.content,
                sandbox_input=script,
                sandbox_output=output["output"],
                retries=iteration
            ))
        except (RateLimitError, Exception) as e:
            request_time = round((time.time() - start) * 1000, 2)
            print(e)
            key_usage += 1
            iteration += 1
            if key_usage > 2:
                current_key += 1
                client.api_key=keys[current_key%len(keys)]
                key_usage = 0
            metrics.append(StepMetrics(
                step=len(metrics)+1,
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
            if iteration >= max_iteration:
                break
            print("Retrying in 10 seconds...")
            time.sleep(10)
    solution = SolutionOutput(
        task_id=str(tasks.task_id),
        benchmark="mbpp",
        success=success,
        solution=code if code else "",
        system_prompt=prompt,
        iterations=iteration,
        total_requests=len(metrics),
        total_input_tokens=sum(inputs.input_tokens for inputs in metrics),
        total_output_tokens=sum(inputs.output_tokens for inputs in metrics),
        total_time_seconds=sum(inputs.request_time_ms for inputs in metrics),
        steps=metrics,
        error=output["output"] if success is False else None
    )
    return solution


if __name__ == "__main__":
    client = load_model()
    answered = False
    tasks = load_tasks("./moulinette/evaluations/mbpp/2026-03-01_13-12-36/282/task.json")
    if not tasks:
        print("Error when loading tasks")
        exit()
    keys = load_keys()
    agent_loop_mbpp(tasks, "google/gemma-4-26b-a4b-it:free", keys)
