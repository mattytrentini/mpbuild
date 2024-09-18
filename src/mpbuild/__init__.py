__app_name__ = "mpbuild"
__version__ = "0.1.0"

from enum import Enum
from .find_boards import ports_and_boards, board_db


def find_micropython_root():
    root = Path(os.environ.get("MICROPY_DIR", ".")).resolve()
    while True:
        if (root / "ports").exists() and (root / "mpy-cross").exists():
            return root, port
        
        if root.parent == root:
            raise SystemExit("Please run from micropython source tree or specify with env: MICROPY_DIR")
        root = root.parent
        

root, port = find_micropython_root()
os.chdir(root)


ports = list(ports_and_boards().keys())
# Add 'special' ports - they don't have boards but do have variants
ports.extend(["unix", "webassembly"])
valid_ports = Enum("Ports", dict(([(p, p) for p in ports])))

board_database = board_db()


class OutputFormat(str, Enum):
    rich = "rich"
    text = "text"
