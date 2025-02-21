"""
This file is strongly informed by the design of WandB's client published under MIT license

A good overview and explanation of the different logged quantities can be found
at: https://lambdalabs.com/blog/weights-and-bias-gpu-cpu-utilization/
"""

import abc
import threading
import time
from typing import Dict, List, Optional

import psutil
import pynvml

GPUHandle = object
SamplerDict = Dict[str, List[float]]
StatsDict = Dict[str, float]


class AbstractBackendSender(metaclass=abc.ABCMeta):
    """
    Abstract interface that works in conjunction with the system monitor.
    Should be used to configure where the system metrics are being sent to.
    """

    @abc.abstractmethod
    def publish(self, event: StatsDict, **kwargs) -> None:
        """Implements sending `event` to the corresponding backend."""
        pass


class SystemMonitor(object):
    _pid: int
    gpu_count: int
    _thread: Optional[threading.Thread]
    sampler: StatsDict
    network_init: Optional[Dict]
    _backend_sender: AbstractBackendSender
    _sample_rate_seconds: int
    _rank_prefix: str
    _gpu_key: str

    """
    Important Note:
        Since psutil is giving us system level information and not pod level information
        it is tricky to get reliable and not redundant CPU info here.
        We basically rely on the assumption that our rank is running on its own node here.
        With kubernetes this could be not true in a lot of scenarios, for example when one rank
        only requests one GPU, but one node in the training pool has more than one GPU.
        In this case, psutil will give node information, which could be used by other processes.
        One solution for this could be, to only allow the same number of GPUs per node as a worker
        would request, so that every worker has to request a new node.

        For GPU this is less of a problem, if the worker requests any number of GPUs and those GPUs are not
        shared by other workers / pods. In this case, all GPUs allocated to our worker pod will be the
        only visible cuda devices, and the GPU stats can only be attributed to our worker process.
    """

    def __init__(
        self,
        pid: int,
        backend_sender: AbstractBackendSender,
        sample_rate_seconds: int = 2,
        rank: Optional[int] = None,
    ) -> None:
        """
        Initializes the SystemMonitor using the parent threads PID and a backend_sender that implements the
        logic to send the collectesd stats to the corresponding backend, e.g. CSV, Tensorboard, WandB.

        Args:
            pid (int): Process id of the parent process.
            backend_sender (AbstractBackendSender): Class that publishes the stats, e.g. to WandB.
            sample_rate_seconds (int): The rate of sampling system stats in seconds.
            rank (int): Rank of the current process. Only needed in a distributed setting.
        """
        try:
            pynvml.nvmlInit()
            self.gpu_count = pynvml.nvmlDeviceGetCount()
        except pynvml.NVMLError:
            self.gpu_count = 0

        self._pid = pid
        self._backend_sender = backend_sender
        self._sample_rate_seconds = sample_rate_seconds
        self._shutdown = False
        self._thread = None
        self.sampler = {}
        self._rank_prefix = f"rank{rank}." if rank is not None else ""
        self._gpu_key = (self._rank_prefix + "gpu.{}.{}").format

        if psutil:
            net = psutil.net_io_counters()
            self.network_init = {"sent": net.bytes_sent, "recv": net.bytes_recv}

    def start(self) -> None:
        """Starts the the monitor by launching a separate thread."""
        if self._thread is None:
            self._shutdown = False
            self._thread = threading.Thread(target=self._thread_body)
        if not self._thread.is_alive():
            self._thread.start()

    @property
    def proc(self) -> psutil.Process:
        """Returns the process corresponding to the parents PID"""
        return psutil.Process(pid=self._pid)

    def _thread_body(self) -> None:
        while True:
            stats = self._stats()
            # Not all stats are refreshed at the same time. To circumvent ever-changing keys in the sampler dict
            # we iterate through the collected stats and see if the stat is on the sampler dict. If not we add a None
            # and then add it with the value. If yes, we instantiate the sample with the same value again to carry it
            # over. In this way we get the full sampler dict after some time. This method will become especially
            # important if we start averaging quantities over a longer aggregation window.
            for stat, value in stats.items():
                self.sampler[stat] = self.sampler.get(stat, None)
                self.sampler[stat] = value

            self.flush()
            if self._shutdown:
                return

            seconds = 0.0
            while seconds < self._sample_rate_seconds:
                time.sleep(0.1)
                seconds += 0.1
                if self._shutdown:
                    return

    def shutdown(self) -> None:
        """Closes the SystemMonitor's thread."""
        self.flush()
        self._shutdown = True
        try:
            if self._thread is not None:
                self._thread.join()
        finally:
            self._thread = None

    def flush(self) -> None:
        """Used the backend senders publish method to sent the latest metrics to the configured backend"""
        self._backend_sender.publish(self.sampler)

    def _stats(self) -> StatsDict:
        stats: StatsDict = {}
        stats.update(self._collect_gpu_stats())
        stats.update(self._collect_system_stats())

        return stats

    def _collect_system_stats(self) -> StatsDict:
        stats: StatsDict = {}
        # See the notes in the class docstring under which assumption the rank prefix is sensible for CPU stats.
        pre = self._rank_prefix
        if psutil:
            net = psutil.net_io_counters()
            sysmem = psutil.virtual_memory()
            stats[pre + "cpu"] = psutil.cpu_percent()
            stats[pre + "memory"] = sysmem.percent
            stats[pre + "network"] = {
                "sent": net.bytes_sent - self.network_init["sent"],
                "recv": net.bytes_recv - self.network_init["recv"],
            }
            stats[pre + "disk"] = psutil.disk_usage("/").percent
            stats[pre + "proc.memory.availableMB"] = sysmem.available / 1048576.0
            try:
                stats[pre + "proc.memory.rssMB"] = self.proc.memory_info().rss / 1048576.0
                stats[pre + "proc.memory.percent"] = self.proc.memory_percent()
                stats[pre + "proc.cpu.threads"] = self.proc.num_threads()
            except psutil.NoSuchProcess:
                pass
        return stats

    def _collect_gpu_stats(self) -> StatsDict:
        stats: StatsDict = {}
        for i in range(0, self.gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            try:
                stats.update(self._get_gpu_utilization(i, handle))
            except pynvml.NVMLError:
                pass

            # Try to add power usage metrics separately. Some GPU's don't provide these infos and hence
            # we should catch them in a separate block as otherwise we'd not be recording any metrics.
            try:
                stats.update(self._get_gpu_power_usage(i, handle))
            except pynvml.NVMLError:
                pass

        return stats

    def _get_gpu_power_usage(self, i: int, handle: GPUHandle) -> StatsDict:
        stats: StatsDict = {}
        power_watts = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        power_capacity_watts = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000.0
        power_usage = (power_watts / power_capacity_watts) * 100

        stats[self._gpu_key(i, "powerWatts")] = power_watts
        stats[self._gpu_key(i, "powerPercent")] = power_usage

        return stats

    def _get_gpu_utilization(self, i: int, handle: GPUHandle) -> StatsDict:
        stats: StatsDict = {}
        utilz = pynvml.nvmlDeviceGetUtilizationRates(handle)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        stats[self._gpu_key(i, "gpu")] = utilz.gpu
        stats[self._gpu_key(i, "memory")] = utilz.memory
        stats[self._gpu_key(i, "memoryAllocated")] = (memory.used / float(memory.total)) * 100
        stats[self._gpu_key(i, "temp")] = temp

        return stats
