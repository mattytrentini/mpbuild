from . import board_database
from rich.tree import Tree
from rich import print


def list_boards(port: str = None, links: bool = False) -> None:
    db = board_database
    tree = Tree(":snake: [bright_white]MicroPython Boards[/]")
    tree.add
    for p in db.keys():
        if not port or (port and port.name == p):
            treep = tree.add(f"{p}   [bright_black]{len(db[p])}[/]")
            for b in db[p]:
                variants = ", ".join(db[p][b][0])
                variants = f" [bright_black]{variants}[/]" if variants else ""
                treep.add(
                    f"[bright_white][link={db[p][b][1]['url']}]{b}[/link][/] {variants}"
                )
    print(tree)
