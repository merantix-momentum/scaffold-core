import os
import random
import string

from git import Repo


def get_branch_identifier(random_suffix: bool = False) -> str:
    """
    Get version from git repository.

    By default, the version is `branch-sha`.
    If there are untracked files, the suffix `-dirty` is appended.
    If `random_suffix=True` a random suffix is appended.

    Kwargs:
        random_suffix (bool): whether a random suffix should be appended.
    """
    repo = Repo(os.getcwd(), search_parent_directories=True)
    sha = repo.git.rev_parse(repo.head, short=True)

    if not repo.head.is_detached:
        version = repo.active_branch.name + "-" + sha
    elif (tag := next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)) is not None:
        version = tag.name + "-" + sha
    else:
        version = repo.head.commit.hexsha

    # Make sure that the version prefix is a valid url path
    version = version.replace("/", "-")
    version = version.replace(".", "_")

    # untracked files or untracked changes or uncommitted but staged changes
    if (len(repo.untracked_files) > 0) or (len(repo.index.diff(None)) > 0) or (len(repo.index.diff("HEAD")) > 0):
        version += "-dirty"

    if random_suffix:
        suffix_len = 5
        version += "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=suffix_len))

    return version
