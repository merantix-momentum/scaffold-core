import importlib
import logging
from contextlib import contextmanager
from typing import Callable, Dict, Generator, List, Set, Tuple, Union

from flytekit.configuration import (
    Config,
    FastSerializationSettings,
    Image,
    ImageConfig,
    PlatformConfig,
    SerializationSettings,
)
from flytekit.core.base_task import PythonTask
from flytekit.core.condition import BranchNode
from flytekit.core.node import Node
from flytekit.core.workflow import WorkflowBase
from flytekit.remote.remote import FlyteRemote

logger = logging.getLogger(__name__)


def mxm_register(nodes: List[Union[PythonTask, WorkflowBase]]) -> Callable:
    """
    Wrapper for both functions and workflows to declare additional flyte components for registration.
    This should go outside the flyte decorators (task, dynamic, workflow etc.)

    Args:
        nodes (List[Union[PythonTask, WorkflowBase]]): A list of tasks and workflows to be registered

    Returns:
        Union[PythonTask, WorkflowBase]: The original workflow
    """

    def decorator(func: Callable) -> Callable:
        assert isinstance(func, PythonTask) or isinstance(
            func, WorkflowBase
        ), f"Can only annotate Flyte entities not {type(func)}"
        func.mxm_nodes = nodes
        return func

    return decorator


def identify_main_workflow(module_name: str) -> Tuple[WorkflowBase, List[Union[PythonTask, WorkflowBase]]]:
    """
    Identify the main Flyte workflow and its subcomponents in a python module.

    Top-level workflows are all workflows defined in the same module as hydra.main.
    The main workflow is the only top-level workflow which is not used in any other top-level workflow - it is assumed,
    that exactly one such workflow exists.
    The required flyte components that also need to be registered are identified by recursively descending through
    the workflow's node tree.

    Note: The main workflow is not contained in the returned list itself.

    Args:
        module_name (str): the python module

    Returns:
        Tuple[WorkflowBase, List[Union[PythonTask, WorkflowBase]]]:
            The main workflow and a list of contained flyte entities to be registered

    Raises:
        ValueError: If the module does not contain exactly one workflow.
    """
    module = importlib.import_module(module_name)
    workflows_to_nodes: Dict[WorkflowBase, Set[Union[PythonTask, WorkflowBase]]] = dict(
        (getattr(module, attr), []) for attr in dir(module) if isinstance(getattr(module, attr), WorkflowBase)
    )

    sub_workflows = set()
    for wf in workflows_to_nodes.keys():
        if wf not in sub_workflows:
            wf_children = [node.flyte_entity for node in wf.nodes]
            if hasattr(wf, "mxm_nodes"):
                wf_children += wf.mxm_nodes
            entities = extract_flyte_entities(set(wf_children), set())
            sub_workflows.update([entity for entity in entities if isinstance(entity, WorkflowBase)])
            workflows_to_nodes[wf] = entities

    main_workflows = list(set(workflows_to_nodes.keys()).difference(sub_workflows))
    assert len(main_workflows) == 1, (
        "Can only register one main workflow. Please be more conservative with workflow "
        "imports and ensure that no unused sub-workflows are defined or imported."
    )
    return main_workflows[0], list(workflows_to_nodes[main_workflows[0]])


def extract_flyte_entities(
    new_entities: Set[Union[PythonTask, WorkflowBase]], entities: Set[Union[PythonTask, WorkflowBase]]
) -> Set[Union[PythonTask, WorkflowBase]]:
    """
    Recursively extract sub-workflows and other flyte entities from a list of nodes or flyte entities.

    Args:
        new_entities (List[Union[PythonTask, WorkflowBase]]): flyte entities used to recursively extract sub-entities
        entities (Set[Union[PythonTask, WorkflowBase]]): already discovered entities not to recurse on

    Returns:
        Set[Union[PythonTask, WorkflowBase]]:
            A set of all children nodes to be registered (including subworkflows).
    """
    # prepare next descend through recursion
    children: Set[Union[Node, PythonTask, WorkflowBase]] = set()
    for entity in new_entities:
        if isinstance(entity, PythonTask):
            # standard tasks, map-tasks and dynamic workflows - add to entities
            entities.add(entity)
        elif isinstance(entity, WorkflowBase):
            # standard workflows - add entity to entities list and add child nodes to next recursion
            children.update(set([node.flyte_entity for node in entity.nodes]))
            entities.add(entity)
        elif isinstance(entity, BranchNode):  # Flyte conditional statements
            clauses = [entity._ifelse_block._case._then_node, entity._ifelse_block._else_node]
            if entity._ifelse_block.other is not None:
                clauses.extend([elif_node._then_node for elif_node in entity._ifelse_block.other])
            children.update(set([clause.flyte_entity for clause in clauses]))
        else:
            raise ValueError(
                f"Encountered Flyte entity of type {type(entity)} during registration. This type is not known and will "
                f"not be registered."
            )

        if hasattr(entity, "mxm_nodes"):
            children.update(entity.mxm_nodes)

    # filter already discovered entities to avoid infinite regress
    children = children.difference(entities)

    if len(children) == 0:
        return entities
    else:
        return extract_flyte_entities(children, entities)


@contextmanager
def temp_flyte_remote(
    project: str,
    domain: str,
    endpoint: str,
) -> Generator[Tuple[FlyteRemote, SerializationSettings], None, None]:
    """
    Create a flyte remote object with a temporary proxy into the kubernetes cluster.

    Args:
        project (str): the flyte project
        domain (str): one of `development`, `staging` or `production`
        service (str): kubernetes service name to port-forward.
        port (int): port of the service in the cluster to port-forward
        namespace (str): namespace of the service in the cluster that is being port-forwarded
        local_port (int): the desired local port to forward to, will use a random port if the desired port is in use
        venv_root (str): python virtual environment root for the flyte image, flyte default is used when not specified.

    Yields:
        Generator[FlyteRemote, None, None]:
            FlyteRemote: flyte remote object to make register calls.
    """
    remote = FlyteRemote(
        default_project=project,
        default_domain=domain,
        config=Config(platform=PlatformConfig(endpoint=endpoint, insecure=True)),
    )

    yield remote


def get_serialization_settings(
    default_image: str,
    extra_images: Dict[str, str],
    fast_serialization_settings: FastSerializationSettings,
    project: str,
    domain: str,
) -> SerializationSettings:
    """
    Create flyte serialization settings for registering tasks and workflows.

    Args:
        default_image (str): the tag of the image used by default by the flyte tasks
        extra_images (Dict[str, str]): a dictionary mapping the names of extra images to be used to the respective tags.
            The format is e.g. `{"spark": "eu.gcr.io/project_name/spark_image:tag"}`.
            In the flyte task decorator, the image is specified e.g. with
            `container_image="{{.images.spark.fqn}}:{{.images.default.version}}"`.
        fast_serialization_settings (FastSerializationSettings): Details of image injections in fast serialisation mode
        project (str): the flyte project
        domain (str): domain, normally one of `development`, `staging` or `production
    Returns:
        Flyte SerializationSettings for registering flyte entities.
    """
    extra_image_configs = []

    for label, image in extra_images.items():
        fqn, tag = image.rsplit(":", 1)
        extra_image_configs.append(Image(name=label, fqn=fqn, tag=tag))

    default_image_fqn, default_image_tag = default_image.rsplit(":", 1)
    default_serialization_settings = SerializationSettings(
        image_config=ImageConfig(
            default_image=Image(name="default", fqn=default_image_fqn, tag=default_image_tag),
            images=extra_image_configs,
        ),
        fast_serialization_settings=fast_serialization_settings,
        project=project,
        domain=domain,
    )

    return default_serialization_settings
