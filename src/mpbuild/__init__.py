from enum import StrEnum
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .board_database import Database
from .find_boards import find_mpy_root

__app_name__ = "mpbuild"

try:
    __version__ = version(__app_name__)
except PackageNotFoundError:
    # Running from a source checkout without an installation (e.g. uv tool ran
    # directly against the repo). Fall back to a sentinel rather than crashing.
    __version__ = "0.0.0+local"


@cache
def board_database(mpy_dir: Path | None = None, port: str | None = None) -> Database:
    mpy_dir, auto_port = find_mpy_root(mpy_dir)
    port = port or auto_port
    # assert port
    return Database(mpy_dir, port)


class OutputFormat(StrEnum):
    rich = "rich"
    text = "text"
