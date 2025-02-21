.. _example1:

Trainer entrypoint example using hydra
--------------------------------------------------------------------

Here we see an example that uses the following scaffold subpackages:

- :ref:`entrypoints`
- :ref:`hydra`

Using scaffold, we are able to get a configurable training running in the cloud without a lot of project specific code:


.. code-block:: python

    from typing import Any, Optional

    import hydra
    from pytorch_lightning import Trainer

    from scaffold.conf.scaffold.entrypoint import EntrypointConf
    from scaffold.entrypoints.entrypoint import Entrypoint
    from scaffold.hydra.config_helpers import structured_config
    from scaffold.ctx_manager import WandBContext


    @structured_config
    class SimpleAEConf:
        _target_: str = "lightning_module.EncoderModule"
        use_mnist: bool = False
        in_channels: int = 24
        learning_rate: float = 0.0001
        seq_length: int = 600
        z_dim: int = 2


    @structured_config
    class AETraining(EntrypointConf):
        module: SimpleAEConf = SimpleAEConf()
        max_epochs: int = 4
        exp_name: str = "trainings"
        run_id: Optional[str] = None


    class TrainerEntrypoint(Entrypoint[AETraining]):
        def run(self, *args, **kwargs) -> Any:
            with WandBContext():
              model = hydra.utils.instantiate(self.config.module)
              trainer = Trainer()
              trainer.fit(model=model.float())
              # can log to wandb as necessary here


    @hydra.main(config_path="../conf", config_name="ae_trainer")
    def main(cfg: AETraining):
        TrainerEntrypoint(cfg, callbacks=[])()


    if __name__ == "__main__":
        main(None)


With the following yaml file ``ae_trainer.yaml`` in the ``../conf`` directory relative to the above script, we can then directly run the script with python.

.. code-block:: yaml

    defaults:
      - AETraining  # sets the schema, which got registered by scaffolds structured_config

    exp_name: 'mnist'
    module:  # follows the SimpleAEConf schema
      use_mnist: True
      in_channels: 28
      learning_rate: 0.0001
      seq_length: 28

    verbose: [scaffold] # Puts python logging for scaffold to DEBUG. Can also be set to True

    hydra:
      output_subdir: # prevents hydra from creating a .hydra dir
      run:
        dir: . # prevents hydra from changing directory


We define a schema for the config using the ``structured_config`` decorator from scaffold, which extends the ``dataclass`` decorator but already registers the schema (config name is the same as the class name) with hydra.
Note that the top-level config node ``AETraining`` inherits from scaffolds ``EntrypointConf``, to add the ``logging`` and ``verbose`` attribute, which can be used to configure python logging.


The actual Entrypoint ``TrainerEntrypoint`` does not seem to do a lot except instantiating a PytorchLightning Trainer Class using hydra then training it,
but because of the inheritance from scaffolds ``Entrypoint`` class we get the following functionality for free:

- Loggers get configured as specified in the config file (not shown here).
- The execution time of our ``run`` method gets logged.

Additionally, note that entrypoint definition takes generic type parameters, which allows us to specify the config type, which is then used to type hint the structured config object in the entrypoint methods.
