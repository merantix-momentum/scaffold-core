import os

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP


def check_distributed_setup() -> bool:
    """Tests distributed setup with a manual calculation."""
    if is_distributed():
        rank = dist.get_rank()
        world_size = dist.get_world_size()
        tensor = torch.arange(2, dtype=torch.int64) + 1 + 2 * rank
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)

        analytic_result = torch.tensor(
            [sum([0 + 1 + 2 * i for i in range(world_size)]), sum([1 + 1 + 2 * i for i in range(world_size)])]
        )

        return torch.allclose(tensor, analytic_result)
    return False


def is_same_accross_workers(local_tensor: torch.Tensor) -> bool:
    """Checks for a tensor if it is the same across all workers.
    Needs to be able to execute on all nodes, since we call all_gather. Otherwise this leads to deadlocks.
    """
    world_size = dist.get_world_size()

    destination_tensor_list = [torch.zeros_like(local_tensor) for _ in range(world_size)]
    dist.all_gather(destination_tensor_list, local_tensor)

    return all(torch.allclose(local_tensor, destination_tensor) for destination_tensor in destination_tensor_list)


def should_distribute() -> bool:
    """Returns true if job should be distributed."""
    return dist.is_available() and int(os.environ.get("WORLD_SIZE", 1)) > 1


def is_distributed() -> bool:
    """Returns true if job is distributed."""
    return dist.is_available() and dist.is_initialized()


def model_to_ddp(model: torch.nn.Module) -> DDP:
    """Converts a torch model into a distributed data parallel model."""
    model = torch.nn.SyncBatchNorm.convert_sync_batchnorm(model)
    # In the distributed setting, the devices always start at index 0 for every worker.
    # Currently we only support ddp, which uses one device per worker, so we always choose 0.
    return DDP(model.to("cuda:0"), device_ids=[0], output_device=0)
