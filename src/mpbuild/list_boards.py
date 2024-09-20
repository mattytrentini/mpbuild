from . import board_database
from rich.tree import Tree
from rich import print

from .cli import OutputFormat


def list_boards(
    port: str = None, fmt: OutputFormat = OutputFormat.rich, mpy_dir: str = None
) -> None:
    db = board_database(mpy_dir)

    if fmt == OutputFormat.rich:
        tree = Tree(":snake: [bright_white]MicroPython Boards[/]")
        tree.add
        for p in db.keys():
            if not port or (port and port == p):
                treep = tree.add(f"{p}   [bright_black]{len(db[p])}[/]")
                for b in sorted(db[p]):
                    variants = ", ".join(db[p][b][0])
                    variants = f" [bright_black]{variants}[/]" if variants else ""
                    treep.add(
                        f"[bright_white][link={db[p][b][1]['url']}]{b}[/link][/] {variants}"
                    )
        print(tree)

    if fmt == OutputFormat.text:
        """ Output a space-separated list of boards (useful for bash
        completions). Don't display variants."""
        print(
            " ".join(
                [
                    " ".join(sorted(db[p]))
                    for p in db.keys()
                    if not port or (port and port == p)
                ]
            )
        )
