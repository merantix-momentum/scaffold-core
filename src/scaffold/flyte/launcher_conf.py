from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import List, Optional

try:
    from flytekit.models.core.execution import WorkflowExecutionPhase
except ImportError:
    # Fallback mirrors for WorkflowExecution.Phase (stable protobuf constants).
    class WorkflowExecutionPhase:  # type: ignore[no-redef]
        UNDEFINED = 0
        QUEUED = 1
        RUNNING = 2
        SUCCEEDING = 3
        SUCCEEDED = 4
        FAILING = 5
        FAILED = 6
        ABORTED = 7
        TIMED_OUT = 8
        ABORTING = 9


@unique
class FlyteDomainEnum(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


@unique
class FlyteNotificationEnum(str, Enum):
    email = "email"
    slack = "slack"


@unique
class FlyteWorkflowExecutionPhaseEnum(str, Enum):
    UNDEFINED = WorkflowExecutionPhase.UNDEFINED
    QUEUED = WorkflowExecutionPhase.QUEUED
    RUNNING = WorkflowExecutionPhase.RUNNING
    SUCCEEDING = WorkflowExecutionPhase.SUCCEEDING
    SUCCEEDED = WorkflowExecutionPhase.SUCCEEDED
    FAILING = WorkflowExecutionPhase.FAILING
    FAILED = WorkflowExecutionPhase.FAILED
    ABORTED = WorkflowExecutionPhase.ABORTED
    TIMED_OUT = WorkflowExecutionPhase.TIMED_OUT
    ABORTING = WorkflowExecutionPhase.ABORTING


@unique
class ExecutionEnvironmentEnum(str, Enum):
    local = "local"
    remote = "remote"


@dataclass
class FlyteDockerImageConf:
    base_image: str
    base_image_version: Optional[str]
    target_image: str
    target_image_version: Optional[str]
    dockerfile_path: str = "infrastructure/docker/Dockerfile"
    docker_context: str = "."
    buildargs: dict = field(default_factory=dict)
    secrets: Optional[List[str]] = None
    docker_kwargs: dict = field(default_factory=dict)
    flyte_image_name: str = "default"


@dataclass
class FlyteWorkflowConf:
    default_image: FlyteDockerImageConf
    extra_images: List[FlyteDockerImageConf] = field(default_factory=list)
    ignore: str = ".flyteignore"
    version: Optional[str] = None
    project: str = "default"
    domain: FlyteDomainEnum = FlyteDomainEnum.development
    cron_schedule: Optional[str] = None


@dataclass
class FlyteNotificationConf:
    type: FlyteNotificationEnum = FlyteNotificationEnum.email
    phases: List[FlyteWorkflowExecutionPhaseEnum] = field(default_factory=list)
    recipients: List[str] = field(default_factory=list)
