import typing as t

from flytekit.configuration import Config as FlyteConfig
from flytekit.remote import FlyteLaunchPlan, FlyteRemote


class FlyteRemoteHelper:
    def __init__(self, domain: str, admin_endpoint: str, insecure: bool = True, project: str = "default"):
        """
        Instantiates a flyteRemote object internally.

        Args:
            domain: In which flyte domain we operate, usually one of staging, development, production
            project: flyte project to operate in. Defaults to 'default'
            admin_endpoint: Connection to Flyte admin. Usually 'flyteadmin.flyte.svc.cluster.local:81' within the
                cluster, or localhost:30081 if forwarded
                via `kubectl port-forward --address 0.0.0.0 svc/flyteadmin 30081:81 -n flyte`
            insecure: If true, no SSL is used for the connection. If the connection is just within cluster or through
                a port-forward done by kubectl it can be set to True.
        """
        self.flyte_remote = FlyteRemote(
            config=FlyteConfig.for_endpoint(endpoint=admin_endpoint, insecure=insecure),
            default_domain=domain,
            default_project=project,
        )

    def fetch_launchplan(self, launchplan_name: str) -> FlyteLaunchPlan:
        """Fetches a registered, remote launchplan by name."""
        return self.flyte_remote.fetch_launch_plan(name=launchplan_name)

    def execute_flyte_launchplan(self, launchplan_name: str, input_args: dict, wait: bool = False) -> t.Any:
        """
        Fetches a launchplan using the connection from init and executes it with the given arguments.

        Args:
            launchplan_name: Name of the launchplan.
                Note that launchplans registered via scaffold usually have a _0 suffix
            input_args: A dictionary mapping from worklow input arguments as string keys to the values with which the
                workflow gets executed. All arguments that do not have a default argument in the launchplan need to be
                provided. Note that cfg does have a default argument in launchplans registered using the flyte launcher.
            wait: If true, this function will only return once the workflow finishes. Defaults to false.

        Returns:
            something
        """
        lp = self.fetch_launchplan(launchplan_name)
        r = self.flyte_remote.execute(lp, inputs=input_args, wait=wait)
        return r
