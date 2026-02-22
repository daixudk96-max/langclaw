"""
Shared utilities for langclaw internals.
"""

from __future__ import annotations

from pathlib import Path


def to_virtual_path(path: str | Path, workspace_dir: Path) -> str:
    """Convert an absolute filesystem path to a virtual path for ``FilesystemBackend``.

    ``deepagents.FilesystemBackend`` runs with ``virtual_mode=True`` anchored
    to ``workspace_dir``.  All skill and memory source paths passed to
    ``create_deep_agent`` must use virtual POSIX paths (e.g. ``/skills``,
    ``/AGENTS.md``) relative to the backend root — not absolute OS paths.

    This function performs the conversion:

    - Paths **inside** ``workspace_dir`` → stripped to their virtual equivalent
      (e.g. ``~/.langclaw/workspace/skills`` → ``/skills``).
    - Paths **outside** ``workspace_dir`` → returned unchanged so callers that
      already supply a virtual path (or an external path) are not modified.

    Args:
        path:          Absolute or relative filesystem path, or an
                       already-virtual path string (starts with ``/``).
        workspace_dir: The ``FilesystemBackend`` root directory.

    Returns:
        A POSIX virtual path string suitable for deepagents middleware sources.

    Examples::

        workspace = Path("~/.langclaw/workspace").expanduser()
        to_virtual_path(workspace / "skills", workspace)   # "/skills"
        to_virtual_path(workspace / "AGENTS.md", workspace)  # "/AGENTS.md"
        to_virtual_path("/custom/skills", workspace)       # "/custom/skills"
    """
    try:
        return "/" + str(Path(path).relative_to(workspace_dir))
    except ValueError:
        return str(path)
