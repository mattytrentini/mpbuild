from glob import iglob, glob
from pathlib import Path
from functools import cache
import json
import typer


def iports():
    for p in iglob("ports/**/"):
        yield Path(p).name


def iboards(port):
    for p in iglob(f"ports/{port}/boards/**/"):
        yield Path(p).name


def port_and_board():
    for p in iglob("ports/**/boards/**/"):
        path = Path(p)
        yield path.parent.parent.name, path.name


@cache
def board_db():
    db = dict()
    for p in glob("ports/**/boards/**/board.json"):
        path = Path(p)
        port, board = path.parent.parent.parent.name, path.parent.name
        with open(p) as f:
            details = json.load(f)
            variants = (
                list(details["variants"].keys()) if "variants" in details.keys() else []
            )
            db.setdefault(port, {})
            db[port].setdefault(board, {})
            db[port][board] = (variants, details)
    return db


def get_port(board):
    p_and_b = board_db()
    for p in p_and_b.keys():
        if board in p_and_b[p]:
            return p

    print(f'"{board}" is an invalid board')
    raise typer.Exit(code=1)
