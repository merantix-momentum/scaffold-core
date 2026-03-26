from hydra_zen import builds, store
from omegaconf import MISSING

from hydra_plugins.flyte_launcher_plugin._flyte_launcher import (
    ExecutionEnvironmentEnum,
    FlyteDockerImageConfig,
    FlyteLauncher,
    FlyteNotificationConfig,
    FlyteWorkflowConfig,
)

GROUP = "hydra/launcher"

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

store(FlyteDockerImageConfig, group="scaffold/flyte_launcher", name="FlyteDockerImageConfig")
store(FlyteWorkflowConfig, group="scaffold/flyte_launcher", name="FlyteWorkflowConfig")
store(FlyteNotificationConfig, group="scaffold/flyte_launcher", name="FlyteNotificationConfig")
store(LauncherConf, group=GROUP, name="flyte")
