import argparse
from student.models.DockerSandbox import DockerSandbox
from student.agent_utils import load_keys, load_model
from student.agent_swebench.loop_swebench import agent_loop_swebench, load_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--provider-url", required=True)
    args = parser.parse_args()

    print("Loading task...")
    task = load_task(args.task_file)
    print(f"Task loaded: {task.instance_id}")

    keys = load_keys()
    print(f"Keys loaded: {len([k for k in keys if k])} keys")

    client = load_model(keys[0], args.provider_url)
    print("Model loaded")

    print(f"Starting Docker container: {task.docker_image}")
    sandbox = DockerSandbox(task.docker_image)

    result = None
    try:
        sandbox.start()
        print("Container started, running agent...")
        result = agent_loop_swebench(
            task, args.model_name, keys, client, 30, sandbox
        )
    except Exception as e:
        print(f"Agent error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sandbox.stop()
        print("Container stopped")

    if result is not None:
        with open(args.output, "w") as f:
            f.write(result.model_dump_json(indent=2))
        print(f"Solution written to {args.output}")
    else:
        print("Agent loop returned None")


if __name__ == "__main__":
    main()
