"""Tests for ``get_main_git_directory`` — git worktree detection.

The function uses ``git rev-parse --git-common-dir`` to determine whether the
caller is in a worktree whose common git directory sits outside the working
tree (and therefore needs an additional bind-mount inside docker).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mpbuild.build import get_main_git_directory


def _git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``, failing the test if it errors.

    ``-c user.name=... -c user.email=...`` is injected so ``git commit`` works
    on hosts without a global git config, without otherwise touching the
    environment that ``git init`` / ``git worktree`` need.
    """
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_returns_none_for_regular_repo(tmp_path: Path) -> None:
    """In a normal repo (``.git`` inside the working tree) no extra mount
    is needed, so the function returns ``None``."""
    _git(tmp_path, "init", "-q")
    assert get_main_git_directory(tmp_path) is None


def test_returns_common_dir_for_worktree(tmp_path: Path) -> None:
    """In a worktree (where the common .git dir sits outside the working
    tree) the function returns the absolute path of that common dir."""
    main_repo = tmp_path / "main"
    work_tree = tmp_path / "work"
    main_repo.mkdir()
    _git(main_repo, "init", "-q")
    (main_repo / "README").write_text("hello")
    _git(main_repo, "add", "README")
    _git(main_repo, "commit", "-q", "-m", "initial")
    _git(main_repo, "worktree", "add", "-q", str(work_tree))

    result = get_main_git_directory(work_tree)

    assert result is not None
    # The common dir is the .git inside the main repo, resolved absolutely.
    assert result == (main_repo / ".git").resolve()


def test_raises_when_git_not_found(tmp_path: Path, monkeypatch) -> None:
    """If git is not on PATH, the helper raises RuntimeError with a hint."""

    def _no_git(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr("mpbuild.build.subprocess.run", _no_git)
    with pytest.raises(RuntimeError, match="Git command not found"):
        get_main_git_directory(tmp_path)
