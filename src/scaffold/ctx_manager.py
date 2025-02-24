import logging
import os
import typing as t
from contextlib import AbstractContextManager, contextmanager, ExitStack

from omegaconf import DictConfig

from scaffold.hydra import compose

logger = logging.getLogger(__name__)


class LoggingContext(AbstractContextManager):
    """
    Context manager for configuring the logging system.
    It wraps the hydra's logging configuration and allows to specify verbosity level per module,
        see hydra documentation for more details: https://hydra.cc/docs/tutorials/basic/running_your_app/logging/

    Example usage:
    ```
        cfg = LoggingContext.DEFAULT_CONFIGURATION
        with LoggingContext(cfg) as log_context:
            logging.info("This message should be logged with the specified configuration.")
        logging.info("This error should be logged with default configuration.")
    ```
    """

    DEFAULT_CONFIGURATION = compose("scaffold/entrypoint/logging/default.yaml")
    SILENT_CONFIGURATION = compose("scaffold/entrypoint/logging/disabled.yaml")

    def __init__(
        self,
        log_config: DictConfig = DEFAULT_CONFIGURATION,
        verbose: t.Union[bool, str, t.Sequence[str]] = False,
    ):
        """
        Initialize the configuration of the logging context.
        """
        self.log_config = log_config
        self.verbose = verbose

    def __enter__(self):
        """
        Configure the logging system with the specified settings on entering the context.
        """
        from hydra.core.utils import configure_log

        configure_log(self.log_config, self.verbose)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context (and ideally restore previous logging configuration).
        """
        # TODO we want to reset the logging configuration here, but there is no way to access the previous configuration
        # for now we ignore this problem, but mind that even after the context is exited, the logging configuration will
        # still be the same as the one set in this context
        pass


class TimerContext(AbstractContextManager):
    def __init__(self, module_name: str = None):
        """
        Initialize the timer context manager.

        Args:
            module_name (str): Optional name of the module to be displayed in the log message.
        """
        self.start_time = None
        self.module_name = module_name

    @staticmethod
    def _get_time_str(t1: int, t2: int) -> str:
        """Returns a human-readable string representation of the time delta between t1 and t2."""
        delta_sec = t2 - t1
        m, s = divmod(delta_sec, 60)
        h, m = divmod(m, 60)
        res = ""
        if h > 0:
            res += f"{h:.0f} hours "
        if m > 0:
            res += f"{m:.0f} min "
        res += f"{s:.2f} sec"
        return res

    def __enter__(self):
        """
        Enter the timer context and start the timer
        """
        from time import perf_counter

        self.start_time = perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the timer context and log the time taken for execution
        """
        from time import perf_counter

        module_name = self.module_name or "Module"
        end_time = perf_counter()
        logger.info(f"{module_name} executed in {self._get_time_str(self.start_time, end_time)}")


class WandBContext(AbstractContextManager):
    """
    Context manager for configuring wandb, starting and exiting a wandb run.

    Example usage:
    ```
        with WandBContext(project="chameleon", entity="mg515") as wandb_ctx:
            # Do something with the WandB context
            wandb.log({"metric": 0.5})
    ```
    """

    def __init__(
        self,
        user: t.Optional[str] = None,
        base_url: str = None,
        entity: str = "mxm",
        run_id: t.Optional[str] = None,
        resume: bool = False,
        run_config: t.Optional[DictConfig] = None,
        **kwargs,
    ) -> None:
        """WandB Context that connects to our WandB instance, creates a WandB run and logs config to WandB instance.

        Args:
            user: Optional cloud username to retrieve wandb login secrets.
                  See Also: :func:`scaffold.wandb.helpers.wandb_environment_setup()`
            base_url: Base URL of WandB instance.
            entity: Name of the WandB entity.
            run_id: Flyte or WandB run ID.
            resume: Whether to resume previous run specified by run_id.
            run_config: Config passed to wandb init.
            **kwargs: Additional kwargs passed to wandb init. See https://docs.wandb.ai/ref/python/init.
        """

        from scaffold.wandb.helpers import wandb_environment_setup

        wandb_environment_setup(user)
        os.environ["WANDB_BASE_URL"] = base_url

        self.entity = entity
        self.kwargs = kwargs
        self.run = None
        self.run_config = run_config or DictConfig({})

        # If we are in flyte context and resume, we set the run_id to the current execution id
        self.run_id = os.environ.get("FLYTE_INTERNAL_EXECUTION_ID", run_id) if resume else run_id
        if resume and self.run_id is None:
            raise ValueError("Resume is set to True but run_id is None.")

        self.kwargs["resume"] = "allow" if resume else None
        logger.info(f"Run will be logged under wandb id: {self.run_id}")

    def __enter__(self):
        """Enters the context manager and starts a new WandB run."""
        import wandb

        if wandb.run is not None:
            logger.info(f"Using existing WandB run {self.run_id}.")
            self.run = wandb.run

        else:
            import flatten_dict

            config = flatten_dict.flatten(dict(self.run_config), reducer="dot")
            self.run = wandb.init(
                entity=self.entity,
                id=self.run_id,
                config=config,
                **self.kwargs,
            )
            logger.info(f"Started WandB run {self.run_id}.")
        return wandb

    def __exit__(
        self, exc_type: t.Optional[type], exc_val: t.Optional[Exception], exc_tb: t.Optional[t.Any]
    ) -> t.Optional[bool]:
        import wandb

        logger.info(f"Finishing WandB run {self.run_id}.")
        wandb.finish(exit_code=1 if exc_type is not None else 0)


@contextmanager
def combined_context(*contexts: t.List[AbstractContextManager]):
    """
    Combine multiple context managers into a stack, since contexts should be exited in reverse order
    in which they are entered. If an exception occurred, this order matters, as any context manager
    could suppress the exception, at which point the remaining managers will not even get notified

    Example use case:

    ```
    with combined_context(LoggingContext(), WandBContext()) as (logger, wandb):
        ...
    ```
    """
    with ExitStack() as stack:
        yield [stack.enter_context(cls) for cls in contexts]
