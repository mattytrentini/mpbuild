__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from functools import cache
from .find_boards import board_db, find_mpy_root


@cache
def board_database(mpy_dir: str = None, port: str = None):
    mpy_dir, auto_port = find_mpy_root(mpy_dir)
    port = port or auto_port

    db = board_db(mpy_dir, port)
    return db


class OutputFormat(str, Enum):
    rich = "rich"
    text = "text"
