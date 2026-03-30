from hydra_zen import builds
from omegaconf import MISSING

from hydra_plugins.flyte_launcher_plugin._flyte_launcher import FlyteLauncher
from scaffold.conf import scaffold_store
from scaffold.flyte.launcher_conf import (
    ExecutionEnvironmentEnum,
    FlyteDockerImageConf,
    FlyteNotificationConf,
    FlyteWorkflowConf,
)

FlyteLauncherConf = builds(
    FlyteLauncher,
    execution_environment=ExecutionEnvironmentEnum.remote,
    endpoint="localhost:30081",
    build_images=True,
    fast_serialization=False,
    run=True,
    workflow=MISSING,
    notifications=[],
)

scaffold_store(FlyteDockerImageConf, group="scaffold/flyte_launcher", name="FlyteDockerImageConf")
scaffold_store(FlyteWorkflowConf, group="scaffold/flyte_launcher", name="FlyteWorkflowConf")
scaffold_store(FlyteNotificationConf, group="scaffold/flyte_launcher", name="FlyteNotificationConf")
