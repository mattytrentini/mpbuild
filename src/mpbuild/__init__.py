__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from functools import cache
from pathlib import Path
from .find_boards import find_mpy_root
from .board_database import Database


@cache
def board_database(mpy_dir: Path | None = None, port: str | None = None) -> Database:
    mpy_dir, auto_port = find_mpy_root(mpy_dir)
    port = port or auto_port
    # assert port
    return Database(mpy_dir, port)


class OutputFormat(str, Enum):
    rich = "rich"
    text = "text"
