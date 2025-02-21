import pytest

from scaffold.flyte.core import identify_main_workflow


def test_main_workflow_extract() -> None:
    """Test correct extraction of main workflow."""
    wf, _ = identify_main_workflow("dummy_modules.valid_module")
    assert wf.name == "dummy_modules.valid_module.main_wf", "Found the wrong workflow"
    with pytest.raises(AssertionError):
        identify_main_workflow("dummy_modules.invalid_module")


def test_registration_set() -> None:
    """Test identification of correct tasks and workflows across module imports for registry in the flyte cloud"""
    wf, entities = identify_main_workflow("dummy_modules.valid_module")
    entity_names = [ent.name for ent in entities]
    assert len(entities) == 4, "There should only be two task in the test workflow to register"
    assert "dummy_modules.sub_module.sub_task" in entity_names, "Missing sub-task"
    assert "dummy_modules.sub_sub_module.sub_sub_task" in entity_names, "Missing sub-sub-task"

    assert "dummy_modules.sub_module.sub_wf" in entity_names, "Missing sub-workflow"
    assert "dummy_modules.sub_sub_module.sub_sub_wf" in entity_names, "Missing sub-sub-workflow"


def test_extract_modules_no_workflow() -> None:
    """Check if workflow extraction fails for module containing no workflows."""

    with pytest.raises(AssertionError):
        identify_main_workflow(__name__)


def test_validate_registration_set() -> None:
    """Check if the extracted tasks are included in the workflow nodes."""

    main_wf, entities = identify_main_workflow("dummy_modules.flyte_entity_module")

    entity_names = [e.name for e in entities]

    assert "dummy_modules.flyte_entity_module.top_lvl_task" in entity_names, "Failed to discover simple task"
    assert (
        "dummy_modules.flyte_entity_module.decorator_task" in entity_names
    ), "Failed to discover task in mxm decorator"
    assert (
        "dummy_modules.flyte_entity_module.decorator_wf" in entity_names
    ), "Failed to discover workflow in mxm decorator"
    assert "dummy_modules.flyte_entity_module.dynamic_wf" in entity_names, "Failed to discover dynamic workflow"
    assert (
        "dummy_modules.flyte_entity_module.map_mapped_task_6b3bd0353da5de6e84d7982921ead2b3-arraynode" in entity_names
    ), "Failed to discover map-task"  # Flyte names mapped tasks as a combination of task name and hashed signature
    assert "dummy_modules.flyte_entity_module.if_task" in entity_names, "Failed to discover task in conditional if"
    assert "dummy_modules.flyte_entity_module.elif_task" in entity_names, "Failed to discover task in conditional elif"
    assert "dummy_modules.flyte_entity_module.else_task" in entity_names, "Failed to discover task in conditional else"

    assert "dummy_modules.flyte_entity_module.if_wf" in entity_names, "Failed to discover workflow in conditional if"
    assert (
        "dummy_modules.flyte_entity_module.elif_wf" in entity_names
    ), "Failed to discover workflow in conditional elif"
    assert (
        "dummy_modules.flyte_entity_module.else_wf" in entity_names
    ), "Failed to discover workflow in conditional else"
    assert (
        "dummy_modules.flyte_entity_module.dummy_task" in entity_names
    ), "Failed to discover subtask nested in conditional workflow"
