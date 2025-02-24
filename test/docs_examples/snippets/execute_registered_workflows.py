from scaffold.flyte.flyte_utils import FlyteRemoteHelper

# when registering a workflow, flyte launcher will log the launchplan names at the end. Can also be found in UI
launchplan_name = "hydra_workflow.scaffold.main_hydra_flyte_extra_inputs.pipeline_production_0"

# using overrides is bit more convenient than changing the cfg argument, especially if configs become huge
overrides = {"strip_string": False}
string_to_be_processed = " please clean Me UP"

# execute the workflow that was registered by flyte launcher before
FlyteRemoteHelper(domain="production", admin_endpoint="flyteadmin.flyte.svc.cluster.local:81").execute_flyte_launchplan(
    launchplan_name, {"overrides": overrides, "data_string": string_to_be_processed}
)
