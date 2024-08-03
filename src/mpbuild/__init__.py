__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from .find_boards import ports_and_boards

# For testing only!
import os

os.chdir("../mattyt-micropython")


ports = ports_and_boards().keys()
valid_ports = Enum("Ports", dict(([(p, p) for p in ports])))
