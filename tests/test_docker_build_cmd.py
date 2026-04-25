"""Tests for docker_build_cmd — assembling the docker run invocation."""

from __future__ import annotations

import os

import pytest

from mpbuild.board_database import Database
from mpbuild.build import docker_build_cmd


@pytest.fixture(autouse=True)
def _stub_host_devices(monkeypatch):
    """Make device discovery deterministic so tests don't depend on the host.

    docker_build_cmd inspects /dev/bus/usb/ and globs /dev/ttyACM* / ttyUSB*
    to populate ``--device`` flags. Stubbing these to empty makes the produced
    command stable across machines.
    """
    monkeypatch.setattr("mpbuild.build.glob.glob", lambda _pattern: [])
    monkeypatch.setattr("mpbuild.build.os.path.exists", lambda _p: False)


# ===================================================================
# Basic shape — non-clean, no variant, simple port
# ===================================================================
class TestDockerBuildCmdBasics:
    def test_shape(self, mpy_root, make_board):
        """The build command runs docker, mounts the mpy dir, and runs make under bash."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"])

        assert cmd.startswith("docker run --rm ")
        assert f"-v {mpy_root}:{mpy_root} -w {mpy_root}" in cmd
        assert "micropython/build-micropython-arm" in cmd
        assert "bash -c " in cmd
        assert "make -C mpy-cross && " in cmd
        assert "make -C ports/stm32 BOARD=PYBV11 submodules && " in cmd
        assert "make -j" in cmd
        assert "ports/stm32 BOARD=PYBV11" in cmd

    def test_uses_running_user_id(self, mpy_root, make_board):
        """A non-clean build runs as the host user so artefact ownership matches."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"])
        assert f"--user {os.getuid()}:{os.getgid()} " in cmd

    def test_interactive_default(self, mpy_root, make_board):
        """docker_interactive=True (default in tests here) adds the -it flag."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"], docker_interactive=True)
        assert " -it " in cmd

    def test_non_interactive_omits_it_flag(self, mpy_root, make_board):
        """docker_interactive=False omits the -it flag (e.g. when stdin is not a TTY)."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"], docker_interactive=False)
        assert " -it " not in cmd


# ===================================================================
# Variants
# ===================================================================
class TestDockerBuildCmdVariants:
    def test_physical_board_uses_BOARD_VARIANT(self, mpy_root, make_board):
        """Physical boards pass the variant via BOARD_VARIANT=."""
        make_board(
            "stm32",
            "PYBV11",
            mcu="stm32f4",
            variants={"DP_THREAD": "Double precision + Threads"},
        )
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"], variant="DP_THREAD")
        assert "BOARD=PYBV11 BOARD_VARIANT=DP_THREAD" in cmd
        assert "VARIANT=DP_THREAD" not in cmd or "BOARD_VARIANT=DP_THREAD" in cmd

    def test_special_port_uses_VARIANT(self, mpy_root):
        """Special ports (physical_board=False) use VARIANT= instead of BOARD_VARIANT=."""
        # 'unix' is a special port; give it a 'standard' variant subdir.
        unix_variants = mpy_root / "ports" / "unix" / "variants"
        unix_variants.mkdir(parents=True)
        (unix_variants / "standard").mkdir()

        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["unix"], variant="standard")
        assert "BOARD=unix VARIANT=standard" in cmd
        assert "BOARD_VARIANT=standard" not in cmd

    def test_unknown_variant_raises(self, mpy_root, make_board):
        """An unknown variant for the board raises ValueError."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        with pytest.raises(ValueError, match="Variant 'NOPE' not found"):
            docker_build_cmd(db.boards["PYBV11"], variant="NOPE")


# ===================================================================
# Clean
# ===================================================================
class TestDockerBuildCmdClean:
    def test_clean_runs_as_root(self, mpy_root, make_board):
        """do_clean=True runs as root (uid=0, gid=0) for permission to remove files."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"], do_clean=True)
        assert "--user 0:0 " in cmd
        assert f"--user {os.getuid()}:{os.getgid()} " not in cmd

    def test_clean_skips_mpy_cross_and_submodules(self, mpy_root, make_board):
        """do_clean=True skips the mpy-cross build and submodule update steps."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"], do_clean=True)
        assert "make -C mpy-cross" not in cmd
        assert "submodules" not in cmd


# ===================================================================
# Container override
# ===================================================================
class TestDockerBuildCmdContainerOverride:
    def test_override_bypasses_port_lookup(self, mpy_root, make_board):
        """build_container_override is used verbatim, replacing the port-derived image."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(
            db.boards["PYBV11"],
            build_container_override="custom/image:tag",
        )
        assert "custom/image:tag" in cmd
        assert "micropython/build-micropython-arm" not in cmd


# ===================================================================
# extra_args
# ===================================================================
class TestDockerBuildCmdExtraArgs:
    def test_extra_args_appended_to_make(self, mpy_root, make_board):
        """extra_args are space-joined and appended after the make target."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(
            db.boards["PYBV11"],
            extra_args=["V=1", "DEBUG=1"],
        )
        assert " V=1 DEBUG=1" in cmd


# ===================================================================
# Device flags (with the autouse stub overridden)
# ===================================================================
class TestDockerBuildCmdDeviceFlags:
    def test_includes_tty_devices_when_present(self, mpy_root, make_board, monkeypatch):
        """Discovered tty devices are passed through as --device flags."""

        def fake_glob(pattern):
            if "ttyACM" in pattern:
                return ["/dev/ttyACM0"]
            if "ttyUSB" in pattern:
                return ["/dev/ttyUSB0"]
            return []

        monkeypatch.setattr("mpbuild.build.glob.glob", fake_glob)

        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"])
        assert "--device /dev/ttyACM0" in cmd
        assert "--device /dev/ttyUSB0" in cmd

    def test_includes_usb_bus_when_populated(self, mpy_root, make_board, monkeypatch):
        """When /dev/bus/usb/ exists and is non-empty, it's passed as a --device."""
        monkeypatch.setattr("mpbuild.build.os.path.exists", lambda p: p == "/dev/bus/usb/")
        monkeypatch.setattr("mpbuild.build.os.listdir", lambda p: ["001"])

        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        cmd = docker_build_cmd(db.boards["PYBV11"])
        assert "--device /dev/bus/usb/" in cmd
