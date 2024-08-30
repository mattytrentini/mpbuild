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

import pathlib
import json
import dataclasses

from mpbuild import build

DEFAULT_VARIANT = ""


@dataclasses.dataclass(repr=True)
class Buildparams:
    """
    These are the parameters to be passed to: 'build.build_board(port, board, variant)'
    """

    port: str
    board: str
    variant: str | None

    @property
    def as_named_parameters(self) -> dict[str, str | None]:
        """
        Use it as follows: 'build.build_board(**self.as_named_parameters)'
        """
        return self.__dict__


@dataclasses.dataclass(repr=True)
class Variant:
    name: str
    """
    Example: DP_THREAD
    """
    text: str
    """
    Example: Double precision float + Threads
    """
    board: Board = None

    @property
    def name_normalized(self) -> str:
        """
        Examples:
        PYBV11 (the default variant)
        PYBV11_DP_THREAD (a specific variant)
        """
        if self.name == DEFAULT_VARIANT:
            return self.board.name
        return f"{self.board.name}_{self.name}"

    @property
    def buildparams(self) -> Buildparams:
        variant = None if (self.name == DEFAULT_VARIANT) else self.name
        return Buildparams(
            port=self.board.port.name, board=self.board.name, variant=variant
        )


@dataclasses.dataclass(repr=True)
class Board:
    name: str
    """
    Example: PYBV11
    """
    variants: list[Variant]
    """
    Example key: DP_THREAD
    This list ALSO contains a default variant.
    Therefor 'len(variants)' is allways at least 1!
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
    port: Port = None

    @property
    def default_variant(self) -> Variant:
        variant = self.variants[0]
        assert variant.name == DEFAULT_VARIANT
        return variant

    @property
    def variants_without_default(self) -> list[Variant]:
        return self.variants[1:]

    @staticmethod
    def factory(filename_json: pathlib.Path) -> Board:
        with filename_json.open("r") as f:
            board_dict = json.load(f)

        # Sort the variants alphabetically and add the default variant
        variants: list[Variant] = [
            Variant(DEFAULT_VARIANT, "Default variant"),
        ]
        dict_variants = board_dict.get("variants", {})
        for name in sorted(dict_variants.keys()):
            variants.append(Variant(name, dict_variants[name]))

        return Board(
            name=filename_json.parent.name,
            variants=variants,
            url=board_dict["url"],
            mcu=board_dict["mcu"],
            product=board_dict["product"],
            vendor=board_dict["vendor"],
        )


@dataclasses.dataclass(repr=True)
class Port:
    ports: Database
    name: str
    """
    Example: str32
    """
    dict_boards: dict[str, Board] = dataclasses.field(default_factory=dict)
    """
    Example key: PYBV11
    """

    @property
    def boards_ordered(self) -> list[Board]:
        return [self.dict_boards[k] for k in sorted(self.dict_boards.keys())]


@dataclasses.dataclass(repr=True)
class Database:
    """
    This database contains all information retrieved from all 'board.json' files.
    """

    dict_ports: dict[str, Port] = dataclasses.field(default_factory=dict)
    dict_boards: dict[str, Board] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        for filename_json in pathlib.Path.cwd().glob("ports/**/boards/**/board.json"):
            port_name = filename_json.parent.parent.parent.name

            # Create a port
            port = self.dict_ports.get(port_name, None)
            if port is None:
                port = Port(ports=self, name=port_name)
                self.dict_ports[port_name] = port

            # Load board.json and attach it to the board
            board = Board.factory(filename_json=filename_json)
            for variant in board.variants:
                variant.board = board
            board.port = port
            port.dict_boards[board.name] = board
            self.dict_boards[board.name] = board

    @property
    def ports_ordered(self) -> list[Port]:
        return [self.dict_ports[k] for k in sorted(self.dict_ports.keys())]


def demo():
    db = Database()

    # Build all variants for board 'PYBV11'
    for variant in db.dict_boards["PYBV11"].variants:
        firmware_filename = build.build_board(**variant.buildparams.as_named_parameters)
        print(f"FIRMWARE for {variant.name_normalized}: {firmware_filename}")

    # Output of above code:
    # FIRMWARE for PYBV11:           ports/stm32/build-PYBV11/firmware.dfu
    # FIRMWARE for PYBV11_DP:        ports/stm32/build-PYBV11-DP/firmware.dfu
    # FIRMWARE for PYBV11_DP_THREAD: ports/stm32/build-PYBV11-DP_THREAD/firmware.dfu
    # FIRMWARE for PYBV11_NETWORK:   ports/stm32/build-PYBV11-NETWORK/firmware.dfu
    # FIRMWARE for PYBV11_THREAD:    ports/stm32/build-PYBV11-THREAD/firmware.dfu

    # mpbuild --list
    for port in db.ports_ordered:
        print(f"{port.name} {len(port.dict_boards)}")
        for board in port.boards_ordered:
            list_variants = [v.name for v in board.variants_without_default]
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
