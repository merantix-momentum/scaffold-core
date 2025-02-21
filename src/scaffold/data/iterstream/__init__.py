"""
At a low level, iterstream is defined through a class called :py:class:`Composable`.
All chaining methods are defined within this class, and can be applied at its high level twin class called
:py:class:`IterableSource`.
"""

from scaffold.data.iterstream.base import Composable
from scaffold.data.iterstream.source import FilePathGenerator, IterableSamplerSource, IterableSource

__all__ = [
    "Composable",
    "IterableSource",
    "IterableSamplerSource",
    "FilePathGenerator",
]
