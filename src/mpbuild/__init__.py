__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from .find_boards import ports_and_boards, board_db

# For testing only!
import os

os.chdir("../mattyt-micropython")


ports = list(ports_and_boards().keys())
# Add 'special' ports - they don't have boards but do have variants
ports.extend(["unix", "webassembly"])
valid_ports = Enum("Ports", dict(([(p, p) for p in ports])))

board_database = board_db()
