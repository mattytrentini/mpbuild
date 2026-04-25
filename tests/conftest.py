"""Shared fixtures for mpbuild tests.

The fixtures here synthesize a minimal MicroPython source tree on disk, which
is the shape every mpbuild code path expects (a directory with ``ports/``,
``mpy-cross/``, board.json files, lockfiles, etc.). Tests declare the factories
they need in their parameter list; pytest wires them up automatically.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def mpy_root(tmp_path: Path) -> Path:
    """A minimal MicroPython repo root.

    Has empty ``ports/`` and ``mpy-cross/`` directories so that
    ``find_mpy_root`` and ``Database`` validation accept it.
    """
    (tmp_path / "ports").mkdir()
    (tmp_path / "mpy-cross").mkdir()
    return tmp_path


@pytest.fixture
def make_board(mpy_root: Path) -> Callable[..., Path]:
    """Factory that writes a board.json under the given port/name.

    Example:
        def test_x(make_board):
            make_board("stm32", "PYBV11", mcu="stm32f4", product="Pyboard v1.1")
    """

    def _make(port: str, name: str, **board_json) -> Path:
        board_dir = mpy_root / "ports" / port / "boards" / name
        board_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(json.dumps(board_json))
        return board_dir

    return _make


@pytest.fixture
def make_lockfile(mpy_root: Path) -> Callable[[str, str], Path]:
    """Factory that writes an ESP-IDF lockfile for the given MCU.

    Writes to ``ports/esp32/lockfiles/dependencies.lock.<mcu>``.
    """

    def _make(mcu: str, content: str) -> Path:
        lockfile_dir = mpy_root / "ports" / "esp32" / "lockfiles"
        lockfile_dir.mkdir(parents=True, exist_ok=True)
        path = lockfile_dir / f"dependencies.lock.{mcu}"
        path.write_text(content)
        return path

    return _make


@pytest.fixture
def make_workflow(mpy_root: Path) -> Callable[[str], Path]:
    """Factory that writes the esp32 CI workflow at the conventional path.

    Writes to ``.github/workflows/ports_esp32.yml``.
    """

    def _make(content: str) -> Path:
        workflow_dir = mpy_root / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        path = workflow_dir / "ports_esp32.yml"
        path.write_text(content)
        return path

    return _make
