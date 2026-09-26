"""Git provenance and dirty-tree guard for benchmark runs.

A benchmark result is only trustworthy if we know exactly what code produced
it. Before a run starts, check_provenance answers two questions with plain
`git` subprocess calls: what commit is checked out, and is the worktree clean.
"""

from __future__ import annotations

import subprocess


class DirtyWorktreeError(RuntimeError):
    """Raised when a run is refused: dirty tree, or no git repo, without --allow-dirty."""


def _git(*args: str) -> str | None:
    """Stripped stdout of `git <args>`, or None if git is missing or the command fails."""
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def check_provenance(allow_dirty: bool) -> tuple[str | None, bool]:
    """Resolve (source_commit_sha, worktree_clean) or raise DirtyWorktreeError.

    Refuses to proceed when there is no git repository, or the tree has
    uncommitted changes, unless `allow_dirty` is set.
    """
    sha = _git("rev-parse", "HEAD") or None
    clean = sha is not None and _git("status", "--porcelain") == ""

    if allow_dirty:
        return sha, clean

    if sha is None:
        raise DirtyWorktreeError(
            "not inside a git repository — pass --allow-dirty to run anyway"
        )
    if not clean:
        raise DirtyWorktreeError(
            "worktree has uncommitted changes — commit them or pass --allow-dirty"
        )
    return sha, clean
