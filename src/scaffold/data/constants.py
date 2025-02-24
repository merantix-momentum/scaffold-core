from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Dict, Optional, Union

from fsspec.spec import AbstractFileSystem

URL = Union[str, Path]
FILESYSTEM = Union[MutableMapping, AbstractFileSystem]
SampleType = Dict[str, Any]
SeedType = Optional[Union[int, float, str, bytes, bytearray]]
