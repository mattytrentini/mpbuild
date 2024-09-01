__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from .find_boards import board_db

# For testing only!
import os

try:
    os.stat("./ports")
except OSError:
    raise SystemExit("Please run from root of micropython source tree")

board_database = board_db()

ports = list(board_database.keys())

# Currently not used; doesn't seem possible to have an *optional* enum
# *argument*.
ValidPorts = Enum("Ports", {p: p for p in ports})


class OutputFormat(str, Enum):
    rich = "rich"
    text = "text"
