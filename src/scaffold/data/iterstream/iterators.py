import os
import pickle
import random
import time
from itertools import islice
from typing import Any, Callable, Iterable, Iterator, List, Optional

import numpy as np
from tqdm import tqdm

from scaffold.data.constants import SeedType


def _pick(buf: List, rng: random.Random) -> Any:
    """Pick a random element from a list.

    Args:
        buf (List): List of items.
        rng (random.Random): Random number generator to use.

    Returns:
        Any: One random item from `buf`.
    """
    k = rng.randint(0, len(buf) - 1)
    sample = buf[k]
    buf[k] = buf[-1]
    buf.pop()
    return sample


def shuffle_(
    iterable: Iterable,
    bufsize: int = 1000,
    initial: int = 100,
    rng: Optional[random.Random] = None,
    seed: SeedType = None,
) -> Iterator:
    """Shuffle the data in the stream.

    Uses a buffer of size `bufsize`. Shuffling at startup is less random; this is traded off against yielding samples
    quickly.

    Args:
        iterable (Iterable): Iterable to shuffle.
        bufsize (int, optional): Buffer size for shuffling. Defaults to 1000.
        initial (int, optional): Minimum number of elements in the buffer before yielding the first element. Must be
            less than or equal to `bufsize`, otherwise will be set to `bufsize`. Defaults to 100.
        rng (random.Random, optional): Either `random` module or a :py:class:`random.Random` instance. If None,
            a `random.Random()` is used.
        seed (Union[int, float, str, bytes, bytearray, None]): A data input that can be used for `random.seed()`.

    Yields:
        Any: Shuffled items of `iterable`.
    """
    rng = get_random_range(rng, seed)

    iterator = iter(iterable)
    initial = min(initial, bufsize)
    buf = []
    for sample in iterator:
        buf.append(sample)
        if len(buf) < bufsize:
            try:
                buf.append(next(iterator))
            except StopIteration:
                pass
        if len(buf) >= initial:
            yield _pick(buf, rng)
    while len(buf) > 0:
        yield _pick(buf, rng)


def take_(iterable: Iterable, n: int) -> Iterator:
    """Yield the first n elements from the iterable.

    Args:
        iterable (Iterable): Iterable to take from.
        n (int): Number of samples to take.

    Yields:
        Any: First `n` elements of `iterable`. Less elements can be yielded if the iterable does not have enough
            elements.
    """
    yield from islice(iterable, 0, n, 1)


def batched_(
    iterable: Iterable,
    batchsize: int = 20,
    collation_fn: Optional[Callable] = None,
    drop_last_if_not_full: bool = True,
) -> Iterator[List]:
    """Yield batches of the given size.

    Args:
        iterable (Iterable): Iterable to be batched.
        batchsize (int, optional): Target batch size. Defaults to 20.
        collation_fn (Callable, optional): Collation function. Defaults to None.
        drop_last_if_not_full (bool, optional): If the length of the last batch is less than `batchsize`, drop it.
            Defaults to True.

    Yields:
        Batches (i.e. lists) of samples.
    """
    it = iter(iterable)
    while True:
        batch = list(islice(it, batchsize))
        if drop_last_if_not_full and len(batch) < batchsize or len(batch) == 0:
            return
        if collation_fn is not None:
            batch = collation_fn(batch)
        yield batch


def map_(iterable: Iterable, callback: Callable) -> Iterator:
    """Apply the `callback` to each item in the `iterable` and yield the item."""
    for sample in iterable:
        yield callback(sample)


def filter_(iterable: Iterable, predicate: Callable) -> Iterator:
    """Filter items in the `iterable` by the `predicate` callable."""
    for sample in iterable:
        if predicate(sample):
            yield sample


def flatten_(iterables: Iterable[Iterable]) -> Iterator:
    """Iterate over iterables in the stream and yield their items."""
    for item in iterables:
        yield from item


def tqdm_(iterable: Iterable, **kwargs) -> Iterator:
    """Iterate while using tqdm."""
    yield from tqdm(iterable, **kwargs)


def get_random_range(rng: Optional[random.Random] = None, seed: SeedType = None) -> random.Random:
    """
    Returns a random number as range, calculated based on the input `rng` and `seed`.

    Args:
        rng (random.Random, optional): Either `random` module or a :py:class:`random.Random` instance. If None,
            a `random.Random()` is used.
        seed (Union[int, float, str, bytes, bytearray, None]): seed (Optional[int]): An int or other acceptable types
            that works for random.seed(). Will be used to seed `rng`. If None, a unique identifier will be used to seed.
    """
    if rng is None:
        rng = random.Random()
    if seed is None:
        seed = f"{os.getpid()}{time.time()}"
    rng.seed(seed)
    return rng


def getsize(item: Any) -> int:
    """Return estimated size (in terms of bytes) of a python object. Currently use numpy method to calculate size.
    Otherwise, the size is estimated through its pickled size. This is considered a better performant option than e.g.
    `zarr.storage.getsize()`.
    """
    if isinstance(item, np.ndarray):
        return item.nbytes
    return len(pickle.dumps(item))
