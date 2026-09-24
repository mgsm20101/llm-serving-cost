"""Git provenance and dirty-tree guard for benchmark runs.

A benchmark result is only trustworthy if we know exactly what code produced
it. This module answers two questions before a run starts: what commit is
checked out, and is the worktree clean. Neither question touches the network
or Ollama — both use plain `git` subprocess calls, which is what makes the
refusal logic testable without a real repository.
"""

from __future__ import annotations

import subprocess
from typing import Callable

RunFunc = Callable[..., subprocess.CompletedProcess]


class DirtyWorktreeError(RuntimeError):
    """Raised when a run is refused: dirty tree, or no git repo, without --allow-dirty."""


def get_source_commit_sha(run: RunFunc = subprocess.run) -> str | None:
    """Return the current commit SHA, or None if not inside a git repository."""
    try:
        result = run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def is_worktree_clean(run: RunFunc = subprocess.run) -> bool:
    """Return True only if `git status --porcelain` reports zero changes."""
    try:
        result = run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    if result.returncode != 0:
        return False
    return result.stdout.strip() == ""


def check_provenance(
    allow_dirty: bool,
    run: RunFunc = subprocess.run,
) -> tuple[str | None, bool]:
    """Resolve (source_commit_sha, worktree_clean) or raise DirtyWorktreeError.

    Refuses to proceed when there is no git repository, or the tree has
    uncommitted changes, unless `allow_dirty` is set.
    """
    sha = get_source_commit_sha(run=run)
    clean = is_worktree_clean(run=run) if sha is not None else False

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
