from tempfile import TemporaryDirectory

from torch.nn import Conv2d
from torch.nn.modules.module import Module
from torch.optim import Adam

from scaffold.data.artifact_manager import ModelLogger
from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager


def test_model_logger_state() -> None:
    """Test Model Logger with state dict functionality."""
    with TemporaryDirectory() as tmp_store:
        artifact_manager = FileSystemArtifactManager(url=tmp_store)
        model_logger = ModelLogger(artifact_manager)

        model = Conv2d(3, 3, 3)
        optim = Adam(model.parameters())

        additional_key_value_pairs = {"epoch": 1, "loss": 0.1}
        # Log with new randomly generated afid
        afid = model_logger.log_state_to_artifact(
            afid="example_afid", model=model, optimizers=[optim], **additional_key_value_pairs
        )
        state = model_logger.retrieve_state_from_artifact(afid)

        assert isinstance(state["model"], Module)
        optim.load_state_dict(state["optimizer_state_dicts"][0])
        assert state["epoch"] == 1
        assert state["loss"] == 0.1
