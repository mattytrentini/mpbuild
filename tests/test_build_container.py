"""Tests for get_build_container — port -> docker image resolution."""

from __future__ import annotations

import pytest

from mpbuild.board_database import Database
from mpbuild.build import (
    ARM_BUILD_CONTAINER,
    ESP_IDF_CONTAINER,
    ESP_IDF_FALLBACK_VERSION,
    MpbuildNotSupportedException,
    get_build_container,
)

# Sample lockfile content reused from the IDF detection tests.
LOCKFILE_ESP32 = """\
dependencies:
  idf:
    source:
      type: idf
    version: 5.5.1
target: esp32
version: 2.0.0
"""


# ===================================================================
# Simple ports: direct lookup in BUILD_CONTAINERS
# ===================================================================
class TestSimplePorts:
    @pytest.mark.parametrize(
        "port_name, expected",
        [
            ("stm32", ARM_BUILD_CONTAINER),
            ("nrf", ARM_BUILD_CONTAINER),
            ("mimxrt", ARM_BUILD_CONTAINER),
            ("renesas-ra", ARM_BUILD_CONTAINER),
            ("samd", ARM_BUILD_CONTAINER),
            ("psoc6", "ifxmakers/mpy-mtb-ci"),
            ("esp8266", "larsks/esp-open-sdk"),
        ],
    )
    def test_physical_port_maps_to_container(self, mpy_root, make_board, port_name, expected):
        """Each non-special port maps directly to its container in BUILD_CONTAINERS."""
        make_board(port_name, "BOARD_X", mcu="dummy")
        db = Database(mpy_root)
        assert get_build_container(db.boards["BOARD_X"]) == expected

    def test_unix_special_port(self, mpy_root):
        """The 'unix' special port resolves to its gcc image."""
        db = Database(mpy_root)
        assert get_build_container(db.boards["unix"]) == "gcc:12-bookworm"

    def test_unsupported_port_raises(self, mpy_root):
        """Ports not in BUILD_CONTAINERS raise MpbuildNotSupportedException."""
        # 'webassembly' is auto-added as a special port but is not in BUILD_CONTAINERS.
        db = Database(mpy_root)
        with pytest.raises(MpbuildNotSupportedException, match="webassembly"):
            get_build_container(db.boards["webassembly"])


# ===================================================================
# rp2 — has its own resolution path (default + RISCV variant)
# ===================================================================
class TestRp2:
    def test_default_returns_arm_bookworm(self, mpy_root, make_board):
        """rp2 needs a recent gcc; default resolves to the arm:bookworm image."""
        make_board("rp2", "RPI_PICO", mcu="rp2040")
        db = Database(mpy_root)
        assert (
            get_build_container(db.boards["RPI_PICO"])
            == "micropython/build-micropython-arm:bookworm"
        )

    def test_riscv_variant_uses_dedicated_image(self, mpy_root, make_board):
        """The RISCV variant (rp2350) uses its own dedicated container."""
        make_board(
            "rp2",
            "RPI_PICO2",
            mcu="rp2350",
            variants={"RISCV": "RISC-V core"},
        )
        db = Database(mpy_root)
        assert (
            get_build_container(db.boards["RPI_PICO2"], variant="RISCV")
            == "micropython/build-micropython-rp2350riscv"
        )

    def test_non_riscv_variant_uses_default(self, mpy_root, make_board):
        """Other rp2 variants still get the regular arm:bookworm container."""
        make_board(
            "rp2",
            "WEACTSTUDIO",
            mcu="rp2040",
            variants={"FLASH_2M": "2 MB flash"},
        )
        db = Database(mpy_root)
        assert (
            get_build_container(db.boards["WEACTSTUDIO"], variant="FLASH_2M")
            == "micropython/build-micropython-arm:bookworm"
        )


# ===================================================================
# esp32 — IDF version detection drives the container tag
# ===================================================================
class TestEsp32:
    def test_uses_detected_idf_version(self, mpy_root, make_board, make_lockfile):
        """When a lockfile pins an IDF version, the container tag matches it."""
        make_board("esp32", "ESP32_GENERIC", mcu="esp32")
        make_lockfile("esp32", LOCKFILE_ESP32)
        db = Database(mpy_root)
        assert get_build_container(db.boards["ESP32_GENERIC"]) == f"{ESP_IDF_CONTAINER}:v5.5.1"

    def test_falls_back_when_detection_fails(self, mpy_root, make_board):
        """Without a lockfile or workflow, esp32 uses the hardcoded fallback version."""
        make_board("esp32", "ESP32_GENERIC", mcu="esp32")
        db = Database(mpy_root)
        assert (
            get_build_container(db.boards["ESP32_GENERIC"])
            == f"{ESP_IDF_CONTAINER}:{ESP_IDF_FALLBACK_VERSION}"
        )

    def test_per_chip_idf_version(self, mpy_root, make_board, make_lockfile):
        """Different chip types pick up the per-MCU lockfile version."""
        make_board("esp32", "ESP32_GENERIC_S3", mcu="esp32s3")
        make_lockfile(
            "esp32s3",
            "dependencies:\n  idf:\n    source:\n      type: idf\n    version: 5.4.2\n",
        )
        db = Database(mpy_root)
        assert get_build_container(db.boards["ESP32_GENERIC_S3"]) == f"{ESP_IDF_CONTAINER}:v5.4.2"
