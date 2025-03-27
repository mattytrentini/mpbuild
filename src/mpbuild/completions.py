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


def _complete(words: list[str], incomplete: str):
    completion = []
    for name in words:
        if name.startswith(incomplete):
            completion.append(name)
    return completion


def complete_board(incomplete: str):
    return _complete(list_boards(), incomplete)


def complete_board_variant(incomplete: str):
    # If no dash yet, only complete board names
    if "-" not in incomplete:
        boards = complete_board(incomplete)
        if incomplete in boards:
            # Offer variant options as well
            board = incomplete
            variants = list_variants_for_board(board)
            boards.extend([f"{board}-{v}" for v in variants])
        
        if len(boards) == 1:
            board = boards[0]
            if board != incomplete:
                #  finish completing this board
                if variants:
                    # There are possible variants, remove the
                    # trailing space from the autocomplete
                    # so the user can autocomplete the variant 
                    # if desired
                    boards[0] += r"\b"
            else:
                # board name complete, suggest variants (if any)
                return [f"{board}-{v}" for v in variants]
        return boards
    else:
        # After board name, complete variants for the specified board
        board, variant_part = incomplete.split("-", 1)
    
        if board in list_boards():
            variants = list_variants_for_board(board)
            if variants:
                return [f"{board}-{v}" for v in variants if v.startswith(variant_part)]
    return []


def complete_port(incomplete: str):
    return _complete(list_ports(), incomplete)