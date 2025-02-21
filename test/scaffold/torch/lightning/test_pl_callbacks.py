import pytest
from py._path.local import LocalPath
from torch.nn import Conv2d
from torch.nn.modules.module import Module
from torch.optim import Adam

from scaffold.data.artifact_manager.filesystem import FileSystemArtifactManager
from scaffold.integration_test.helpers import TmpCwd
from scaffold.torch.lightning.callbacks import LightningCheckpointer


def test_lightning_checkpointer(tmpdir: LocalPath) -> None:
    """Test LightningCheckpointer."""

    with TmpCwd(tmpdir):
        artifact_manager = FileSystemArtifactManager(url=str(tmpdir))

        checkpointer = LightningCheckpointer(
            artifact_manager=artifact_manager, target_afid=None, target_afid_best=None, only_log_current_best=False
        )

        # NOTE It is not ideal to test with a private method, but did not want to go down the route of
        # calling the `on_validation_epoch_end` and building dummy Trainer and LightningModule etc since
        # this seemed a little too much effort for this simple test.
        with pytest.raises(KeyError):
            checkpointer._get_avg_val_loss({"wrong_key": 0})
        assert checkpointer._get_avg_val_loss({"avg_val_loss": 123}) == 123

        model = Conv2d(3, 3, 3)
        optim = Adam(model.parameters())
        additional_key_value_pairs = {"current_epoch": 1, "loss": 0.1}

        afid = checkpointer._log_state_with_new_afid(model=model, optimizers=[optim], **additional_key_value_pairs)
        state = checkpointer.model_logger.retrieve_state_from_artifact(afid)

        checkpointer.model_logger.save_state(checkpointer.best_state_dir, model, [optim], **additional_key_value_pairs)
        state_2 = checkpointer.load_best_state()

        for d in [state, state_2]:
            assert isinstance(d["model"], Module)
            optim.load_state_dict(d["optimizer_state_dicts"][0])
            assert d["current_epoch"] == 1
            assert d["loss"] == 0.1
