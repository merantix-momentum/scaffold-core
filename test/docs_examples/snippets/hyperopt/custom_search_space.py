from optuna import Trial

from scaffold.flyte.hyperopt.optimisers.optuna_search_space import OptunaSearchSpace


class CustomSearchSpace(OptunaSearchSpace):
    def suggest_parameters(self, trial: Trial) -> None:
        """
        Generate parameter selection for a particular trial.

        This allows the implementation of conditional search spaces in which subconfigs are generated depending on the
        sampling outcome of particular indicators (e.g. model type).

        Check https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/002_configurations.html
        for different suggestion mechanisms.

        Additional trial-wise parameter variations that should not be part of the search space can be written into the
        trials user attribute "params" as a dictionary.

        Args:
            trial (optuna.Trial): The optuna trial to suggest parameters for.
        """
        trial.suggest_float("<parameter_name>", 0.0, 1.0)
        trial.set_user_attr("params", {"trainer.model_location": f"<path>/model_{trial.number}"})
