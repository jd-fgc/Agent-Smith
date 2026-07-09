from agent_utils import load_keys, load_model
from agent_mbpp.loop_mbpp import load_tasks, agent_loop_mbpp
from models.MBPP_models import SolutionOutput
from typing import Any
import fire
import json


class Agent_MBPP:
    def run_agent(self, task_file: str, output: str,
                  model_name: str, provider_url: str,
                  max_iteration: int) -> None:
        keys = load_keys()
        if not keys:
            raise Exception("An error occured upon loading API keys.")
        client = load_model(keys[0], provider_url)
        task = load_tasks(task_file)
        if not task:
            raise Exception("An error occured upon loading task.")
        solution = agent_loop_mbpp(task, model_name, keys,
                                   client, max_iteration)
        with open(output, "w") as file:
            json.dump(convert_to_dict(solution), file, indent=4)


def convert_to_dict(solution: SolutionOutput) -> dict[str, Any]:
    output = dict(solution)
    steps = []
    for metric in solution.steps:
        steps.append(dict(metric))
    output["steps"] = steps
    return output
        

def main():
    try:
        agent = Agent_MBPP()
        fire.Fire(agent)
    except Exception as e:
        print(e)
        return


if __name__ == "__main__":
    main()
