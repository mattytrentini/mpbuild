from . import board_database


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
