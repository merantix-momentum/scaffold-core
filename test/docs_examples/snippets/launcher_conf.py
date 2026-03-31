from hydra_zen import ZenStore

from hydra_plugins.flyte_launcher_plugin._flyte_launcher import FlyteDockerImageConf, FlyteWorkflowConf
from scaffold.conf.scaffold.flyte_launcher import FlyteLauncherConf

launcher_store = ZenStore(name="launcher")

launcher_store(
    FlyteLauncherConf(
        workflow=FlyteWorkflowConf(
            default_image=FlyteDockerImageConf(
                base_image="<registry>/<project>/base",
                base_image_version="latest",
                target_image="<registry>/<project>/workflow",
                dockerfile_path="Dockerfile.flyte",
            )
        ),
    ),
    name="flyte",
    group="hydra/launcher",
)
