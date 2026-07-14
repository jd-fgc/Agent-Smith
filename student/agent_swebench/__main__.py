import fire
from models.DockerSandbox import DockerSandbox
from agent_utils import load_keys, load_model
from agent_swebench.loop_swebench import agent_loop_swebench, load_task



class Agent_SWE:
    def run_agent(self, task_file: str, output: str,
                  model_name: str, provider_url: str) -> None:
        task = load_task(task_file)
        keys = load_keys()
        client = load_model(keys[0], provider_url)
        sandbox = DockerSandbox(
            task.docker_image
        )
        sandbox.start()


