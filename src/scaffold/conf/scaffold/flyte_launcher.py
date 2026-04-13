from hydra_zen import builds
from omegaconf import MISSING

from hydra_plugins.flyte_launcher_plugin._flyte_launcher import FlyteLauncher
from scaffold.flyte.launcher_conf import FlyteDockerImageConf  # noqa: F401
from scaffold.flyte.launcher_conf import FlyteNotificationConf  # noqa: F401
from scaffold.flyte.launcher_conf import FlyteWorkflowConf  # noqa: F401
from scaffold.flyte.launcher_conf import ExecutionEnvironmentEnum

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
