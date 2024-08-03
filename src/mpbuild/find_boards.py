from glob import iglob
from pathlib import Path
from functools import cache


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
def ports_and_boards():
    p_and_b = dict()
    for p, b in port_and_board():
        p_and_b.setdefault(p, []).append(b)
    return p_and_b
