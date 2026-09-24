"""Tests for the git provenance / dirty-tree refusal logic in src/bench/provenance.py.

subprocess.run is mocked throughout — no real git process is invoked.
"""

from __future__ import annotations

import subprocess

import pytest

from src.bench.provenance import (
    DirtyWorktreeError,
    check_provenance,
    get_source_commit_sha,
    is_worktree_clean,
)


def _completed(returncode=0, stdout=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_get_source_commit_sha_returns_stripped_sha():
    def fake_run(*a, **k):
        return _completed(0, "abc123def456\n")

    assert get_source_commit_sha(run=fake_run) == "abc123def456"


def test_get_source_commit_sha_returns_none_outside_git_repo():
    def fake_run(*a, **k):
        return _completed(128, "")

    assert get_source_commit_sha(run=fake_run) is None


def test_get_source_commit_sha_returns_none_when_git_missing():
    def fake_run(*a, **k):
        raise FileNotFoundError("git not found")

    assert get_source_commit_sha(run=fake_run) is None


def test_is_worktree_clean_true_when_status_empty():
    def fake_run(*a, **k):
        return _completed(0, "")

    assert is_worktree_clean(run=fake_run) is True


def test_is_worktree_clean_false_when_status_has_output():
    def fake_run(*a, **k):
        return _completed(0, " M run_bench.py\n")

    assert is_worktree_clean(run=fake_run) is False


def test_check_provenance_refuses_dirty_tree_by_default():
    calls = {"sha": _completed(0, "deadbeef01\n"), "status": _completed(0, " M x.py\n")}

    def fake_run(cmd, **k):
        if "rev-parse" in cmd:
            return calls["sha"]
        return calls["status"]

    with pytest.raises(DirtyWorktreeError):
        check_provenance(allow_dirty=False, run=fake_run)


def test_check_provenance_refuses_outside_git_repo_by_default():
    def fake_run(cmd, **k):
        return _completed(128, "")

    with pytest.raises(DirtyWorktreeError):
        check_provenance(allow_dirty=False, run=fake_run)


def test_check_provenance_allows_dirty_tree_with_flag():
    def fake_run(cmd, **k):
        if "rev-parse" in cmd:
            return _completed(0, "deadbeef01\n")
        return _completed(0, " M x.py\n")

    sha, clean = check_provenance(allow_dirty=True, run=fake_run)
    assert sha == "deadbeef01"
    assert clean is False


def test_check_provenance_passes_on_clean_tree():
    def fake_run(cmd, **k):
        if "rev-parse" in cmd:
            return _completed(0, "cafebabe99\n")
        return _completed(0, "")

    sha, clean = check_provenance(allow_dirty=False, run=fake_run)
    assert sha == "cafebabe99"
    assert clean is True
