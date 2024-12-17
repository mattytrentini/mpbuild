import os
from pathlib import Path
from functools import cache


@cache
def find_mpy_root(root: str| Path | None = None) -> tuple[Path, str]:
    if root is None:
        root = Path(os.environ.get("MICROPY_DIR", ".")).resolve()
    else:
        root = Path(root)

    port = ""
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
