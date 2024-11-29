"""
Call mpbuild for some selected boards and variants.

Goal is a high test coverage.
"""

import os
from pathlib import Path

from mpbuild.build_api import build_by_variant_str
from mpbuild.board_database import Database


MICROPY_DIR = "MICROPY_DIR"

_VARIANTS_TO_TEST = (
    # Standard case
    "RPI_PICO2",
    # Special case: Variant uses another build container
    "RPI_PICO2-RISCV",
    # Standard case
    "PYBV11",
    "ESP8266_GENERIC",
    # Special case: Variant
    "PYBV11-THREAD",
    # Special case: Unix
    "unix-minimal",
    "unix-coverage",
)


def get_db() -> Database:
    try:
        mpy_root_directory = Path(os.environ[MICROPY_DIR])
        return Database(mpy_root_directory=mpy_root_directory)
    except KeyError as e:
        raise SystemExit(
            f"The environment variable '{MICROPY_DIR}' is not defined!"
        ) from e


def main():
    db = get_db()

    for variant_str in _VARIANTS_TO_TEST:
        print(f"Testing {variant_str}")
        firmware = build_by_variant_str(
            db=db,
            variant_str=variant_str,
            do_clean=False,
        )
        print(f"  {firmware}")


if __name__ == "__main__":
    main()
