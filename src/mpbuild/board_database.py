"""
The micropython git repo contains many 'board.json' files.

This is an example:
ports/stm32/boards/PYBV11/board.json

{
    "deploy": [
        "../PYBV10/deploy.md"
    ],
    "docs": "",
    "features": [],
    "images": [
        "PYBv1_1.jpg",
        "PYBv1_1-C.jpg",
        "PYBv1_1-E.jpg"
    ],
    "mcu": "stm32f4",
    "product": "Pyboard v1.1",
    "thumbnail": "",
    "url": "https://store.micropython.org/product/PYBv1.1",
    "variants": {
        "DP": "Double-precision float",
        "DP_THREAD": "Double precision float + Threads",
        "NETWORK": "Wiznet 5200 Driver",
        "THREAD": "Threading"
    },
    "vendor": "George Robotics"
}

This module implements `class Database` which reads all 'board.json' files and
provides a way to browse it's data.
"""

from __future__ import annotations

from pathlib import Path
import json
from dataclasses import dataclass, field
from glob import glob

DEFAULT_VARIANT = ""
"""
A variant with this name is the default variant.
"""

@dataclass(order=True)
class Variant:
    name: str
    """
    Example: "DP_THREAD"
    """
    text: str
    """
    Example: "Double precision float + Threads"
    """
    board: Board = field(repr=False)

    @property
    def is_default_variant(self) -> bool:
        return self.name == DEFAULT_VARIANT
    

@dataclass(order=True)
class Board:
    name: str
    """
    Example: "PYBV11"
    """
    directory: Path
    """
    The directory of the source code.
    Example: "<repo>/ports/esp32"
    """
    variants: list[Variant]
    """
    List of variants available for this board.
    Variants are sorted.
    The default variant is included in the list and is always first!
    See also the property 'variants_without_default'. 

    Example: ["", "DP_THREAD"]
    """
    url: str
    """
    Primary URL to link to this board.
    """
    mcu: str
    """
    Example: "stm32f4"
    """
    product: str
    """
    Example: "Pyboard v1.1"
    """
    vendor: str
    """
    Example: "George Robotics"
    """
    images: list[str]
    """
    Images of this board, stored in the micropython-media repository.
    Example: ["PYBv1_1.jpg", "PYBv1_1-C.jpg", "PYBv1_1-E.jpg"]
    """
    deploy: list[str]
    """
    Files that explain how to deploy for this board:
    Example: ["../PYBV10/deploy.md"]
    """
    physical_board: bool
    """
    physical_board is False for 'special' builds, namely unix, webassembly, windows.
    True for all actual boards.
    """
    port: Port | None = field(default=None, compare=False)

    @staticmethod
    def factory(filename_json: Path) -> Board:
        with filename_json.open() as f:
            board_json = json.load(f)

        board = Board(
            name=filename_json.parent.name,
            directory=filename_json.parent,
            variants=[],
            url=board_json["url"],
            mcu=board_json["mcu"],
            product=board_json["product"],
            vendor=board_json["vendor"],
            images=board_json["images"],
            deploy=board_json["deploy"],
            physical_board=True,
        )
        board.variants.append(Variant(DEFAULT_VARIANT, "Default variant", board=board))
        board.variants.extend(
            sorted([Variant(*v, board=board) for v in board_json.get("variants", {}).items()])
        )
        return board

    @property
    def deploy_filename(self) -> Path:
        return self.directory / self.deploy[0]

    @property
    def default_variant(self) -> Variant:
        variant = self.variants[0]
        assert variant.name == DEFAULT_VARIANT
        return variant

    @property
    def variants_without_default(self) -> list[Variant]:
        assert self.variants[0].is_default_variant
        return self.variants[1:]
    
    def find_variant(self, variant: str) -> Variant | None:
        for v in self.variants:
            if v.name == variant:
                return v
        return None

@dataclass(order=True)
class Port:
    name: str
    """
    Example: "stm32"
    """
    directory: Path
    """
    The directory of the source code.
    Example: "<repo>/ports"
    """
    boards: dict[str, Board] = field(default_factory=dict, repr=False)
    """
    Example key: "PYBV11"
    """

    @property
    def directory_repo(self) -> Path:
        """
        The top directory of the micropython repo
        """
        repo = self.directory.parent
        assert repo.is_dir(), repo
        assert (repo / "ports" / "renesas-ra").is_dir()
        return repo


@dataclass
class Database:
    """
    This database contains all information retrieved from all 'board.json' files.
    """

    mpy_root_directory: Path = field(repr=False)
    port_filter: str = field(default="", repr=False)

    ports: dict[str, Port] = field(default_factory=dict)
    boards: dict[str, Board] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert isinstance(self.mpy_root_directory, Path)
        assert isinstance(self.port_filter, str)

        if not (self.mpy_root_directory / "ports").is_dir():
            raise ValueError(f"'mpy_root_directory' should point to the top of a micropython repo: {self.mpy_root_directory}")

        # Take care to avoid using Path.glob! Performance was 15x slower.
        for p in glob(f"{self.mpy_root_directory}/ports/*/boards/*/board.json"):
            filename_json = Path(p)
            port_directory = filename_json.parent.parent.parent
            port_name = port_directory.name
            if self.port_filter and self.port_filter != port_name:
                continue

            # Create a port
            port = self.ports.get(port_name, None)
            if port is None:
                port = Port(name=port_name, directory=port_directory.parent)
                self.ports[port_name] = port

            # Load board.json and attach it to the board
            board = Board.factory(filename_json)
            board.port = port

            port.boards[board.name] = board
            self.boards[board.name] = board

        # Add 'special' ports, that don't have boards
        # TODO(mst) Tidy up later (variant descriptions etc)
        for special_port_name in ["unix", "webassembly", "windows"]:
            if self.port_filter and self.port_filter != special_port_name:
                continue
            path = self.mpy_root_directory / "ports" / special_port_name
            board = Board(
                name=special_port_name,
                directory=path,
                variants=[],
                url=f"https://github.com/micropython/micropython/blob/master/ports/{special_port_name}/README.md",
                mcu="",
                product="",
                vendor="",
                images=[],
                deploy=[],
                physical_board=False,
            )
            board.variants.append(Variant(DEFAULT_VARIANT, "Default variant", board=board))
            variant_names = [
                var.name for var in path.glob("variants/*") if var.is_dir()
            ]
            board.variants.extend([Variant(name=v, text="", board=board) for v in variant_names])

            
            port = Port(name=special_port_name, directory=path.parent, boards={special_port_name: board})
            board.port = port

            self.ports[special_port_name] = port
            self.boards[board.name] = board
