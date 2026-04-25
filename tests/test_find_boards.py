"""Tests for find_mpy_root — the walk-up-the-tree logic that locates a MicroPython repo."""

from __future__ import annotations

import pytest

from mpbuild.find_boards import find_mpy_root


@pytest.fixture(autouse=True)
def _clear_find_mpy_root_cache():
    """find_mpy_root is @cache-decorated; clear between tests for isolation."""
    find_mpy_root.cache_clear()
    yield
    find_mpy_root.cache_clear()


class TestFindMpyRoot:
    def test_explicit_path(self, mpy_root):
        """Explicit path that already is a MicroPython root returns it unchanged."""
        result, port = find_mpy_root(mpy_root)
        assert result == mpy_root
        assert port == ""

    def test_walks_up_to_find_root(self, mpy_root):
        """Walks parent dirs until ports/ + mpy-cross/ are found."""
        deep = mpy_root / "ports" / "stm32" / "boards" / "PYBV11"
        deep.mkdir(parents=True)

        result, port = find_mpy_root(deep)

        assert result == mpy_root

    def test_detects_port_when_inside_ports_subdir(self, mpy_root):
        """When a parent is ports/, that subdirectory's name is returned as the port."""
        port_dir = mpy_root / "ports" / "stm32"
        port_dir.mkdir(parents=True)

        _, port = find_mpy_root(port_dir)

        assert port == "stm32"

    def test_uses_env_var_when_no_arg(self, mpy_root, monkeypatch):
        """With no explicit path, MICROPY_DIR is consulted."""
        monkeypatch.setenv("MICROPY_DIR", str(mpy_root))
        result, _ = find_mpy_root()
        assert result == mpy_root

    def test_uses_cwd_when_no_arg_and_no_env(self, mpy_root, monkeypatch):
        """Without an arg or env var, CWD is the starting point."""
        monkeypatch.delenv("MICROPY_DIR", raising=False)
        monkeypatch.chdir(mpy_root)
        result, _ = find_mpy_root()
        assert result == mpy_root

    def test_raises_when_no_root_found(self, tmp_path):
        """Walking past the filesystem root without finding ports/+mpy-cross/ exits."""
        with pytest.raises(SystemExit, match="MicroPython source tree"):
            find_mpy_root(tmp_path)
