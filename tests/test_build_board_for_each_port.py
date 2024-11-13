"""
Call mpbuild for all boards.
Tests the first two variants.

Goal is a high test coverage of the boards.
"""

from mpbuild.build_api import build_by_variant
from mpbuild.build import MpbuildNotSupportedException

from test_build_some_variants import get_db

NUMBER_BOARDS = 1
NUMBER_VARIANTS = 2


def main():
    db = get_db()

    for port in db.ports.values():
        for board in list(port.boards.values())[0:NUMBER_BOARDS]:
            for variant in board.variants[0:NUMBER_VARIANTS]:
                print(f"Testing {variant.name_full}")
                try:
                    filename_firmware = build_by_variant(
                        variant=variant,
                        do_clean=False,
                    )
                    print(f"  {filename_firmware}")
                except MpbuildNotSupportedException:
                    print("  Not supported!")


if __name__ == "__main__":
    main()
