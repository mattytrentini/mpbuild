from typing import Optional
from . import board_database
from rich.tree import Tree
from rich import print

from .cli import OutputFormat


def list_ports() -> list[str]:
    db = board_database()
    return [p.name for p in sorted(db.ports.values())]


def list_boards() -> list[str]:
    db = board_database()
    return [b.name for b in sorted(db.boards.values())]


def list_variants_for_board(board: str) -> list[str]:
    db = board_database()
    variants = db.boards[board].variants
    return [v.name for v in variants if v]


def print_boards(
    port: Optional[str] = None, 
    fmt: OutputFormat = OutputFormat.rich, 
    mpy_dir: Optional[str] = None,
) -> None:
    db = board_database(mpy_dir, port)

    if fmt == OutputFormat.rich:
        tree = Tree(":snake: [bright_white]MicroPython Boards[/]")
        tree.add
        for p in sorted(db.ports.values()):
            if not port or (port and port == p.name):
                treep = tree.add(f"{p.name}   [bright_black]{len(p.boards)}[/]")
                for b in sorted(p.boards.values()):
                    variants = ", ".join([v.name for v in b.variants])
                    variants = f" [bright_black]{variants}[/]" if variants else ""
                    treep.add(
                        f"[bright_white][link={b.url}]{b.name}[/link][/] {variants}"
                    )
        print(tree)

    if fmt == OutputFormat.text:
        """ Output a space-separated list of boards (useful for bash
        completions). Don't display variants."""
        print(
            " ".join(
                [
                    b.name
                    for b in sorted(db.boards.values())
                    if not port or (port and port == b.port.name)
                ]
            )
        )
