from hydra_zen import ZenStore

from hydra_plugins.flyte_launcher_plugin._flyte_launcher import FlyteDockerImageConfig, FlyteWorkflowConfig
from scaffold.conf.scaffold.flyte_launcher import LauncherConf

launcher_store = ZenStore(name="launcher")

launcher_store(
    LauncherConf(
        workflow=FlyteWorkflowConfig(
            default_image=FlyteDockerImageConfig(
                base_image="<registry>/<project>/base",
                base_image_version="latest",
                target_image="<registry>/<project>/workflow",
                dockerfile_path="Dockerfile.flyte",
            )
        )
    ),
    name="flyte",
    group="hydra/launcher",
)
