from hydra_zen import builds, store
from omegaconf import MISSING

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

store(WandBContextConf, group="ctx_manager", name="WandBContextConf")
