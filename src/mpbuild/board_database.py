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

This module imlements `class Database` which reads all 'board.json' files and
allows to browse its data.
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
    Example: DP_THREAD
    """
    text: str
    """
    Example: Double precision float + Threads
    """
    board: Board


@dataclass
class Board:
    name: str
    """
    Example: PYBV11
    """
    variants: list[Variant]
    """
    Example key: DP_THREAD
    Variants are sorted and may be an empty list if no variants are available.
    """
    url: str
    mcu: str
    """
    Example: stm32f4
    """
    product: str
    """
    Example: Pyboard v1.1
    """
    vendor: str
    """
    Example: George Robotics
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
    Example: str32
    """
    boards: dict[str, Board] = field(default_factory=dict)
    """
    Example key: PYBV11
    """

    def __lt__(self, other):
        return self.name < other.name


@dataclass
class Database:
    """
    This database contains all information retrieved from all 'board.json' files.
    """

    mpy_root_directory: str

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


def demo():
    print("query start")
    import timeit

    timer = timeit.Timer(lambda: Database())
    elapsed = timer.timeit(1)
    print(f"Time taken: {elapsed:.6f} seconds")
    db = Database()
    print("query end")

    # import timeit
    # timer = timeit.Timer(lambda: Database())
    # elapsed = timer.timeit(10)
    # print(f'Time taken: {elapsed:.6f} seconds')

    # Build all variants for board 'PYBV11'
    # for variant in db.dict_boards["PYBV11"].variants:
    #    firmware_filename = build.build_board(**variant.buildparams.as_named_parameters)
    #    print(f"FIRMWARE for {variant.name_normalized}: {firmware_filename}")

    # Output of above code:
    # FIRMWARE for PYBV11:           ports/stm32/build-PYBV11/firmware.dfu
    # FIRMWARE for PYBV11_DP:        ports/stm32/build-PYBV11-DP/firmware.dfu
    # FIRMWARE for PYBV11_DP_THREAD: ports/stm32/build-PYBV11-DP_THREAD/firmware.dfu
    # FIRMWARE for PYBV11_NETWORK:   ports/stm32/build-PYBV11-NETWORK/firmware.dfu
    # FIRMWARE for PYBV11_THREAD:    ports/stm32/build-PYBV11-THREAD/firmware.dfu

    # mpbuild --list
    for port in db.ports.values():
        print(f"{port.name} {len(port.boards)}")
        for board in port.boards.values():
            list_variants = [v.name for v in board.variants if board.variants]
            print(f"  {board.name} {', '.join(list_variants)}")

    # Output of above code:
    # ...
    # stm32 65
    #   ...
    #   PYBD_SF6
    #   PYBLITEV10 DP, DP_THREAD, NETWORK, THREAD
    #   PYBV10 DP, DP_THREAD, NETWORK, THREAD
    #   PYBV11 DP, DP_THREAD, NETWORK, THREAD


if __name__ == "__main__":
    demo()
