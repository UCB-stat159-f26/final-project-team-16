"""Build paths of project files from the repository root."""

from pathlib import Path


def repo_path(*parts):
    """Build the path of a file or folder inside the repository.

    Parameters
    ----------
    *parts : str
        Names of the folders and the file below the repository root, in order.
        With no parts, the function returns the repository root.

    Returns
    -------
    pathlib.Path
        The absolute path of the file or folder. The function does not check
        that the path exists.
    """
    # This file is <root>/bpdtools/paths.py, so the repository root is the
    # parent of the bpdtools folder. This works from any working directory.
    repo_root = Path(__file__).resolve().parents[1]
    # Join the parts below the root, in the order given.
    return repo_root.joinpath(*parts)
