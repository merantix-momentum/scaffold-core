from __future__ import annotations

import abc
import logging
from abc import ABC
from contextlib import AbstractContextManager
from copy import deepcopy
from typing import Any, Generic, List, TYPE_CHECKING, TypeVar, Union

import hydra
import omegaconf
from omegaconf import OmegaConf

import scaffold
from scaffold.conf.scaffold.entrypoint import EntrypointConf
from scaffold.ctx_manager import combined_context, LoggingContext, TimerContext

if TYPE_CHECKING:
    from scaffold.hydra.config_helpers import StructuredConfig

logger = logging.getLogger(__name__)

ENTRYPOINT_CONFIG_TYPE = TypeVar("ENTRYPOINT_CONFIG_TYPE")


class Entrypoint(ABC, Generic[ENTRYPOINT_CONFIG_TYPE]):
    def __init__(
        self,
        config: ENTRYPOINT_CONFIG_TYPE,
        contexts: List[AbstractContextManager] = None,
    ) -> None:
        """
        Initialize entrypoint with a configuration of the specified type.
        Given context managers will be appended after the ones are found in the config.

        Args:
            config (EntrypointConf): The entrypoint configuration object of the specified type.
            contexts (List[AbstractContextManager]): Context managers that should be added next to the ones
                specified in the config.
        """
        # We check for correct type explicitly, because
        # specifying bounds for the generic type is not supported by vscode yet.
        assert (
            issubclass(OmegaConf.get_type(config), EntrypointConf)
            or OmegaConf.get_type(config) == EntrypointConf
            # if the config is a DictConfig, we can't check the type
            # this happens when composing the config through scaffold.hydra.compose()
            or OmegaConf.get_type(config) == dict
        ), "Config passed to the Entrypoint must be of class EntrypointConf."

        self.config: ENTRYPOINT_CONFIG_TYPE = deepcopy(config)
        self._initialize_contexts(contexts)
        logger.debug("Config:\n" + OmegaConf.to_yaml(self.config))

    def _initialize_contexts(self, contexts: List[AbstractContextManager] = None) -> None:
        """Initializes contexts from the config and adds them to the list of contexts."""
        cls_name = self.__class__.__name__
        logging_ctx = self._get_logging_context(cls_name=cls_name)
        timer_ctx = TimerContext(module_name=cls_name)

        self.contexts = [logging_ctx, timer_ctx]
        if "contexts" in self.config:
            initialized_contexts = [hydra.utils.instantiate(c) for c in self.config.contexts.values()]
            self.contexts.extend(initialized_contexts)
            logger.debug(f"Added contexts from config: {initialized_contexts}")
        if contexts is not None:
            self.contexts.extend(contexts)

    @classmethod
    def from_config_name_or_class(
        cls,
        config_name_or_class: Union[str, StructuredConfig],
        config_dir: str = None,
        overrides: List[str] = None,
        contexts: List[AbstractContextManager] = None,
    ) -> Entrypoint:
        """Temporarily initialized hydra, composes the config and initialized the entrypoint.

        Args:
            config_name_or_class (str): Name of the config file or EntrypointConf class.
            config_dir (str): Absolute path to the directory that should be added to the searchpath.
            overrides (List[str]): Hydra overrides that get applied during config composition.
            contexts (List[AbstractContextManager]): Contexts that should be added to the ones defined in the config.

        Return:
            Initialized Entrypoint instance.
        """
        _config = scaffold.hydra.compose(config_name_or_class, config_dir=config_dir, overrides=overrides)
        return cls(config=_config, contexts=contexts)

    def _get_logging_context(self, cls_name: str) -> LoggingContext:
        """Creates a logging context with the entrypoint class name as filename."""
        try:
            if self.config.logging.handlers.file.filename is None:
                self.config.logging.handlers.file.filename = f"{cls_name}.log"
        except omegaconf.errors.ConfigAttributeError:
            logger.debug(
                "Tried to overwrite the log filename, but couldn't find 'logging.handlers.file.filename' in the config!"
                "\nThis could be because the logging config is not provided."
                " It's recommended to either use '/scaffold/entrypoint/EntrypointConf@_here_' to apply the default"
                " schema and default values, or manually use '/scaffold/entrypoint/logging@logging: default' "
                "in your defaults list."
            )
        return LoggingContext(self.config.logging, verbose=self.config.verbose)

    @abc.abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Abstract function that has to be overwritten."""
        pass

    def __call__(self, *args, **kwargs) -> Any:
        """Wraps self.run() within initialized contexts. Arguments and keyword arguments will be passed to run()."""
        with combined_context(*self.contexts) as _:  # TODO extend when need access to context module
            output = self.run(*args, **kwargs)
        return output
