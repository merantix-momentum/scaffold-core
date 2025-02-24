import os
import time

from flatten_dict import flatten

from scaffold.system_monitor import AbstractBackendSender, StatsDict, SystemMonitor


class MockBackendSender(AbstractBackendSender):
    def publish(self, event: StatsDict, **kwargs) -> None:
        """Dummy method for tests"""
        pass


def test_system_monitor(gpu_mock: object) -> None:
    """Ensure all data GPU data is logged correctly"""

    expected_keys = [
        "gpu.0.gpu",
        "gpu.0.memory",
        "gpu.0.memoryAllocated",
        "gpu.0.temp",
        "gpu.0.powerWatts",
        "gpu.0.powerPercent",
        "gpu.1.gpu",
        "gpu.1.memory",
        "gpu.1.memoryAllocated",
        "gpu.1.temp",
        "cpu",
        "memory",
        "network/sent",
        "network/recv",
        "disk",
        "proc.memory.availableMB",
        "proc.memory.rssMB",
        "proc.memory.percent",
        "proc.cpu.threads",
    ]

    monitor = SystemMonitor(os.getpid(), MockBackendSender())

    monitor.start()
    time.sleep(4)  # Sleep for a bit to gather some stats
    flat_stats = flatten(monitor.sampler, reducer="path")
    monitor.shutdown()

    # Ensure monitor thread is shut down before asserting anything
    # Otherwise pytest fails and creates a zombie thread and doesn't exit
    assert set(flat_stats.keys()) == set(expected_keys)
    for v in flat_stats.values():
        assert v >= 0.0


def test_system_monitor_with_gpu_by_us(gpu_mock: object, mocker: object) -> None:
    """Ensure all data GPU data is logged correctly when GPU in use by us"""

    expected_keys = [
        "rank0.gpu.0.gpu",
        "rank0.gpu.0.memory",
        "rank0.gpu.0.memoryAllocated",
        "rank0.gpu.0.temp",
        "rank0.gpu.0.powerWatts",
        "rank0.gpu.0.powerPercent",
        "rank0.gpu.1.gpu",
        "rank0.gpu.1.memory",
        "rank0.gpu.1.memoryAllocated",
        "rank0.gpu.1.temp",
        "rank0.cpu",
        "rank0.memory",
        "rank0.network/sent",
        "rank0.network/recv",
        "rank0.disk",
        "rank0.proc.memory.availableMB",
        "rank0.proc.memory.rssMB",
        "rank0.proc.memory.percent",
        "rank0.proc.cpu.threads",
    ]

    monitor = SystemMonitor(os.getpid(), MockBackendSender(), rank=0)

    monitor.start()
    time.sleep(4)  # Sleep for a bit to gather some stats
    flat_stats = flatten(monitor.sampler, reducer="path")
    monitor.shutdown()

    # Ensure monitor thread is shut down before asserting anything
    # Otherwise pytest fails and creates a zombie thread and doesn't exit
    assert set(flat_stats.keys()) == set(expected_keys)
    for v in flat_stats.values():
        assert v >= 0.0
