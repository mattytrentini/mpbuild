__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from functools import cache
from .find_boards import ports_and_boards, board_db, find_mpy_root


@cache
def board_database(mpy_dir: str = None):
    mpy_dir, port = find_mpy_root(mpy_dir)

    ports = list(ports_and_boards(mpy_dir).keys())
    # Add 'special' ports - they don't have boards but do have variants
    ports.extend(["unix", "webassembly"])

    db = board_db(mpy_dir, port)
    return db


class OutputFormat(str, Enum):
    rich = "rich"
    text = "text"
