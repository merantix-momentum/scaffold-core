import typing as t
from test.conftest import MockContextManager

import pytest

from scaffold.ctx_manager import combined_context, TimerContext, WandBContext

WandB = WandBContext(base_url="wand.com", project="mock_project")


def test_wandbctx_enter_exit_run(mock_wandb: t.Any) -> None:
    """Test that entering the context manager starts and ends a WandB run."""
    mock_wandb.run = None  # Simulate that there's no existing run
    mock_wandb.init.assert_not_called()  # Verify that no run was started before entering the context
    with WandB as _:
        mock_wandb.init.assert_called_once()  # Verify run was started
        mock_wandb.finish.assert_not_called()  # Verify that the run didn't finish before exiting the context
    mock_wandb.finish.assert_called_once()  # Verify that the run finished after exiting the context
    assert mock_wandb.finish.call_args.kwargs["exit_code"] == 0  # Verify that the run finished with exit_code=0


def test_wandbctx_exit_with_exception(mock_wandb: t.Any) -> None:
    """Test that the WandB run finishes with exit_code=1 when an exception is raised within the context."""

    wandb_ctx = WandB
    with pytest.raises(Exception):  # Use the specific exception you expect
        with wandb_ctx as _:
            raise Exception("This is a test exception")

    assert mock_wandb.finish.call_args.kwargs["exit_code"] == 1


def test_timer_ctx_manager(mock_logger) -> None:
    """Test that the TimerContext logs the time taken to execute the block."""
    import re
    from time import sleep

    module_name = "test_timer_ctx_manager"
    sleep_time = 0.5

    with TimerContext(module_name) as _:
        sleep(sleep_time)

    # Last call should be the execution time log
    logged_text = mock_logger.info.call_args.args[-1]

    # parse out the only number from the log message with a regex
    exec_time = float(re.search(r"\d+\.\d+", logged_text).group())

    # Assert that the time taken is within 0.1s of the expected time
    assert exec_time >= sleep_time < sleep_time + 0.1


def test_all_context_managers_are_entered() -> None:
    """
    Since `assert_called_once` does not assert anything about when the call was made,
    this test inherently checks that both context managers are entered.
    """
    mock1 = MockContextManager()
    mock2 = MockContextManager()

    with combined_context(mock1, mock2):
        mock1.enter.assert_called_once()
        mock2.enter.assert_called_once()


def test_exception_is_propagated() -> None:
    """Test that an exception raised within the combined context is propagated."""
    mock1 = MockContextManager()
    mock2 = MockContextManager()

    with pytest.raises(Exception):
        with combined_context(mock1, mock2):
            raise Exception("Testing exception propagation")

    mock1.exit.assert_called_once()
    mock2.exit.assert_called_once()
