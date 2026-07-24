from ..code_parser import extract_code, tool_call_reformer, ToolCall
from ..models.MBPP_models import StepMetrics, SolutionOutput, MBPPTaskInput
from ..models.sandbox_config import SandboxConfig
from ..sandbox.sandbox import Sandbox
from ..mcp.tools.execution_tools import run_tests
from ..agent_utils import respond
from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletion
from typing import Any, List
from token_count import TokenCount
import time
import json


def load_tasks(path) -> MBPPTaskInput:
    '''
    This function load the JSON file stored at {path} and
    return the content into a MBPPTaskInput object.
    '''
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


def get_visible_tokens(answer: ChatCompletion):
    '''
    This functions purpose is to calculate number of token output
    depending on if the LLM uses "reasoning_tokens" which are caculated
    in the output for certain model and if they're used, we use another
    package, token_count, and return the number of output token
    '''
    usage = answer.usage
    reasoning = 0
    if hasattr(usage, "completion_tokens_details"):
        details = usage.completion_tokens_details
        if details is not None:
            reasoning = details.reasoning_tokens or 0

    if reasoning:
        return usage.completion_tokens - reasoning

    return None


def build_script(solution_code: str, test_list: List[str],
                 test_imports: List[str]) -> str:
    """Build a Python test script combining solution code and assertions.

    Wraps each assertion in a try/except block to print PASS or FAIL.
    The resulting script is intended to be executed by the sandbox.

    Args:
        solution_code: Python source code of the function to test.
        test_list: List of assert statements (e.g. ["assert f(1) == 2"]).
        test_imports: List of module names to import at the top of the script.

    Returns:
        A Python script as a string ready for exec().
    """
    script = ""
    imp = ""
    tests = ""
    for impt in test_imports:
        imp += f"import {impt}\n"
    for tst in test_list:
        escaped = tst.replace("'", '"')
        block = "try:\n"
        block += f"    {tst}\n"
        block += f"    print('PASS: {escaped}')\n"
        block += "except AssertionError:\n"
        block += f"    print('FAIL: {escaped}')\n"
        tests += block
    script = imp + solution_code + "\n" + tests

    return script


async def agent_loop_mbpp(tasks: MBPPTaskInput, model: str,
                          keys: list[str], client: OpenAI,
                          max_iteration: int) -> SolutionOutput:
    '''
        This function is the main loop.
        It'll run as long as there is no success or the number of iteration is lower
        then {max_iteration}.

        === LOOP ===

        A single iteration work as follow:
            The prompt is build and given to the LLM.
            From the LLM's answer, we extract the code he gave.
            Then, the code is executed into the sandbox.

            Upon completion (fail or success),
            we fill a SolutionOutput object and return it.
    '''
    current_key = 0
    iteration = 0
    original_prompt = tasks.task_definition + \
        f" The function is declared as follow: {tasks.function_definition}" +\
        " Only give the function."
    key_usage = 0
    metrics = []
    success = False
    code = ""
    config = SandboxConfig()
    sandbox = Sandbox(config=config)
    prompt = original_prompt
    token_count = TokenCount()
    while iteration < max_iteration and not success:
        try:
            start = time.time()
            print("Thinking")
            answer = respond(client, model, prompt)
            request_time = round((time.time() - start) * 1000, 2)
            output_tokens = get_visible_tokens(answer)
            if output_tokens is None:
                output_tokens = token_count.num_tokens_from_string(
                    answer.choices[0].message.content
                )
            code = extract_code(answer.choices[0].message.content)
            if isinstance(code, ToolCall):
                code = tool_call_reformer(code)
            script = build_script(
                code,
                tasks.test_list,
                tasks.test_imports
            )
            print("Running thought code")
            output = await sandbox.execute(script)
            if output["success"] is False or "FAIL" in output["output"]:
                print("Me fail, am a dum dum")
                prompt = original_prompt + \
                    "\n\nHere is your previously generated " + \
                    f"function:\n{code}\n\n" + \
                    f"And here is the terminal output:\n{output['output']}"
            else:
                print("Success, mi muscles are getting biger")
                success = True
            iteration += 1
            key_usage += 1
            if key_usage > 2:
                current_key += 1
                client.api_key = keys[current_key % len(keys)]
                key_usage = 0
            metrics.append(StepMetrics(
                step=len(metrics) + 1,
                input_tokens=answer.usage.prompt_tokens,
                output_tokens=output_tokens,
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
            if key_usage > 2:
                current_key += 1
                client.api_key = keys[current_key % len(keys)]
                key_usage = 0
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
            iteration += 1
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
        total_time_seconds=sum(inputs.request_time_ms/1000
                               for inputs in metrics),
        steps=metrics,
        error=output["output"] if success is False else None
    )
    return solution
