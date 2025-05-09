from __future__ import annotations

import os
import tempfile
import typing as t
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import numpy as np
import pytest

from scaffold.data.fs import get_fs_from_url
from scaffold.data.iterstream import Composable, FilePathGenerator, IterableSource
from scaffold.data.iterstream.iterators import take_

if t.TYPE_CHECKING:
    from scaffold.data.constants import SampleType


def test_iterablesource() -> None:
    """Test instantiating IterableSource in different ways"""

    def _gen() -> t.Any:
        """A generator without argument"""
        yield from range(3)

    def _gen_2(num: int) -> t.Any:
        """A generator with arguments"""
        yield from range(num)

    class _Gen:
        def __init__(self, items: t.List):
            self.items = items

        def __iter__(self):
            yield from self.items

    s = [0, 1, 2]
    it1 = IterableSource(range(3)).collect()
    it2 = IterableSource(s).collect()
    it3 = IterableSource(_gen).collect()
    it4 = IterableSource(_gen()).collect()
    it5 = IterableSource(partial(_Gen, s)).collect()
    it6 = IterableSource(partial(_gen_2, 3)).collect()
    it7 = IterableSource(_Gen(s)).collect()
    assert s == it1 == it2 == it3 == it4 == it5 == it6 == it7


def test_map(samples: t.List[t.Dict]) -> None:
    """Test map"""
    res_1 = IterableSource(samples).map(lambda sample: _f(sample, 3)).map(lambda sample: sample["label"]).collect()
    assert all(i == 3 for i in res_1)
    res_2 = IterableSource(range(5)).map(lambda sample, offset: sample + offset, offset=1).collect()
    assert res_2 == [1, 2, 3, 4, 5]
    res_3 = IterableSource(range(5)).map(multiply, factor=2).collect()
    assert res_3 == [0, 2, 4, 6, 8]
    linear_fn = partial(lambda x, a, b: a * x + b, b=1)
    res_4 = IterableSource(range(5)).map(linear_fn, a=2).collect()
    assert res_4 == [1, 3, 5, 7, 9]


def test_compose() -> None:
    """Test composing with different init methods"""

    class Add1(Composable):
        # use default constructor, supported by compose
        def __iter__(self):
            for i in self.source:
                yield i + 1

    class Add2(Composable):
        # use constructor without source, supported by compose
        def __init__(self):
            super().__init__()

        def __iter__(self):
            for i in self.source:
                yield i + 2

    class Add3(Composable):
        # use constructor with source, not supported by compose
        def __init__(self, source: t.Union[t.Iterable, t.Callable]):
            super().__init__(source)

        def __iter__(self):
            for i in self.source:
                yield i + 3

    class AddX1(Composable):
        # use constructor with other arguments and source as None, not supported by compose
        def __init__(self, x: int, source: t.Optional[t.Union[t.Iterable, t.Callable]] = None):
            super().__init__(source)
            self.x = x

        def __iter__(self):
            for i in self.source:
                yield i + self.x

    class AddX2(Composable):
        # use constructor with other arguments and source ,not supported by compose
        def __init__(self, x: int, source: t.Union[t.Iterable, t.Callable]):
            super().__init__(source)
            self.x = x

        def __iter__(self):
            for i in self.source:
                yield i + self.x

    lis = [1, 2, 3]
    it = IterableSource(lis).compose(Add1).collect()
    it1 = IterableSource(lis).compose(Add2).collect()
    with pytest.raises(ValueError):
        IterableSource(lis).compose(AddX1, 1).collect()
    with pytest.raises(ValueError):
        IterableSource(lis).compose(AddX2, 1).collect()
    with pytest.raises(ValueError):
        IterableSource(lis).compose(Add3).collect()
    assert it == [2, 3, 4]
    assert it1 == [3, 4, 5]


def test_async_map(samples: t.List[SampleType]) -> None:
    """Test async_map"""
    res_1 = (
        IterableSource(samples)
        .async_map(lambda sample: _f(sample, 4))
        .async_map(lambda sample: sample["label"])
        .collect()
    )
    assert all(i == 4 for i in res_1)
    res_2 = IterableSource(range(5)).async_map(lambda value, offset: value + offset, offset=1).collect()
    assert res_2 == [1, 2, 3, 4, 5]
    res_3 = IterableSource(range(5)).async_map(multiply, factor=2).collect()
    assert res_3 == [0, 2, 4, 6, 8]
    linear_fn = partial(lambda x, a, b: a * x + b, b=1)
    res_4 = IterableSource(range(5)).async_map(linear_fn, a=2).collect()
    assert res_4 == [1, 3, 5, 7, 9]
    res_5 = IterableSource(range(5)).async_map(multiply, factor=10, buffer=100).collect()
    assert res_5 == [0, 10, 20, 30, 40]


def test_filter(samples: t.List[SampleType]) -> None:
    """Test filter"""
    res = IterableSource(samples).filter(lambda s: s["label"] == 3).collect()
    assert len(res) == 0


def test_take(samples: t.List[SampleType]) -> None:
    """Test take"""
    # take less than elements in iterator
    res = IterableSource(samples).take(len(samples) - 1).collect()
    assert len(res) == len(samples) - 1

    # take more than elements in iterator
    res = IterableSource(samples).take(len(samples) + 1).collect()
    assert len(res) == len(samples)

    # take all elements in iterator
    res = IterableSource(samples).take(len(samples)).collect()
    assert len(res) == len(samples)


def test_take_exact(samples: t.List[SampleType]) -> None:
    """Test take_exact"""

    # take all elements in iterator
    it = IterableSource(samples).loop().take(len(samples)).collect()
    assert len(it) == len(samples)

    for n in np.random.choice(range(0, 100), 10, replace=False):
        it = IterableSource(samples).loop().take(n).collect()
        assert len(it) == n

    # take 0 elements
    it = IterableSource(samples).loop().take(0).collect()
    assert len(it) == 0

    # ensure that empty iterable works as expected
    it = IterableSource([]).loop().take(2).collect()
    assert len(it) == 0


@pytest.mark.parametrize("n", [0, 2, 4])
def test_loop(samples: t.List[SampleType], n: int) -> None:
    """Test loop"""
    it = IterableSource(samples).loop(n).collect()
    assert len(it) == n * len(samples)
    assert IterableSource([1, 2, 3]).loop(3).collect() == [1, 2, 3, 1, 2, 3, 1, 2, 3]


def test_loop_infinite() -> None:
    """Test infinite loop"""
    it = IterableSource([1, 2, 3]).loop()
    data = []
    for i, x in enumerate(it):
        data.append(x)
        if i == 8:
            break
    assert data == [1, 2, 3, 1, 2, 3, 1, 2, 3]


def test_loop_finite_counter() -> None:
    """Test loop counter"""
    it = IterableSource([1, 2, 3]).loop(n=3)
    counter = []
    for _ in it:
        counter.append(it.counter)
    assert counter == [0, 0, 0, 1, 1, 1, 2, 2, 2]


def test_loop_infinite_counter() -> None:
    """Test loop counter"""
    it = IterableSource([1, 2, 3]).loop()
    counter = []
    for i, _ in enumerate(it):
        counter.append(it.counter)
        if i == 8:
            break
    assert counter == [0, 0, 0, 1, 1, 1, 2, 2, 2]


def test_take_side_effect() -> None:
    """Test that take_ fetches correct number of elements from an iterator."""
    lst = [1, 2, 3, 4]
    it = iter(lst)
    assert list(take_(it, 2)) == [1, 2]
    assert list(take_(it, 2)) == [3, 4]


def test_take_less_elements() -> None:
    """Check that trying to take more elements than possible does not lead to errors."""
    assert list(take_([1, 2, 3], 10)) == [1, 2, 3]


def test_batched(samples: t.List[SampleType]) -> None:
    """Test batched with and without dropping non-full last batch"""
    res_drop = IterableSource(samples).batched(3, drop_last_if_not_full=True).collect()
    res_no_drop = IterableSource(samples).batched(3, drop_last_if_not_full=False).collect()
    assert len(res_drop) == 3
    assert len(res_no_drop) == 4
    assert all(len(batch) == 3 for batch in res_drop)


@pytest.mark.parametrize(
    "window_size,deepcopy,stride,drop_last_if_not_full,min_window_size,fill_nan_on_partial,expected",
    [
        (
            5,
            False,
            1,
            True,
            1,
            False,
            [
                [0, 1, 2, 3, 4],
                [1, 2, 3, 4, 5],
                [2, 3, 4, 5, 6],
                [3, 4, 5, 6, 7],
                [4, 5, 6, 7, 8],
                [5, 6, 7, 8, 9],
            ],
        ),
        (
            5,
            False,
            2,
            True,
            1,
            False,
            [
                [0, 1, 2, 3, 4],
                [2, 3, 4, 5, 6],
                [4, 5, 6, 7, 8],
            ],
        ),
        (
            5,
            False,
            2,
            True,
            1,
            True,
            [
                [0, 1, 2, 3, 4],
                [2, 3, 4, 5, 6],
                [4, 5, 6, 7, 8],
            ],
        ),
        (
            5,
            False,
            2,
            False,
            1,
            False,
            [
                [0, 1, 2, 3, 4],
                [2, 3, 4, 5, 6],
                [4, 5, 6, 7, 8],
                [6, 7, 8, 9],
                [8, 9],
            ],
        ),
        (
            5,
            False,
            2,
            False,
            3,
            True,
            [
                [0, 1, 2, 3, 4],
                [2, 3, 4, 5, 6],
                [4, 5, 6, 7, 8],
                [6, 7, 8, 9, None],
                [8, 9, None, None, None],
            ],
        ),
        (
            5,
            False,
            2,
            False,
            1,
            True,
            [
                [0, 1, 2, 3, 4],
                [2, 3, 4, 5, 6],
                [4, 5, 6, 7, 8],
                [6, 7, 8, 9, None],
                [8, 9, None, None, None],
            ],
        ),
        (
            5,
            False,
            2,
            True,
            1,
            True,
            [
                [0, 1, 2, 3, 4],
                [2, 3, 4, 5, 6],
                [4, 5, 6, 7, 8],
            ],
        ),
        (
            20,
            False,
            1,
            True,
            1,
            False,
            [],
        ),
    ],
)
def test_sliding(
    window_size: int,
    deepcopy: bool,
    stride: int,
    drop_last_if_not_full: bool,
    min_window_size: int,
    fill_nan_on_partial: bool,
    expected: t.List,
) -> None:
    """Test sliding"""
    inp = list(range(10))
    assert (
        IterableSource(inp)
        .sliding(
            window_size=window_size,
            deepcopy=deepcopy,
            stride=stride,
            drop_last_if_not_full=drop_last_if_not_full,
            min_window_size=min_window_size,
            fill_nan_on_partial=fill_nan_on_partial,
        )
        .collect()
        == expected
    )


def test_sliding_raise() -> None:
    """Test sliding exception for invalid arguments"""
    inp = list(range(10))
    with pytest.raises(ValueError):
        IterableSource(inp).sliding(2, deepcopy=False, stride=3).collect()
    with pytest.raises(ValueError):
        IterableSource(inp).sliding(1, deepcopy=False, stride=1).collect()


def test_sliding_and_batched_equivalence() -> None:
    """Test equivalence of sliding and batched when window_size==stride"""
    inp = list(range(10))
    s = 5
    assert (
        IterableSource(inp).sliding(s, deepcopy=False, stride=s).collect() == IterableSource(inp).batched(s).collect()
    )


def test_shuffle(samples: t.List[SampleType]) -> None:
    """Test shuffle"""
    ids = [s["key"] for s in samples]
    res_shuffled = IterableSource(samples).shuffle(10).map(lambda x: x["key"]).collect()
    assert len(set(ids) - set(res_shuffled)) == 0
    assert ids != res_shuffled
    assert sorted(ids) == sorted(res_shuffled)


def test_async_map_executor() -> None:
    """Test passing an executor to async_map"""
    exec_ = ThreadPoolExecutor(max_workers=2)
    res_1 = IterableSource(range(10)).async_map(lambda x: x + 1, executor=exec_).collect()
    # pass it to another stream to make sure it's not closed by scaffold when IterableSource is exhausted
    res_2 = (
        IterableSource(range(10))
        .async_map(lambda x: x + 2, executor=exec_)
        .async_map(lambda x: x - 1, executor=exec_)
        .collect()
    )
    exec_.shutdown()
    assert [i + 1 for i in range(10)] == res_1
    assert res_1 == res_2


def test_different_maps() -> None:
    """Test mapping a value with map, async_map"""

    def _add_one(x: int) -> int:
        return x + 1

    items = list(range(10))
    res_3 = IterableSource(items).map(_add_one).collect()
    res_4 = IterableSource(items).async_map(_add_one).collect()
    assert res_3 == res_4


def test_tqdm(samples: t.List[SampleType]) -> None:
    """Smoke test tqdm shorthand"""
    IterableSource(samples).tqdm().join()


def test_filepathgenerator_nested() -> None:
    """Test FilePathGenerator with on without nested argument"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        for d in range(2):
            for sub in range(2):
                basedir = f"{tmp_dir}/{d}"
                if not os.path.exists(basedir):
                    os.makedirs(basedir)
                with open(f"{tmp_dir}/{d}/{sub}.csv", mode="x") as f:
                    f.write("")

        dirs = FilePathGenerator(url=tmp_dir).collect()
        files = FilePathGenerator(url=tmp_dir, nested=True).collect()

    assert len(dirs) == 2
    assert len(files) == 4
    for fpath in files + dirs:
        assert fpath.startswith(tmp_dir)


@pytest.mark.skip(reason="Manual bucket test. Remove @skip to run.")
@pytest.mark.parametrize("bucket_path", ["gs://<example_bucket>/test_filepathgenerator_scaffold"])
def test_filepathgenerator_bucket(bucket_path: str) -> None:
    """Test FilePathGenerator with the bucket path"""

    fs = get_fs_from_url(bucket_path)
    random_uuid = str(uuid.uuid4())

    basedir = f"{bucket_path}/{random_uuid}"
    for d in range(2):
        for sub in range(2):
            d_dir = f"{basedir}/{d}"
            # save a dummy csv file to the bucket with the name: {d}/{sub}.csv
            if not fs.exists(d_dir):
                fs.makedirs(d_dir)
            with fs.open(f"{d_dir}/{sub}.csv", mode="x") as f:
                f.write("")

    dirs = FilePathGenerator(url=basedir).collect()
    files = FilePathGenerator(url=basedir, nested=True).collect()
    assert len(dirs) == 2
    assert len(files) == 4
    for fpath in files + dirs:
        assert fpath.startswith(bucket_path)


def test_zip_index() -> None:
    """Test zip_index method"""
    res1 = IterableSource(list(range(3))).zip_index().map(lambda x: x[0]).collect()
    assert res1 == [0, 1, 2]

    res2 = IterableSource(list(range(3))).zip_index(pad_length=3).map(lambda x: x[0]).collect()
    assert res2 == ["000", "001", "002"]

    res3 = IterableSource(list(range(101))).zip_index(pad_length=2).map(lambda x: x[0]).collect()
    assert res3[0] == "00" and res3[-2] == "99" and res3[-1] == "100"


@pytest.mark.parametrize("size", [None, 1, 200])
def test_shuffle_size_parameter(size: t.Optional[int]) -> None:
    """Test size paramter for shuffle"""
    source = IterableSource(list(range(100)))
    iter = source.shuffle(size=size).collect()
    assert sorted(iter) == list(range(100))


@pytest.fixture
def samples() -> t.List[SampleType]:
    """A fixture to get a list of samples"""
    return [get_sample() for _ in range(10)]


def get_sample() -> SampleType:
    """Return a single sample with random values"""
    return {
        "key": f"_{np.random.randint(1, 10000)}",
        "image": np.random.random(size=(1, 1, 1)),
        "label": np.random.choice([0, 1]),
        "meta": {"key": "value", "split": np.random.choice(["train", "test", "validation"])},
        "cache_spec": [
            "label",
        ],
    }


def _f(sample: SampleType, value: int) -> SampleType:
    """Sets label value to given value"""
    sample["label"] = value
    return sample


def multiply(value: float, factor: float) -> float:
    """Simply multiply value by given factor"""
    return value * factor
