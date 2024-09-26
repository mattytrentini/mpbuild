import os
from pathlib import Path
from functools import cache


@cache
def find_mpy_root(root: str| Path | None = None):
    if root is None:
        root = Path(os.environ.get("MICROPY_DIR", ".")).resolve()
    else:
        root = Path(root)

    port = None
    while True:
        # If run from a port folder, store that for use in filters
        if root.parent.name == "ports":
            port = root.name

        if (root / "ports").exists() and (root / "mpy-cross").exists():
            return root, port

        if root.parent == root:
            raise SystemExit(
                "Please run from MicroPython source tree or specify with env: MICROPY_DIR"
            )
        root = root.parent


def parse_board_spec(spec):
    """
    board spec format is <port/>board</variant>
    ie both port and variant are optional, with just the board as mandatory.

    """
    port = None
    specs = spec.split("/")
    if specs[0].lower() == specs[0]:
        port = specs.pop(0)
    board = specs.pop(0)
    variant = specs[0] if specs else ""
    return port, board, variant
