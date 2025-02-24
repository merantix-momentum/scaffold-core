"""This module defines functions that should be importable for integration tests and unit tests as well.

We use a separate module from conftest.py to circumvent imports from conftest, since this name can be ambiguous
when multiple conftest.py exist (e.g. for unit and integration tests) in one run.
Not importing from conftest is a best practice described in the note here:
https://pytest.org/en/6.2.x/writing_plugins.html#conftest-py-local-per-directory-plugins

This means we only use conftest.py to define fixtures which will automatically be shared with the respective scope.
"""
import os
from collections import namedtuple
from contextlib import AbstractContextManager
from dataclasses import field
from types import TracebackType
from typing import Any, List, Optional, Type

import pynvml
from mockito import when

from scaffold.conf.scaffold.entrypoint import EntrypointConf
from scaffold.entrypoints.entrypoint import Entrypoint
from scaffold.hydra.config_helpers import structured_config

MB = 1024 * 1024


class TmpCwd(object):
    def __init__(self, tmpdir: str) -> None:
        """Jump to a different cwd within the with clause"""
        self.tmpdir = tmpdir

    def __enter__(self) -> "TmpCwd":
        """Saves current cwd and chdir to tmp cwd"""
        self._cwd_stack = os.getcwd()
        os.chdir(self.tmpdir)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Restores stored cwd"""
        os.chdir(self._cwd_stack)


@structured_config(group="my_project/schemas")
class ExampleEntrypointConf(EntrypointConf):
    defaults: List[Any] = field(
        default_factory=lambda: [
            "/scaffold/entrypoint/hydra_defaults@_global_",
            {"/scaffold/entrypoint/logging@logging": "default"},
        ]
    )
    greeting: str = "Hey"


class MyContext(AbstractContextManager):
    """Helper context manager for testing. It sets a flag True when active and False when it exits."""

    def __init__(self) -> None:
        """Context init"""
        self.ctx_active = None

    def __enter__(self) -> "MyContext":
        """Context enter"""
        self.ctx_active = True
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Context exit"""
        self.ctx_active = False


class MinimalExampleEntrypoint(Entrypoint[ExampleEntrypointConf]):
    def run(self, name: str) -> str:
        """Compile and return greeting."""
        return self.config.greeting + " " + name


def configure_mock(N: object = pynvml, scenario_nonexistent_pid: bool = False) -> None:
    """Define mock behaviour for pynvml and psutil.{Process,virtual_memory}.

    Functionality adopted from:
    https://github.com/wookayin/gpustat/blob/cab5f2465fe718619ba03bf59f5208909581ea60/gpustat/test_gpustat.py#L202
    """

    # without following patch, unhashable NVMLError makes unit test crash
    N.NVMLError.__hash__ = lambda _: 0
    assert issubclass(N.NVMLError, BaseException)

    when(N).nvmlInit().thenReturn()
    when(N).nvmlShutdown().thenReturn()
    when(N).nvmlSystemGetDriverVersion().thenReturn("415.27.mock")

    NUM_GPUS = 3
    mock_handles = ["mock-handle-%d" % i for i in range(3)]
    when(N).nvmlDeviceGetCount().thenReturn(NUM_GPUS)

    def _return_or_raise(v: Any) -> Any:
        """Return a callable for thenAnswer() to let exceptions re-raised."""

        def _callable(*args, **kwargs) -> Any:
            if isinstance(v, Exception):
                raise v
            return v

        return _callable

    for i in range(NUM_GPUS):
        handle = mock_handles[i]
        when(N).nvmlDeviceGetHandleByIndex(i).thenReturn(handle)
        when(N).nvmlDeviceGetIndex(handle).thenReturn(i)
        when(N).nvmlDeviceGetName(handle).thenReturn(("GeForce GTX TITAN %d" % i).encode())
        when(N).nvmlDeviceGetUUID(handle).thenReturn(
            {
                0: b"GPU-10fb0fbd-2696-43f3-467f-d280d906a107",
                1: b"GPU-d1df4664-bb44-189c-7ad0-ab86c8cb30e2",
                2: b"GPU-50205d95-57b6-f541-2bcb-86c09afed564",
            }[i]
        )

        when(N).nvmlDeviceGetTemperature(handle, N.NVML_TEMPERATURE_GPU).thenReturn([80, 36, 71][i])
        when(N).nvmlDeviceGetFanSpeed(handle).thenReturn([16, 53, 100][i])
        when(N).nvmlDeviceGetPowerUsage(handle).thenAnswer(
            _return_or_raise({0: 125000, 1: N.NVMLError_NotSupported(), 2: 250000}[i])
        )
        when(N).nvmlDeviceGetEnforcedPowerLimit(handle).thenAnswer(
            _return_or_raise({0: 250000, 1: 250000, 2: N.NVMLError_NotSupported()}[i])
        )

        mock_memory_t = namedtuple("Memory_t", ["total", "used"])
        when(N).nvmlDeviceGetMemoryInfo(handle).thenAnswer(
            _return_or_raise(
                {
                    0: mock_memory_t(total=12883853312, used=8000 * MB),
                    1: mock_memory_t(total=12781551616, used=9000 * MB),
                    2: mock_memory_t(total=12781551616, used=0),
                }[i]
            )
        )

        mock_utilization_t = namedtuple("Utilization_t", ["gpu", "memory"])
        when(N).nvmlDeviceGetUtilizationRates(handle).thenAnswer(
            _return_or_raise(
                {
                    0: mock_utilization_t(gpu=76, memory=0),
                    1: mock_utilization_t(gpu=0, memory=0),
                    2: N.NVMLError_NotSupported(),  # Not Supported
                }[i]
            )
        )

        when(N).nvmlDeviceGetEncoderUtilization(handle).thenAnswer(
            _return_or_raise(
                {
                    0: [88, 167000],  # [value, sample_rate]
                    1: [0, 167000],  # [value, sample_rate]
                    2: N.NVMLError_NotSupported(),  # Not Supported
                }[i]
            )
        )
        when(N).nvmlDeviceGetDecoderUtilization(handle).thenAnswer(
            _return_or_raise(
                {
                    0: [67, 167000],  # [value, sample_rate]
                    1: [0, 167000],  # [value, sample_rate]
                    2: N.NVMLError_NotSupported(),  # Not Supported
                }[i]
            )
        )

        # running process information: a bit annoying...
        mock_process_t = namedtuple("Process_t", ["pid", "usedGpuMemory"])

        if scenario_nonexistent_pid:
            mock_processes_gpu2_erratic = [
                mock_process_t(99999, 9999 * MB),
                mock_process_t(99995, 9995 * MB),
            ]
        else:
            mock_processes_gpu2_erratic = N.NVMLError_NotSupported()
        when(N).nvmlDeviceGetComputeRunningProcesses(handle).thenAnswer(
            _return_or_raise(
                {
                    0: [mock_process_t(48448, 4000 * MB), mock_process_t(153223, 4000 * MB)],
                    1: [mock_process_t(192453, 3000 * MB), mock_process_t(194826, 6000 * MB)],
                    2: mock_processes_gpu2_erratic,  # Not Supported or non-existent
                }[i]
            )
        )

        when(N).nvmlDeviceGetGraphicsRunningProcesses(handle).thenAnswer(
            _return_or_raise(
                {
                    0: [mock_process_t(48448, 4000 * MB)],
                    1: [],
                    2: N.NVMLError_NotSupported(),
                }[i]
            )
        )
