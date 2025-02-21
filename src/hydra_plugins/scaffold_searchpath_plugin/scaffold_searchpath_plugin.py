"""Taken from https://github.com/facebookresearch/hydra/blob/main/examples/plugins/example_searchpath_plugin/hydra_plugins/example_searchpath_plugin/example_searchpath_plugin.py"""  # noqa: E501
from hydra.core.config_search_path import ConfigSearchPath
from hydra.plugins.search_path_plugin import SearchPathPlugin


class ScaffoldSearchPathPlugin(SearchPathPlugin):
    def manipulate_search_path(self, search_path: ConfigSearchPath) -> None:
        """Appends the search path for this plugin to the end of the hydra search path.
        This makes all config files inside the conf folder available by their group/name.
        """
        from scaffold.conf import register_all

        register_all()

        search_path.append(provider="scaffold", path="pkg://scaffold/conf")
