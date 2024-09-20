import os
from glob import iglob, glob
from pathlib import Path
from functools import cache
import json
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
                "Please run from micropython source tree or specify with env: MICROPY_DIR"
            )
        root = root.parent


@cache
def board_db(mpy_dir, single_port):
    db = dict()
    for p in glob(f"{mpy_dir}/ports/**/boards/**/board.json"):
        path = Path(p)
        port, board = path.parent.parent.parent.name, path.parent.name
        if single_port and port != single_port:
            continue
        with open(p) as f:
            details = json.load(f)
            variants = (
                list(details["variants"].keys()) if "variants" in details.keys() else []
            )
            db.setdefault(port, {})
            db[port].setdefault(board, {})
            db[port][board] = (variants, details)

    # "Special" ports - don't have boards
    for port in SPECIAL_PORTS:
        path = Path("ports", port)
        board = port
        details = {
            "url": f"https://github.com/micropython/micropython/blob/master/ports/{port}/README.md"
        }
        variants = [var.name for var in path.glob("variants/*") if var.is_dir()]
        db.setdefault(port, {})
        db[port].setdefault(board, {})
        db[port][board] = (variants, details)

    return db


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
