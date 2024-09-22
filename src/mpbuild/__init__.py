__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from functools import cache
from .find_boards import find_mpy_root
from .board_database import Database


@cache
def board_database(mpy_dir: str = None) -> Database:
    mpy_dir, port = find_mpy_root(mpy_dir)

    return Database(mpy_dir)


class OutputFormat(str, Enum):
    rich = "rich"
    text = "text"
