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


def list_pins() -> list[str]:
    """List all pins across all boards."""
    db = board_database()
    all_pins = set()

    for board in db.boards.values():
        pins = board.pins
        for pin in pins:
            all_pins.add(pin.display_name)

    return sorted(list(all_pins))


def list_pins_for_board(board: str) -> list[str]:
    """List pins for a specific board."""
    db = board_database()
    if board not in db.boards:
        return []

    pins = db.boards[board].pins
    return sorted([pin.display_name for pin in pins])
