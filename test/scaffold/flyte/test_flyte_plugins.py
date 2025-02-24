from flytekit.core.base_task import PythonTask
from flytekit.extend import TypeEngine
from omegaconf import DictConfig

from scaffold.flyte.core import identify_main_workflow


def test_registration_set_plugins() -> None:
    """Test identification of correct tasks and workflows for torch and spark plugins"""
    wf, entities = identify_main_workflow("dummy_modules.plugin_module")
    assert len(entities) == 1, "There should be exactly one task in the test workflow to register"
    entity_names = [ent.name for ent in entities]

    assert "dummy_modules.plugin_module.hello_torch" in entity_names, "Missing torch task"

    task_nodes = [node for node in wf.nodes if isinstance(node.flyte_entity, PythonTask)]

    for node in task_nodes:
        assert node.flyte_entity in entities, "Tasks used by the workflow should be extracted"


def test_flytekit_hydra_plugin() -> None:
    """Check if hydra plugin is successfully registered upon import."""
    assert TypeEngine.get_transformer(DictConfig), "Data Transformer should be available for 'DictConfig'"
