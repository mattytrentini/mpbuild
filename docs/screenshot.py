"""Regenerate ``docs/interactive.svg`` — a static screenshot of the TUI.

Synthesises a small fake MicroPython source tree, drives the Textual app
through Pilot to a representative state (board selected, sample build output
in the log), then exports the rendered frame as SVG. Re-run after any
visual change to the TUI.

Usage:
    uv run python docs/screenshot.py
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent / "interactive.svg"

BOARDS: list[tuple[str, str, dict]] = [
    (
        "stm32",
        "PYBV11",
        {
            "mcu": "stm32f4",
            "product": "Pyboard v1.1",
            "vendor": "George Robotics",
            "url": "https://store.micropython.org/product/PYBv1.1",
            "images": [],
            "deploy": [],
            "variants": {
                "DP": "Double-precision float",
                "DP_THREAD": "Double precision float + Threads",
                "THREAD": "Threading",
            },
        },
    ),
    (
        "stm32",
        "NUCLEO_F401RE",
        {
            "mcu": "stm32f4",
            "product": "Nucleo F401RE",
            "vendor": "ST",
            "url": "https://www.st.com/",
            "images": [],
            "deploy": [],
        },
    ),
    (
        "rp2",
        "RPI_PICO",
        {
            "mcu": "rp2040",
            "product": "Raspberry Pi Pico",
            "vendor": "Raspberry Pi",
            "url": "https://www.raspberrypi.com/products/raspberry-pi-pico/",
            "images": [],
            "deploy": [],
        },
    ),
    (
        "rp2",
        "RPI_PICO2",
        {
            "mcu": "rp2350",
            "product": "Raspberry Pi Pico 2",
            "vendor": "Raspberry Pi",
            "url": "https://www.raspberrypi.com/products/raspberry-pi-pico-2/",
            "images": [],
            "deploy": [],
            "variants": {"RISCV": "RISC-V cores"},
        },
    ),
    (
        "esp32",
        "ESP32_GENERIC",
        {
            "mcu": "esp32",
            "product": "ESP32 Generic",
            "vendor": "Espressif",
            "url": "https://www.espressif.com/",
            "images": [],
            "deploy": [],
        },
    ),
]

LOG_LINES = [
    "[bold cyan][Building PYBV11 (DP_THREAD)][/]",
    "make -C mpy-cross",
    "make[1]: Entering directory '/micropython/mpy-cross'",
    "CC main.c",
    "CC genhdr/qstr.last.c",
    "LINK build/mpy-cross",
    "make -C ports/stm32 BOARD=PYBV11 BOARD_VARIANT=DP_THREAD submodules",
    "Synchronizing submodule url for 'lib/stm32lib'",
    "make -j 16 -C ports/stm32 BOARD=PYBV11 BOARD_VARIANT=DP_THREAD",
    "GEN build/PYBV11/DP_THREAD/genhdr/pins.h",
    "CC stm32_it.c",
    "CC main.c",
    "CC mphalport.c",
]


def _materialise_tree(root: Path) -> None:
    (root / "ports").mkdir()
    (root / "mpy-cross").mkdir()
    for port, name, data in BOARDS:
        d = root / "ports" / port / "boards" / name
        d.mkdir(parents=True)
        (d / "board.json").write_text(json.dumps(data))


async def _capture(out: Path) -> None:
    initial_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _materialise_tree(root)
        os.environ["MICROPY_DIR"] = str(root)
        os.chdir(root)
        try:
            # Imported after env setup; clear @cache so the new MICROPY_DIR
            # is picked up.
            from textual.widgets import RichLog, Tree

            from mpbuild import board_database
            from mpbuild.find_boards import find_mpy_root
            from mpbuild.interactive import MpBuildApp

            find_mpy_root.cache_clear()
            board_database.cache_clear()

            app = MpBuildApp()
            async with app.run_test(size=(110, 32)) as pilot:
                tree = app.query_one("#board-tree", Tree)
                stm32 = next(c for c in tree.root.children if str(c.label) == "stm32")
                stm32.expand()
                await pilot.pause()
                pyb = next(leaf for leaf in stm32.children if str(leaf.label) == "PYBV11")
                tree.select_node(pyb)
                await pilot.pause()

                # Populate the log with representative output so the screenshot
                # actually shows what a build looks like.
                log = app.query_one("#build-log", RichLog)
                for line in LOG_LINES:
                    log.write(line)
                log.border_title = "Building PYBV11 (DP_THREAD)"
                await pilot.pause()

                app.save_screenshot(str(out))
        finally:
            os.chdir(initial_cwd)


def main() -> None:
    asyncio.run(_capture(OUT_PATH))
    cwd = Path.cwd()
    rel = OUT_PATH.relative_to(cwd) if OUT_PATH.is_relative_to(cwd) else OUT_PATH
    print(f"Wrote {rel}")


if __name__ == "__main__":
    main()
