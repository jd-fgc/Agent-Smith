import docker
from docker.models.containers import Container
from typing import Any


class DockerSandbox:
    def __init__(self, image: str):
        self.image = image
        self.client = docker.from_env()
        self.container: Container | None = None

    def start(self):
        self.container = self.client.containers.run(
            image=self.image,
            command="sleep infinity",
            detach=True,
            tty=True,
            working_dir="/testbed"
        )

    def execute(self, command: str) -> dict[str, Any]:
        if self.container is None:
            raise RuntimeError("Sandbox not started")
        result = self.container.exec_run(
            cmd=command,
            workdir="/testbed"
        )
        return {
            "exit_code": result.exit_code,
            "output": result.output.decode("utf-8", errors="replace")
        }

    def stop(self) -> None:
        if self.container:
            self.container.remove(force=True)
            self.container = None

