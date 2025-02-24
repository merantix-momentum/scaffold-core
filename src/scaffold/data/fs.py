import fsspec
from fsspec.core import split_protocol

from scaffold.data.constants import FILESYSTEM, URL

__all__ = ["get_fs_from_url", "get_protocol"]


def join_path(*parts: str) -> str:
    """Join path parts into a single path.

    This function concatenates the provided path segments using "/"
    and strips trailing slashes from each part. It works for both local
    paths and cloud bucket paths (e.g., "gs://").

    Args:
        *parts (str): Variable number of path segments.

    Returns:
        str: The resulting joined path.
    """
    return "/".join(part.rstrip("/") for part in parts if part)


def get_fs_from_url(url: URL, **storage_options) -> FILESYSTEM:
    """Get filesystem suitable for a url.

    Only the protocol part of the url is used, thus there is no need to call this method several times for different
    stores accessed with the same protocol. Should be called outside of store initialization to allow buffering from
    the same container among different stores or shards.

    The protocol can be overriden via the `storage_options`. This is important if people want to use the fsspec caching
    functionality, which requires the protocol to be, e.g., `simplecache`.
    """

    protocol, _ = split_protocol(url)

    # Provided storage_options take precedence
    storage_options = {"protocol": protocol, **storage_options}
    return fsspec.filesystem(**storage_options)


def get_protocol(url: str) -> str:
    """Get the protocol from a url, return empty string if local"""
    return f"{url.split('://')[0]}://" if "://" in url else ""
