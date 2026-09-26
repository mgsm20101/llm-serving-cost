"""Tests for the git provenance / dirty-tree refusal logic in src/bench/provenance.py.

subprocess.run is monkeypatched throughout — no real git process is invoked.
"""

from __future__ import annotations

import subprocess

import pytest

from src.bench import provenance
from src.bench.provenance import DirtyWorktreeError, check_provenance


def _fake_git(monkeypatch, sha=(0, "deadbeef01\n"), status=(0, "")):
    """Answer `git rev-parse HEAD` with `sha` and `git status` with `status` (returncode, stdout)."""

    def fake_run(cmd, **kwargs):
        returncode, stdout = sha if "rev-parse" in cmd else status
        return subprocess.CompletedProcess(args=cmd, returncode=returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(provenance.subprocess, "run", fake_run)


def test_passes_on_clean_tree_and_strips_sha(monkeypatch):
    _fake_git(monkeypatch, sha=(0, "cafebabe99\n"), status=(0, ""))

    assert check_provenance(allow_dirty=False) == ("cafebabe99", True)


def test_refuses_dirty_tree_by_default(monkeypatch):
    _fake_git(monkeypatch, status=(0, " M x.py\n"))

    with pytest.raises(DirtyWorktreeError, match="worktree has uncommitted changes"):
        check_provenance(allow_dirty=False)


def test_refuses_outside_git_repo_by_default(monkeypatch):
    _fake_git(monkeypatch, sha=(128, ""), status=(128, ""))

    with pytest.raises(DirtyWorktreeError, match="not inside a git repository"):
        check_provenance(allow_dirty=False)


def test_refuses_when_git_is_not_installed(monkeypatch):
    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(provenance.subprocess, "run", missing_git)

    with pytest.raises(DirtyWorktreeError, match="not inside a git repository"):
        check_provenance(allow_dirty=False)


def test_allows_dirty_tree_with_flag_and_records_it(monkeypatch):
    _fake_git(monkeypatch, status=(0, " M x.py\n"))

    assert check_provenance(allow_dirty=True) == ("deadbeef01", False)


def test_allows_no_repo_with_flag_and_records_no_sha(monkeypatch):
    _fake_git(monkeypatch, sha=(128, ""), status=(128, ""))

    assert check_provenance(allow_dirty=True) == (None, False)


def test_failed_git_status_counts_as_dirty(monkeypatch):
    _fake_git(monkeypatch, status=(1, ""))

    assert check_provenance(allow_dirty=True) == ("deadbeef01", False)
