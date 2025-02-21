from __future__ import annotations

import inspect
import queue
from abc import abstractmethod
from concurrent.futures import Executor, ThreadPoolExecutor
from copy import deepcopy
from functools import partial
from typing import Any, Callable, Generator, Iterable, Iterator, List, Optional, Type, Union

from scaffold.data.iterstream.iterators import batched_, filter_, flatten_, map_, shuffle_, take_, tqdm_

__all__ = ["Composable", "AsyncContent"]


class Composable(Iterable):
    """A mix-in class that provides stream manipulation functionalities."""

    def __init__(self, source: Optional[Union[Iterable, Callable]] = None):
        """Init"""
        self.source = source

    @abstractmethod
    def __iter__(self) -> Iterator:
        """Abstract iter"""
        pass

    def compose(self, constructor: Type[Composable], *args, **kw) -> Composable:
        """
        Apply the transformation expressed in the `__iter__` method of the `constructor` to items in the stream.
        If the provided constructor has an __init__ method, then the source argument should not be provided.
        """
        assert "source" not in kw
        if "__init__" in constructor.__dict__ and "source" in inspect.signature(constructor).parameters:
            raise ValueError(
                "If the provided constructor argument has an __init__ method, it should not "
                "have the source argument."
            )
        return constructor(*args, **kw).source_(self)

    def to(self, f: Callable, *args, **kw) -> _Iterable:
        """Pipe the iterable into another iterable which applies `f` callable on it"""
        assert "source" not in kw
        return _Iterable(self, f, *args, **kw)

    def source_(self, source: Union[Iterable, Callable]) -> Composable:
        """Set the source of the stream"""
        self.source = source
        return self

    def map(self, callback: Callable, **kw) -> _Iterable:
        """Applies the `callback` to each item in the stream. Specify key-word arguments for callback in **kw"""
        partial_callback = partial(callback, **kw)
        return self.to(map_, partial_callback)

    def filter(self, predicate: Callable) -> _Iterable:
        """Filters items by `predicate` callable"""
        return self.to(filter_, predicate)

    def async_map(
        self,
        callback: Callable,
        buffer: int = 100,
        max_workers: Optional[int] = None,
        executor: Optional[Executor] = None,
        **kw,
    ) -> _AsyncMap:
        """
        Applies the `callback` to the item in the self and returns the result.

        Args:
            callback (Callable): a callable to be applied to items in the stream
            buffer (int): the size of the buffer
            max_workers (int): number of workers in the
                :py:class:`ThreadPoolExecutor <concurrent.futures.ThreadPoolExecutor>`.
                `max_workers` is only used when `executor` is not provided, as the `executor`
                already includes the number of `max_workers`.
            executor (concurrent.futures.Executor, dask.distributed.Client): an optional executor to be used.
                By default a :py:class:`ThreadPoolExecutor <concurrent.futures.ThreadPoolExecutor>`
                is created, if no executor is provided. If you need a
                :py:class:`ProcessPoolExecutor <concurrent.futures.ProccessPoolExecutor>`,
                you can explicitly provide it here. It is also useful when chaining multiple
                `async_map`; you can pass the same `executor` to each `async_map` to share resources. If
                `dask.distributed.Client` is passed, tasks will be executed with the provided client (local or remote).

                **Note** if the executor is provided, it will not be closed in this function even after the iterator
                is exhausted.

                **Note** if executor is provided, the argument `max_workers` will be ignored. You should
                specify this in the executor that is being passed.
            **kw (dict): key-word arguments for callback

        Returns (_AsyncMap)
        """
        partial_callback = partial(callback, **kw)
        return _AsyncMap(
            source=self, callback=partial_callback, buffer=buffer, max_workers=max_workers, executor=executor
        )

    def flatten(self) -> _Iterable:
        """When items in the stream are themselves iterables, flatten turn them back to individual items again"""
        return self.to(flatten_)

    def batched(
        self, batchsize: int, collation_fn: Optional[Callable] = None, drop_last_if_not_full: bool = True
    ) -> _Iterable:
        """Batch items in the stream.

        Args:
            batchsize: number of items to be batched together
            collation_fn: Collation function to use.
            drop_last_if_not_full (bool): if the length of the last batch is less than the `batchsize`, drop it
        """
        return self.to(
            batched_,
            batchsize=batchsize,
            collation_fn=collation_fn,
            drop_last_if_not_full=drop_last_if_not_full,
        )

    def sliding(
        self,
        window_size: int,
        *,
        deepcopy: bool,
        stride: int = 1,
        drop_last_if_not_full: bool = True,
        min_window_size: int = 1,
        fill_nan_on_partial: bool = False,
    ) -> Composable:
        """
        Apply sliding window over the stream.

        Args:
            window_size (int): the length of the window
            deepcopy (bool): If True, each window will be returned as a deepcopy. If items are mutated in the
                subsequent steps of the pipeline, this should be set to True, otherwise it should be False.
                Note that deepcopy may incur a substantial cost, so set this parameter carefully.
            stride (int): the distance that the window moves at each step
            drop_last_if_not_full (bool): If True, it would only return windows of size `window_size` and drops the
                last items which have fewer items.
            min_window_size (int): The minimum length of the window for the last remaining elements.
                This argument is only relevant if `drop_last_if_not_full` is set to False, otherwise it's ignored.
            fill_nan_on_partial (bool): If `drop_last_if_not_full` is False, the length of the last few windows
                will be less than `window_size`. This argument fill the missing values with None if set to True.
                This argument take precedence over If `min_window_size`.

        """
        if not window_size > 1:
            raise ValueError("window_size must be > 1")
        if not window_size > min_window_size >= 1:
            raise ValueError("window_size must be greater than min_window_size, and min_window_size >= 1")
        if not window_size >= stride >= 1:
            raise ValueError("stride should be smaller or equal to window_size, and greater or equal to 1")

        return _SlidingIter(
            source=self,
            window_size=window_size,
            deepcopy=deepcopy,
            stride=stride,
            drop_last_if_not_full=drop_last_if_not_full,
            min_window_size=min_window_size,
            fill_nan_on_partial=fill_nan_on_partial,
        )

    def shuffle(self, size: Optional[int] = 1000, **kw) -> Composable:
        """Shuffles items in the buffer, defined by `size`, to simulate IID sample retrieval.

        Args:
            size (int, optional): Buffer size for shuffling. Defaults to 1000. Skip the shuffle step if `size < 2`.

        Acceptable keyword arguments:

        - initial (int, optional): Minimum number of elements in the buffer before yielding the first element.
          Must be less than or equal to `size`, otherwise will be set to `size`. Defaults to 100.

        - rng (random.Random, optional): Either `random` module or a :py:class:`random.Random` instance. If None,
          a `random.Random()` is used.

        - seed (Union[int, float, str, bytes, bytearray, None]): A data input that can be used for `random.seed()`.

        """

        if size is None:
            size = 1000

        if size < 2:
            return self
        return self.to(shuffle_, size, **kw)

    def take(self, n: Optional[int]) -> Composable:
        """Take n samples from iterable"""
        if n is None:
            return self
        return self.to(take_, n)

    def loop(self, n: Optional[int] = None) -> Composable:
        """Repeat the iterable n times.

        Args:
            n (int, Optional): number of times that the iterable is looped over. If None (the default), it loops forever

        Note: this method creates a deepcopy of the `source` attribute, i.e. all steps in the chain of Composables
        `before` the loop itself, which must be picklable.
        """
        return _LoopIterable(self, n)

    def zip_index(self, pad_length: int = None) -> Composable:
        """Zip the item in the stream with its index and yield Tuple[index, item]

        Args:
            pad_length: if provided, all indexes will be padded with zeros if they have less digits than pad_length,
                in which case all indexes are str rather than int.
        """
        return _ZipIndexIterable(self, pad_length=pad_length)

    def join(self) -> None:
        """A method to consume the stream"""
        for _ in self:
            pass

    def collect(self) -> List[Any]:
        """Collect and returns the result of the stream"""
        return list(self)

    def tqdm(self, **kw) -> _Iterable:
        """Add tqdm to iterator."""
        return self.to(tqdm_, **kw)


class _Iterable(Composable):
    """
    A class representing an iterable, which applies the callable `f` to the `source` items and returns the result in
    the :py:meth:`__iter__` method. This is used as the object being passed between steps of the stream.
    """

    def __init__(self, source: Iterable, f: Callable[..., Iterator], *args, **kw):
        """Initialize _Iterable.

        Args:
            source (Iterable): An iterable representing the source items.
            f (Callable): A callable to be applied to the iterator, which is built from `source`. Must return an
                iterator.
            *args: Arguments being passed to `f`.
            **kw: Kwargs passed to `f`.
        """
        super().__init__(source)
        assert callable(f)
        self.f = f
        self.args = args
        self.kw = kw

    def __iter__(self) -> Iterator:
        """Returns the iterator that is obtained by applying `self.f` to `self.source`."""
        assert self.source is not None, f"must set source before calling iter {self.f} {self.args} {self.kw}"
        assert callable(self.f), self.f
        return self.f(iter(self.source), *self.args, **self.kw)


class _SlidingIter(Composable):
    def __init__(
        self,
        source: Iterable,
        window_size: int,
        deepcopy: bool,
        stride: int = 1,
        drop_last_if_not_full: bool = True,
        min_window_size: int = 1,
        fill_nan_on_partial: bool = False,
    ):
        """Init"""
        super().__init__(source=source)
        self.window_size = window_size
        self.deepcopy = deepcopy
        self.stride = stride
        self.drop_last_if_not_full = drop_last_if_not_full
        self.min_window_size = min_window_size
        self.fill_nan_on_partial = fill_nan_on_partial

    def __iter__(self):
        it = iter(self.source)
        _win = []

        while len(_win) < self.window_size:
            try:
                _win.append(next(it))
            except StopIteration:
                if not self.drop_last_if_not_full:
                    yield from self._yield(self._fill_na(_win))
                return

        while True:
            yield from self._yield(_win)
            _win = self._step(_win, it)
            if (
                _win is None
                or (len(_win) < self.min_window_size and not self.fill_nan_on_partial)
                or all([i is None for i in _win])
            ):
                return

    def _step(self, win_: List, it_: Iterable) -> List | None:
        _new_items = []
        for _ in range(self.stride):
            try:
                _new_items.append(next(it_))
            except StopIteration:
                if not self.drop_last_if_not_full:
                    return self._fill_na(win_[self.stride :] + _new_items)
                else:
                    return
        return win_[self.stride :] + _new_items

    def _yield(self, _win: List) -> Generator[List[Any], None, None]:
        if self.deepcopy:
            yield deepcopy(_win)
        else:
            yield _win

    def _fill_na(self, _win: List) -> List | None:
        if all([i is None for i in _win]):
            return
        if self.fill_nan_on_partial and len(_win) < self.window_size:
            return _win + [None for _ in range(self.window_size - len(_win))]
        else:
            return _win


class _LoopIterable(Composable):
    def __init__(self, source: Iterable, n: Optional[int]):
        """Init"""
        super().__init__(source=source)
        self.n = n
        self.counter = 0

    def __iter__(self) -> Iterator:
        """Iterate over the iterable n times"""
        _started = False
        if self.n is None:
            current_ = iter(deepcopy(self.source))
            while True:
                try:
                    yield next(current_)
                    _started = True
                except StopIteration:
                    if not _started:
                        return
                    self.counter += 1
                    current_ = iter(deepcopy(self.source))
        else:
            for _ in range(self.n):
                yield from iter(deepcopy(self.source))
                self.counter += 1


class _ZipIndexIterable(Composable):
    def __init__(self, source: Iterable, pad_length: int = None) -> None:
        """Init"""
        super().__init__(source)
        self.idx = 0
        self.pad_length = pad_length

    def __iter__(self) -> Iterator:
        """Zip the index and the data"""
        for i in self.source:
            yield self._next_idx(), i

    def _next_idx(self) -> Union[int, str]:
        _idx = None
        if self.pad_length is not None:
            str_idx = str(self.idx)

            _idx = "0" * (self.pad_length - len(str_idx)) + str_idx
        else:
            _idx = self.idx
        self.idx += 1
        return _idx


class _AsyncMap(Composable):
    def __init__(
        self,
        source: Iterable,
        callback: Callable,
        buffer: int = 100,
        max_workers: Optional[int] = None,
        executor: Optional[Executor] = None,
    ):
        """A class that applies a `callback` asynchronously to the items in the `dataset`, using thread pool executor"""
        super().__init__(source)
        self.buffer = buffer
        self.callback = callback
        self.max_workers = max_workers
        self.executor = executor

        # Instantiate queue lazily in the __iter__ method
        # This is necessary to be compatible with the thread forking of PyTorch multiprocessing context
        # when using a multi-worker dataloader.
        self.queue = None

    def __iter__(self) -> Iterator:
        """An iterator"""

        self.queue = queue.Queue(self.buffer)
        it = iter(self.source)

        if self._executor_not_provided():
            with ThreadPoolExecutor(max_workers=self.max_workers) as exec_:
                yield from self._iter(it, exec_)
        elif isinstance(self.executor, Executor):
            yield from self._iter(it, self.executor)
        else:
            raise ValueError(f"Executor {self.executor} not recognized")

    def _executor_not_provided(self) -> bool:
        return self.executor is None

    def _iter(self, it: Iterator, executor: Executor) -> Iterator:
        sentinel = object()
        while True:
            # Fill queue
            while not self.queue.full():
                item = next(it, sentinel)
                if item is sentinel:
                    break
                self.queue.put(AsyncContent(item=item, func=self.callback, executor=executor))

            # stop iterating if all samples processed
            if self.queue.empty():
                break

            # yield sample
            yield self.queue.get().value()

    def _dask_iter(self, it: Iterator) -> Iterator:
        sentinel = object()
        while True:
            while not self.queue.full():
                item = next(it, sentinel)
                if item is sentinel:
                    break
                self.queue.put(self.executor.submit(self.callback, item))

            if self.queue.empty():
                break

            yield self.queue.get().result()


class AsyncContent:
    """Represents content that can be fetched asynchronously."""

    def __init__(self, item: str, func: Callable, executor: Executor) -> None:
        """Initialize AsyncContent.

        Args:
            item (str): Key corresponding to a single item, will be passed to `fetch_func`.
            func (Callable): Function that fetches a given key.
            executor (concurrent.futures.Executor): Executor to submit `func` with `item`.
        """
        self.stack = 1
        self.future = executor.submit(func, item)

    def value(self, timeout: int = None) -> Any:
        """Get the value asynchronously.

        Args:
            timeout (int, optional): Number of seconds to wait for the result. If None, then the future is waited
                indefinitely. Defaults to None.

        Returns:
            Any: Content.
        """
        return self.future.result(timeout)
