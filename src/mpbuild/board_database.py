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


@dataclass
class Variant:
    name: str
    """
    Example: "DP_THREAD"
    """
    text: str
    """
    Example: "Double precision float + Threads"
    """
    board: Board


@dataclass
class Board:
    name: str
    """
    Example: "PYBV11"
    """
    variants: list[Variant]
    """
    Example key: "DP_THREAD"
    Variants are sorted. May be an empty list if no variants are available.
    """
    url: str
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
    Example: ["PYBv1_1.jpg", "PYBv1_1-C.jpg", "PYBv1_1-E.jpg"]
    """
    port: Port = None

    def __lt__(self, other):
        return self.name < other.name

    @staticmethod
    def factory(filename_json: Path) -> Board:
        with filename_json.open() as f:
            board_json = json.load(f)

        dict_variants = dict(sorted(board_json.get("variants", {}).items()))
        variants: list[Variant] = [
            Variant(k, v, None) for k, v in dict_variants.items()
        ]
        return Board(
            name=filename_json.parent.name,
            variants=variants,
            url=board_json["url"],
            mcu=board_json["mcu"],
            product=board_json["product"],
            vendor=board_json["vendor"],
            images=board_json["images"],
        )


@dataclass
class Port:
    name: str
    """
    Example: "stm32"
    """
    boards: dict[str, Board] = field(default_factory=dict)
    """
    Example key: "PYBV11"
    """

    def __lt__(self, other):
        return self.name < other.name


@dataclass
class Database:
    """
    This database contains all information retrieved from all 'board.json' files.
    """

    mpy_root_directory: str  # TODO(mst) Currently unused.

    ports: dict[str, Port] = field(default_factory=dict)
    boards: dict[str, Board] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Take care to avoid using Path.glob! Performance was 15x slower.
        for p in glob("ports/**/boards/**/board.json"):
            filename_json = Path(p)
            port_name = filename_json.parent.parent.parent.name

            # Create a port
            port = self.ports.get(port_name, None)
            if port is None:
                port = Port(port_name)
                self.ports[port_name] = port

            # Load board.json and attach it to the board
            board = Board.factory(filename_json)
            for variant in board.variants:
                variant.board = board
            board.port = port

            port.boards[board.name] = board
            self.boards[board.name] = board

        # Add 'special' ports, that don't have boards
        # TODO(mst) Tidy up later (variant descriptions etc)
        for special_port_name in ["unix", "webassembly", "windows"]:
            path = Path("ports", special_port_name)
            variant_names = [
                var.name for var in path.glob("variants/*") if var.is_dir()
            ]
            board = Board(
                special_port_name,
                [],
                f"https://github.com/micropython/micropython/blob/master/ports/{special_port_name}/README.md",
                "",
                "",
                "",
                [],
            )
            board.variants = [Variant(v, "", board) for v in variant_names]
            port = Port(special_port_name, {special_port_name: board})
            board.port = port

            self.ports[special_port_name] = port
            self.boards[board.name] = board
