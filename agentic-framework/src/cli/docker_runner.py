"""Module containing docker runner functionality for the Enterprise Agent Framework."""

import subprocess


DOCKER_IMAGE = "enterprise-agent-framework:v2"


def run_docker():
    """Execute the run docker operation."""
    command = [
        "docker",
        "run",
        "-it",
        "--rm",
        DOCKER_IMAGE,
    ]

    try:
        subprocess.run(command, check=True)

    except FileNotFoundError:
        raise RuntimeError(
            "Docker is not installed or Docker Desktop is not running."
        )

    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Docker container failed with exit code {exc.returncode}."
        )