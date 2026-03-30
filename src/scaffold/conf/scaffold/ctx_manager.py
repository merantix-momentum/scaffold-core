from hydra_zen import builds
from omegaconf import MISSING

from scaffold.conf import scaffold_store
from scaffold.ctx_manager import WandBContext

WandBContextConf = builds(
    WandBContext,
    base_url=MISSING,
    project=MISSING,
    entity="mxm",
    group=None,
    job_type=None,
    tags=None,
    name=None,
    notes=None,
    run_id=None,
    user=None,
    resume=False,
)

scaffold_store(WandBContextConf, group="ctx_manager", name="WandBContextConf")
