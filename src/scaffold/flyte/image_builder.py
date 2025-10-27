import logging
import operator
import os
import subprocess
import threading
from functools import reduce
from pathlib import Path
from typing import Dict, List, Optional

import docker

logger = logging.getLogger(__name__)


BUILD_TIMEOUT = 20 * 60  # 20 Mins for now


def early_termination(process, msg):
    """Terminate a process early, raise with the provided error message"""
    process.kill()
    raise Exception(msg)


def build_image(
    dockerfile: Path,
    workdir_path: Path,
    image_repo: str,
    image_tag: str,
    buildargs: Dict[str, str],
    secrets: Optional[List[str]] = None,
    push_image: bool = False,
    **kwargs: Dict[str, str],
) -> str:
    """Build docker image with local docker engine.

    Args:
        dockerfile (Path): path to the dockerfile
        workdir_path (Path): path to the working directory/docker context
        image_repo (str): fqn of the image repository. e.g eu.gcr.io/<proj_name>/<repo>
        image_tag (str): tag of the image. e.g <commit-hash>-dev
    Kwargs:
        buildargs (Dict[str,str]): Build args for docker build command
        secrets (List[str]): List of secret names to be used in the build
            Example, to mount google credentials from the host machine to the build context,
            you can pass `secrets=["id=gcp-cred,src=<path-to-creds-file>"]`
        push_image (bool, optional): flag to push the image to remote repo. Defaults to False.
        kwargs (Dict[str,str]): Additional arguments for docker build CLI call
    Returns:
        str: fqn:tag of the image

    """
    if image_repo[-1] == "/":
        raise ValueError("Image repo string should not end with '/'")
    docker_client = docker.from_env(timeout=BUILD_TIMEOUT)
    full_image_name = f"{image_repo}:{image_tag}"

    msg = f"Build image `{full_image_name}` with Dockerfile `{dockerfile}` and context `{workdir_path}`.\n"
    for key, val in buildargs.items():
        msg += f"Use ARG {key} `{val}`.\n"
    logger.info(msg)

    # Overwrite default values if they are not provided
    timeout = kwargs.pop("timeout", BUILD_TIMEOUT)
    if isinstance(timeout, str):
        timeout = int(timeout)

    # Use cli call to take advantage of BUILDKIT features
    os.environ["DOCKER_BUILDKIT"] = "1"

    docker_build_command = ["docker", "build", "-f", dockerfile, "--tag", full_image_name, "--progress=plain"]
    for key, val in kwargs.items():
        docker_build_command.extend([f"--{key}={val}"])
    for key, val in buildargs.items():
        docker_build_command.extend(["--build-arg", f"{key}={val}"])
    if kwargs.pop("pull", True):
        docker_build_command.append("--pull")
    if secrets:
        for secret in secrets:
            docker_build_command.append(f"--secret {secret}")

    docker_build_command.append(f"{workdir_path}")

    try:
        process = subprocess.Popen(
            " ".join(docker_build_command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        timer = threading.Timer(timeout, lambda: early_termination(process, f"Timeout reached after {timeout} sec"))
        timer.start()
        while True:
            line = process.stdout.readline()
            if not line:
                break
            logger.info("\t" + line.strip())
        timer.cancel()
    except subprocess.CalledProcessError as sub_err:
        logger.info(f"Docker command failed with return code: {sub_err.returncode} and msg\n{sub_err.stdout}")
        raise sub_err

    images = docker_client.api.images(name=image_repo)
    image_tags = [image.get("RepoTags", []) for image in images]
    if len(images) == 0 or full_image_name not in reduce(
        operator.concat, [tag for tag in image_tags if tag is not None]
    ):
        raise Exception(f"Build of image {full_image_name} not successful.")

    if push_image:
        logger.info(f"Pushing image `{full_image_name}`.")
        r = docker_client.images.push(full_image_name, stream=True, decode=True)
        for r_line in r:
            if "error" in r_line and r_line["error"]:
                raise docker.errors.APIError(r_line["error"])

    return full_image_name
