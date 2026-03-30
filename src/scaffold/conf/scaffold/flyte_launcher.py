from hydra_zen import builds
from omegaconf import MISSING

from hydra_plugins.flyte_launcher_plugin._flyte_launcher import (
    ExecutionEnvironmentEnum,
    FlyteDockerImageConfig,
    FlyteLauncher,
    FlyteNotificationConfig,
    FlyteWorkflowConfig,
)
from scaffold.conf import scaffold_store

LauncherConf = builds(
    FlyteLauncher,
    execution_environment=ExecutionEnvironmentEnum.remote,
    endpoint="localhost:30081",
    build_images=True,
    fast_serialization=False,
    run=True,
    workflow=MISSING,
    notifications=[],
)

scaffold_store(FlyteDockerImageConfig, group="scaffold/flyte_launcher", name="FlyteDockerImageConfig")
scaffold_store(FlyteWorkflowConfig, group="scaffold/flyte_launcher", name="FlyteWorkflowConfig")
scaffold_store(FlyteNotificationConfig, group="scaffold/flyte_launcher", name="FlyteNotificationConfig")
