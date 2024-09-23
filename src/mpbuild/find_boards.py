import os
from glob import iglob
from pathlib import Path
from functools import cache
import typer


SPECIAL_PORTS = ["unix", "webassembly", "windows"]


def port_and_board(mpy_dir):
    for p in iglob(f"{mpy_dir}/ports/**/boards/**/"):
        path = Path(p)
        yield path.parent.parent.name, path.name

    for port in SPECIAL_PORTS:
        yield port, port


@cache
def find_mpy_root(root: str = None):
    if root is None:
        root = Path(os.environ.get("MICROPY_DIR", ".")).resolve()

    port = None
    while True:
        # If run from a port folder, store that for use in filters
        if root.parent.name == "ports":
            port = root.name

        if (root / "ports").exists() and (root / "mpy-cross").exists():
            return str(root), port

        if root.parent == root:
            raise SystemExit(
                "Please run from MicroPython source tree or specify with env: MICROPY_DIR"
            )
        root = root.parent


@cache
def ports_and_boards(mpy_dir):
    p_and_b = dict()
    for p, b in port_and_board(mpy_dir):
        p_and_b.setdefault(p, []).append(b)
    return p_and_b


def get_port(mpy_dir, board):
    p_and_b = ports_and_boards(mpy_dir)
    for p in p_and_b.keys():
        if board in p_and_b[p]:
            print(f'"{board}" is in {p}')
            return p

    print(f'"{board}" is an invalid board')
    raise typer.Exit(code=1)
